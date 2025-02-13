from PIL import Image
import torch
from pathlib import Path
import json
from tqdm import tqdm
from transformers import CLIPProcessor, CLIPModel
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time
import pickle
import pillow_heif
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.image_features = {}
        self.index_path = "image_index.pkl"
        
        # Загружаем существующий индекс, если он есть
        if os.path.exists(self.index_path):
            logger.info("Загружен существующий индекс")
            with open(self.index_path, 'rb') as f:
                self.image_features = pickle.load(f)
                logger.info(f"({len(self.image_features)} изображений)")
    
    def load_model(self):
        if self.model is None:
            logger.info("Загрузка модели CLIP...")
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            if self.device == "cpu":
                self.model.float()  # Используем float32 для CPU
            logger.info(f"Модель загружена (используется {self.device}, {torch.get_num_threads()} потоков)")
    
    def convert_heic_to_jpeg(self, heic_path):
        try:
            # Создаем jpeg путь, заменяя расширение
            jpeg_path = str(heic_path).rsplit('.', 1)[0] + '.jpg'
            
            # Если JPEG уже существует и новее чем HEIC, пропускаем
            if os.path.exists(jpeg_path) and os.path.getmtime(jpeg_path) > os.path.getmtime(heic_path):
                return jpeg_path
            
            # Конвертируем HEIC в PIL Image
            heif_file = pillow_heif.read_heif(heic_path)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
            
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Сохраняем как JPEG
            image.save(jpeg_path, 'JPEG', quality=95)
            logger.info(f"Конвертирован {heic_path} -> {jpeg_path}")
            return jpeg_path
        except Exception as e:
            logger.error(f"Ошибка при конвертации {heic_path}: {str(e)}")
            return None

    def process_image(self, image_path):
        try:
            # Проверяем формат файла
            if image_path.lower().endswith('.heic'):
                # Конвертируем HEIC в JPEG и получаем новый путь
                jpeg_path = self.convert_heic_to_jpeg(image_path)
                if jpeg_path is None:
                    return None
                # Открываем сконвертированное изображение
                image = Image.open(jpeg_path)
            else:
                # Открываем обычное изображение
                image = Image.open(image_path)
            
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Предобработка и получение эмбеддингов
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                image_features = image_features.cpu().numpy()
                # Нормализуем вектор
                image_features = image_features / np.linalg.norm(image_features)
            return image_features
        except Exception as e:
            logger.error(f"Ошибка при обработке {image_path}: {str(e)}")
            return None

    def update_index(self, images_dir, progress_callback=None):
        self.load_model()
        
        # Получаем список всех изображений
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.heic', '*.HEIC', '*.PNG', '*.JPG', '*.JPEG']:
            image_files.extend(Path(images_dir).glob(ext))
        
        # Фильтруем файлы, исключая видео и поврежденные изображения
        valid_files = []
        for img_path in image_files:
            try:
                # Если это HEIC файл, проверяем возможность конвертации
                if str(img_path).lower().endswith('.heic'):
                    jpeg_path = self.convert_heic_to_jpeg(str(img_path))
                    if jpeg_path:
                        valid_files.append(Path(jpeg_path))
                    continue
                
                # Для остальных файлов проверяем как обычно
                with Image.open(img_path) as img:
                    img.verify()
                valid_files.append(img_path)
            except Exception as e:
                logger.error(f"Пропускаем файл {img_path}: {str(e)}")
                continue
        
        # Удаляем дубликаты путей (если HEIC уже был сконвертирован ранее)
        valid_files = list(set(valid_files))
        
        total_files = len(valid_files)
        logger.info(f"Найдено всего {total_files} валидных изображений из {len(image_files)} файлов")
        
        # Инициализируем прогресс
        if progress_callback:
            progress_callback(0, total_files)
        
        # Проверяем, какие файлы новые или изменились
        new_files = []
        for image_path in valid_files:
            image_path_str = str(image_path)
            # Для JPEG файлов, конвертированных из HEIC, проверяем время изменения исходного HEIC
            heic_path = image_path_str.rsplit('.', 1)[0] + '.heic'
            if os.path.exists(heic_path):
                mtime = max(os.path.getmtime(image_path), os.path.getmtime(heic_path))
            else:
                mtime = os.path.getmtime(image_path)
            
            if image_path_str not in self.image_features or \
               mtime > self.image_features[image_path_str].get('mtime', 0):
                new_files.append(image_path)
        
        if not new_files:
            logger.info("Новых или измененных файлов не обнаружено")
            if progress_callback:
                progress_callback(total_files, total_files)  # Показываем 100% прогресс
            return
        
        logger.info(f"Найдено {len(new_files)} новых или измененных файлов")
        
        # Обрабатываем новые файлы с промежуточным сохранением
        processed = 0
        for i, image_path in enumerate(tqdm(new_files, desc="Обработка изображений")):
            image_path_str = str(image_path)
            features = self.process_image(image_path_str)
            if features is not None:
                self.image_features[image_path_str] = {
                    'features': features,
                    'mtime': os.path.getmtime(image_path)
                }
                processed += 1
            
            # Обновляем прогресс с учетом уже обработанных файлов
            if progress_callback:
                progress_callback(processed, len(new_files))
            
            # Сохраняем каждые 100 изображений
            if (i + 1) % 100 == 0:
                logger.info(f"Промежуточное сохранение индекса... ({i + 1}/{len(new_files)})")
                with open(self.index_path, 'wb') as f:
                    pickle.dump(self.image_features, f)
        
        # Финальное сохранение
        logger.info("Сохранение индекса...")
        with open(self.index_path, 'wb') as f:
            pickle.dump(self.image_features, f)
        logger.info("Индекс сохранен!")
    
    def search_images(self, query, top_k=30):
        self.load_model()
        
        # Кодируем текстовый запрос
        with torch.no_grad():
            inputs = self.processor(text=query, return_tensors="pt", padding=True).to(self.device)
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features.cpu().numpy()
            
            # Нормализуем вектор запроса
            text_features = text_features / np.linalg.norm(text_features)
        
        # Считаем косинусное сходство со всеми изображениями
        results = []
        for path, data in self.image_features.items():
            if 'features' in data:  # Проверяем наличие признаков
                # Нормализуем вектор изображения
                image_features = data['features']  # Уже нормализован при сохранении
                similarity = float(np.dot(text_features, image_features.T)[0][0])
                # Преобразуем сходство в проценты (0-100)
                similarity = max(0, min(100, (similarity + 1) * 50))  # Ограничиваем значения от 0 до 100
                results.append((path, similarity))
        
        # Сортируем по убыванию сходства и возвращаем top_k результатов
        results.sort(key=lambda x: x[1], reverse=True)
        return [{'path': path, 'score': score} for path, score in results[:top_k]]

def main():
    # Предварительно загружаем модель в кэш, если её там нет
    if not os.path.exists(os.path.expanduser('~/.cache/huggingface/hub')):
        print("Первичная загрузка и кэширование модели CLIP...")
        CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("Модель загружена в кэш")
    
    engine = ImageSearchEngine()
    
    # Проверяем наличие индекса перед обновлением
    if not os.path.exists('image_index.json'):
        print("Создание индекса...")
        engine.update_index("Photos")
    
    while True:
        print("\nВведите поисковый запрос (или 'exit' для выхода, 'update' для обновления индекса):")
        query = input().strip()
        
        if query.lower() == 'exit':
            break
        elif query.lower() == 'update':
            engine.update_index("Photos")
            continue
        
        results = engine.search_images(query)
        
        if results:
            print(f"\nНайдено {len(results)} изображений:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Файл: {result['path']}")
                print(f"   Уверенность: {result['score']:.2%}")
        else:
            print("\nИзображений по запросу не найдено")

if __name__ == "__main__":
    main() 