from pyicloud import PyiCloudService
import os
import time
from pathlib import Path
import logging
import pickle
import json
from cryptography.fernet import Fernet
from config import SESSION_FILE, ENCRYPTION_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ICloudSync:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.api = None
        self.photos_dir = Path("Photos")
        self.photos_dir.mkdir(exist_ok=True)
        
    def connect(self):
        """Подключается к iCloud"""
        try:
            if self.username and self.password:
                self.api = PyiCloudService(self.username, self.password)
                
                if self.api.requires_2fa:
                    logger.error("Требуется двухфакторная аутентификация")
                    return False, "Требуется двухфакторная аутентификация"
                
                return True, "Успешное подключение"
            
            return False, "Необходимы учетные данные для входа"
            
        except Exception as e:
            logger.error(f"Ошибка при подключении к iCloud: {str(e)}")
            return False, str(e)

    def verify_2fa_code(self, code):
        try:
            if not self.api:
                return False
            result = self.api.validate_2fa_code(code)
            return result
        except Exception as e:
            logger.error(f"Ошибка при проверке кода 2FA: {str(e)}")
            return False

    def sync_photos(self, progress_callback=None):
        if not self.api:
            success, message = self.connect()
            if not success:
                return False, message, []

        try:
            # Получаем все фотографии
            all_photos = self.api.photos.all
            total = len(all_photos)
            logger.info(f"Всего файлов в iCloud: {total}")
            
            if total == 0:
                return True, "Нет фотографий для синхронизации", []
            
            downloaded = 0
            new_photos = 0
            failed_photos = []
            retry_count = 3  # Количество попыток скачивания
            max_workers = 10  # Максимальное количество потоков

            logger.info(f"Начинаем синхронизацию {total} фотографий")
            
            from concurrent.futures import ThreadPoolExecutor
            from queue import Queue
            
            # Очередь для обновления прогресса
            progress_queue = Queue()
            
            def update_progress():
                nonlocal downloaded, new_photos
                while True:
                    item = progress_queue.get()
                    if item is None:  # Сигнал завершения
                        break
                    success, is_new = item
                    downloaded += 1
                    if success and is_new:
                        new_photos += 1
                    if progress_callback:
                        progress = (downloaded / total) * 100
                        progress_callback(progress, downloaded, total, new_photos)

            # Запускаем поток обновления прогресса
            import threading
            progress_thread = threading.Thread(target=update_progress)
            progress_thread.start()

            def download_photo(photo):
                try:
                    # Получаем имя файла
                    filename = None
                    if hasattr(photo, 'filename'):
                        filename = photo.filename
                    elif hasattr(photo, 'id'):
                        filename = f"{photo.id}.jpg"
                    else:
                        logger.error(f"Не удалось получить имя файла для фото")
                        progress_queue.put((False, False))
                        return "unknown_filename"

                    # Генерируем путь для сохранения
                    download_path = self.photos_dir / filename
                    
                    # Проверяем, существует ли уже файл
                    if download_path.exists():
                        progress_queue.put((True, False))
                        return None

                    logger.info(f"Скачиваем {filename}...")
                    
                    # Пробуем скачать файл несколько раз
                    for attempt in range(retry_count):
                        try:
                            # Получаем response для скачивания
                            response = photo.download()
                            
                            # Проверяем что это действительно response
                            if hasattr(response, 'content'):
                                # Сохраняем файл
                                with open(download_path, 'wb') as f:
                                    f.write(response.content)
                                
                                # Проверяем, что файл действительно создан и не пустой
                                if download_path.exists() and download_path.stat().st_size > 0:
                                    logger.info(f"Успешно скачано: {filename}")
                                    progress_queue.put((True, True))
                                    return None
                                else:
                                    logger.warning(f"Попытка {attempt + 1}: Файл не был создан или пустой: {filename}")
                                    if download_path.exists():
                                        download_path.unlink()
                            else:
                                logger.warning(f"Попытка {attempt + 1}: Неверный формат ответа при скачивании {filename}")
                            
                            time.sleep(1)  # Добавляем задержку между попытками
                            
                        except Exception as e:
                            logger.error(f"Ошибка при скачивании {filename} (попытка {attempt + 1}): {str(e)}")
                            if download_path.exists():
                                download_path.unlink()
                            time.sleep(1)
                    
                    logger.error(f"Не удалось скачать после {retry_count} попыток: {filename}")
                    progress_queue.put((False, False))
                    return filename
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке фото: {str(e)}")
                    progress_queue.put((False, False))
                    return filename if filename else "unknown_filename"

            # Запускаем загрузку в пуле потоков
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                failed = list(filter(None, executor.map(download_photo, all_photos)))
                failed_photos.extend(failed)

            # Убеждаемся что прогресс дошел до 100%
            if downloaded < total:
                remaining = total - downloaded
                for _ in range(remaining):
                    progress_queue.put((True, False))

            # Завершаем поток прогресса
            progress_queue.put(None)
            progress_thread.join()

            status_message = f"Синхронизация завершена. Скачано новых фотографий: {new_photos}"
            if failed_photos:
                status_message += f"\nНе удалось скачать {len(failed_photos)} фотографий"
                logger.error(f"Список неудачных загрузок: {', '.join(failed_photos)}")

            return True, status_message, failed_photos

        except Exception as e:
            error_message = f"Ошибка при синхронизации: {str(e)}"
            logger.error(error_message)
            return False, error_message, [] 