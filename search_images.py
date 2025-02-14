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
import cv2

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
        self.progress_path = "indexing_progress.json"
        self.last_update = None
        
        # Загружаем существующий индекс, если он есть
        if os.path.exists(self.index_path):
            logger.info("Загружен существующий индекс")
            with open(self.index_path, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, dict):
                    self.image_features = data
                    self.last_update = time.ctime(os.path.getmtime(self.index_path))
                elif isinstance(data, tuple):
                    self.image_features, self.last_update = data
                logger.info(f"({len(self.image_features)} изображений)")
        
        # Загружаем прогресс индексации, если он есть
        self._load_progress()
    
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
            if os.path.exists(jpeg_path) and os.path.getmtime(jpeg_path) > os.path.getmtime(str(heic_path)):
                return jpeg_path
            
            # Конвертируем HEIC в PIL Image
            heif_file = pillow_heif.read_heif(str(heic_path))  # Преобразуем Path в строку
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

    def extract_video_frame(self, video_path):
        """Извлекает первый кадр из видео файла"""
        try:
            # Открываем видео файл
            cap = cv2.VideoCapture(str(video_path))
            
            # Проверяем, успешно ли открыт файл
            if not cap.isOpened():
                logger.error(f"Не удалось открыть видео файл: {video_path}")
                return None
            
            # Читаем первый кадр
            ret, frame = cap.read()
            
            # Освобождаем ресурсы
            cap.release()
            
            if not ret:
                logger.error(f"Не удалось прочитать кадр из видео: {video_path}")
                return None
            
            # Конвертируем BGR в RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Конвертируем в PIL Image
            return Image.fromarray(frame_rgb)
        except Exception as e:
            logger.error(f"Ошибка при извлечении кадра из видео {video_path}: {str(e)}")
            return None

    def process_image(self, image_path):
        try:
            # Проверяем расширение файла
            ext = str(image_path).lower()
            if ext.endswith(('.mp4', '.mov', '.avi', '.mkv')):
                # Для видео файлов извлекаем первый кадр
                image = self.extract_video_frame(image_path)
                if image is None:
                    return None
            else:
                # Для обычных изображений используем существующую логику
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
                # Преобразуем в одномерный массив
                return image_features.flatten()
        except Exception as e:
            logger.error(f"Ошибка при обработке {image_path}: {str(e)}")
            return None

    def check_index_exists(self):
        """Проверяет существование индекса"""
        return os.path.exists(self.index_path) and len(self.image_features) > 0

    def get_last_update_time(self):
        """Возвращает время последнего обновления индекса"""
        return self.last_update or "Никогда"

    def _save_progress(self, processed_files, total_files):
        """Сохраняет прогресс индексации"""
        progress_data = {
            "processed_files": processed_files,
            "total_files": total_files,
            "last_save_time": time.time()
        }
        with open(self.progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

    def _load_progress(self):
        """Загружает прогресс индексации"""
        if os.path.exists(self.progress_path):
            try:
                with open(self.progress_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке прогресса: {e}")
        return None

    def convert_all_heic_files(self, images_dir):
        """Конвертирует все HEIC файлы в JPEG перед индексацией"""
        logger.info("Поиск HEIC файлов для конвертации...")
        images_dir = Path(images_dir)
        heic_files = []
        for ext in ['*.HEIC', '*.heic']:
            heic_files.extend(list(images_dir.rglob(ext)))
        
        if not heic_files:
            logger.info("HEIC файлы не найдены")
            return
        
        logger.info(f"Найдено {len(heic_files)} HEIC файлов")
        for heic_path in tqdm(heic_files, desc="Конвертация HEIC в JPEG"):
            self.convert_heic_to_jpeg(heic_path)

    def update_index(self, images_dir="Photos", progress_callback=None):
        """Обновляет индекс изображений"""
        self.load_model()
        images_dir = Path(images_dir)
        
        # Сначала конвертируем все HEIC файлы
        self.convert_all_heic_files(images_dir)
        
        # Получаем список всех изображений и видео
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.mp4', '*.mov', '*.avi', '*.mkv']:
            image_files.extend(list(images_dir.rglob(ext)))
        
        # Проверяем, какие файлы уже проиндексированы
        existing_files = set(str(Path(path)) for path in self.image_features.keys())
        new_files = [f for f in image_files if str(f) not in existing_files]
        
        if not new_files:
            logger.info("Новых файлов для индексации не найдено")
            if progress_callback:
                progress_callback(0, 0)  # Сообщаем, что новых файлов нет
            return True  # Возвращаем True, чтобы показать, что новых файлов нет
        
        total_images = len(new_files)
        processed = 0
        logger.info(f"Найдено {total_images} новых файлов для индексации")
        
        # Загружаем сохраненный прогресс
        saved_progress = self._load_progress()
        if saved_progress:
            # Пропускаем уже обработанные файлы
            processed_paths = set(str(Path(path)) for path in self.image_features.keys())
            new_files = [f for f in new_files if str(f) not in processed_paths]
            processed = saved_progress.get("processed_files", 0)
            logger.info(f"Восстановление индексации с {processed} обработанных файлов")
        
        if progress_callback:
            progress_callback(processed, total_images)
        
        for image_path in tqdm(new_files, desc="Индексация новых файлов"):
            try:
                features = self.process_image(image_path)
                if features is not None:
                    self.image_features[str(image_path)] = features
                
                processed += 1
                
                # Сохраняем прогресс каждые 100 изображений
                if processed % 100 == 0:
                    self._save_progress(processed, total_images)
                    # Сохраняем текущий индекс
                    self.last_update = time.ctime()
                    with open(self.index_path, 'wb') as f:
                        pickle.dump((self.image_features, self.last_update), f)
                    logger.info(f"Сохранен промежуточный прогресс: {processed} из {total_images}")
                
                if progress_callback:
                    progress_callback(processed, total_images)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке {image_path}: {e}")
        
        # Сохраняем окончательный индекс
        self.last_update = time.ctime()
        with open(self.index_path, 'wb') as f:
            pickle.dump((self.image_features, self.last_update), f)
        
        # Удаляем файл прогресса после успешного завершения
        if os.path.exists(self.progress_path):
            os.remove(self.progress_path)
        
        logger.info(f"Индекс обновлен (всего {len(self.image_features)} файлов, добавлено {len(new_files)} новых)")
        return False  # Возвращаем False, чтобы показать, что были обработаны новые файлы

    def search_images(self, query, top_k=30):
        self.load_model()
        
        # Кодируем текстовый запрос
        with torch.no_grad():
            inputs = self.processor(text=query, return_tensors="pt", padding=True).to(self.device)
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features.cpu().numpy()
            # Нормализуем вектор запроса и преобразуем в одномерный массив
            text_features = text_features.flatten()
            text_features = text_features / np.linalg.norm(text_features)
        
        # Считаем косинусное сходство со всеми изображениями
        results = []
        for path, features in self.image_features.items():
            similarity = float(np.dot(text_features, features))
            # Преобразуем сходство в проценты (0-100)
            similarity = max(0, min(100, (similarity + 1) * 50))
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