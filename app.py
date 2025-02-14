from flask import Flask, render_template, jsonify, request, send_file, Response
import os
from search_images import ImageSearchEngine
from pathlib import Path
from icloud_sync import ICloudSync
import threading
import json
import time
import sys
import subprocess
from datetime import datetime
from PIL import Image
import pillow_heif
import shutil
import uuid
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from logger_config import setup_logger
import logging

# Настройка логирования
logger = setup_logger('app')

# Отключаем стандартное логирование Flask и Werkzeug
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.disabled = True

app = Flask(__name__)
# Отключаем логирование Flask
app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = True

# Настройка приложения
app.config['DEBUG'] = True
app.config['USE_RELOADER'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['IMAGES_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Photos')

# Создаем директорию для фотографий, если она не существует
os.makedirs(app.config['IMAGES_DIR'], exist_ok=True)
logger.info(f"Директория для фотографий: {app.config['IMAGES_DIR']}")

# Путь к файлу с сохраненными учетными данными
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.enc')

def get_device_id():
    """Получает или создает уникальный идентификатор устройства"""
    device_id_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.device_id')
    if os.path.exists(device_id_file):
        with open(device_id_file, 'r') as f:
            device_id = f.read().strip()
            logger.debug(f"Загружен существующий device_id: {device_id[:8]}...")
            return device_id
    
    # Создаем новый идентификатор устройства
    device_id = str(uuid.uuid4())
    logger.info(f"Создан новый device_id: {device_id[:8]}...")
    with open(device_id_file, 'w') as f:
        f.write(device_id)
    return device_id

def get_encryption_key():
    """Генерирует ключ шифрования на основе идентификатора устройства"""
    device_id = get_device_id().encode()
    # Используем PBKDF2 для генерации ключа из идентификатора устройства
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'icloud_photos_app',  # Фиксированная соль
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(device_id))
    return key

def save_credentials(username, password):
    """Сохраняет зашифрованные учетные данные"""
    try:
        logger.debug(f"Попытка сохранения учетных данных для пользователя: {username}")
        key = get_encryption_key()
        f = Fernet(key)
        data = {
            'username': username,
            'password': password
        }
        encrypted_data = f.encrypt(json.dumps(data).encode())
        with open(CREDENTIALS_FILE, 'wb') as file:
            file.write(encrypted_data)
        logger.info(f"Учетные данные успешно сохранены для пользователя: {username}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении учетных данных: {str(e)}")
        return False

def load_credentials():
    """Загружает и расшифровывает учетные данные"""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            logger.debug("Файл с учетными данными не найден")
            return None
            
        logger.debug("Попытка загрузки сохраненных учетных данных")
        key = get_encryption_key()
        f = Fernet(key)
        with open(CREDENTIALS_FILE, 'rb') as file:
            encrypted_data = file.read()
        decrypted_data = f.decrypt(encrypted_data)
        data = json.loads(decrypted_data.decode())
        logger.info(f"Учетные данные успешно загружены для пользователя: {data['username']}")
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке учетных данных: {str(e)}")
        return None

def delete_credentials():
    """Удаляет сохраненные учетные данные"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            logger.debug("Удаление файла с учетными данными")
            os.remove(CREDENTIALS_FILE)
            logger.info("Файл с учетными данными успешно удален")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении учетных данных: {str(e)}")
        return False

def initialize_engine():
    try:
        return ImageSearchEngine()
    except EOFError:
        logger.warning("Ошибка при загрузке индекса. Создаем новый индекс...")
        # Если индекс поврежден, удаляем его и создаем новый
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image_index.pkl')
        if os.path.exists(index_path):
            os.remove(index_path)
        return ImageSearchEngine()

engine = initialize_engine()
icloud_sync = None
sync_progress = {
    "status": "idle",
    "progress": 0,
    "message": "",
    "total": 0,
    "downloaded": 0,
    "new_photos": 0,
    "failed_photos": []
}
sync_lock = threading.Lock()

# Добавляем глобальную переменную для отслеживания прогресса индексации
indexing_progress = {
    "status": "idle",
    "current": 0,
    "total": 0,
    "message": ""
}

def progress_callback(progress, downloaded, total, new_photos):
    global sync_progress
    with sync_lock:
        sync_progress["progress"] = round(progress)
        sync_progress["downloaded"] = downloaded
        sync_progress["total"] = total
        sync_progress["new_photos"] = new_photos
        sync_progress["message"] = f"Загружено {downloaded} из {total} фотографий. Новых: {new_photos}"

def generate_progress_events():
    while True:
        with sync_lock:
            data = {
                'progress': sync_progress['progress'],
                'status': f"Загружено {sync_progress['downloaded']} из {sync_progress['total']} фотографий. Новых: {sync_progress['new_photos']}"
            }
        yield f"data: {json.dumps(data)}\n\n"
        if sync_progress['progress'] >= 100:
            break
        time.sleep(0.2)

def generate_indexing_events():
    """Генерирует события о прогрессе индексации"""
    logger.info("Начало генерации событий индексации")
    while True:
        with sync_lock:
            if indexing_progress["total"] > 0:
                progress = round((indexing_progress["current"] / indexing_progress["total"] * 100))
            else:
                progress = 0
            
            data = {
                'progress': progress,
                'status': indexing_progress["message"],
                'state': indexing_progress["status"]
            }
            logger.debug(f"Отправка события индексации: {data}")
            
            if indexing_progress["status"] in ["completed", "stopped", "no_new_files"]:
                data['progress'] = 100
                logger.info(f"Завершение индексации со статусом: {indexing_progress['status']}")
        
        yield f"data: {json.dumps(data)}\n\n"
        
        if data['progress'] >= 100 or indexing_progress["status"] in ["completed", "stopped", "no_new_files"]:
            logger.info("Завершение потока событий индексации")
            break
        
        time.sleep(0.2)

@app.route('/')
def index():
    logger.info("Запрос главной страницы")
    return render_template('index.html')

@app.route('/icloud/connect', methods=['POST'])
def icloud_connect():
    global icloud_sync
    data = request.json
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False)
    
    logger.debug(f"Попытка подключения к iCloud для пользователя: {username}")
    
    if not username or not password:
        logger.error("Не указан логин или пароль")
        return jsonify({"success": False, "error": "Не указан логин или пароль"})
    
    logger.info(f"Инициализация подключения к iCloud для пользователя: {username}")
    icloud_sync = ICloudSync(username, password)
    success, message = icloud_sync.connect()
    
    if success:
        logger.info(f"Успешное подключение к iCloud для пользователя: {username}")
        if remember:
            logger.debug("Сохранение учетных данных по запросу пользователя")
            if save_credentials(username, password):
                logger.info("Учетные данные успешно сохранены")
            else:
                logger.warning("Не удалось сохранить учетные данные")
        
        if not message.startswith('2fa'):
            logger.info("Запуск автоматической синхронизации")
            thread = threading.Thread(target=lambda: start_sync_process())
            thread.start()
    else:
        logger.error(f"Ошибка подключения к iCloud: {message}")
    
    return jsonify({"success": success, "message": message})

@app.route('/icloud/verify_2fa', methods=['POST'])
def verify_2fa():
    global icloud_sync
    if not icloud_sync:
        return jsonify({"success": False, "error": "Нет активного подключения"})
    
    code = request.json.get('code')
    if not code:
        return jsonify({"success": False, "error": "Не указан код подтверждения"})
    
    success = icloud_sync.verify_2fa_code(code)
    
    # Если двухфакторная аутентификация успешна, запускаем синхронизацию
    if success:
        thread = threading.Thread(target=lambda: start_sync_process())
        thread.start()
    
    return jsonify({"success": success})

@app.route('/icloud/load_credentials', methods=['GET'])
def get_saved_credentials():
    """Загружает сохраненные учетные данные"""
    credentials = load_credentials()
    if credentials:
        return jsonify({"success": True, "credentials": {"username": credentials['username']}})
    return jsonify({"success": False})

@app.route('/icloud/delete_credentials', methods=['POST'])
def remove_credentials():
    """Удаляет сохраненные учетные данные"""
    success = delete_credentials()
    return jsonify({"success": success})

def start_sync_process():
    """Вспомогательная функция для запуска процесса синхронизации"""
    global sync_progress
    
    with sync_lock:
        if sync_progress["status"] == "syncing":
            return
        
        sync_progress = {
            "status": "syncing",
            "progress": 0,
            "message": "Начинаем синхронизацию...",
            "total": 0,
            "downloaded": 0,
            "new_photos": 0,
            "failed_photos": []
        }
    
    try:
        success, message, failed_photos = icloud_sync.sync_photos(progress_callback)
        with sync_lock:
            sync_progress["status"] = "completed" if success else "error"
            sync_progress["message"] = message
            sync_progress["failed_photos"] = failed_photos
            if success:
                sync_progress["progress"] = 100
        
        # Обновляем индекс после успешной синхронизации
        if success:
            engine.update_index(app.config['IMAGES_DIR'])
            
    except Exception as e:
        with sync_lock:
            sync_progress["status"] = "error"
            sync_progress["message"] = str(e)

@app.route('/sync_icloud', methods=['POST'])
def start_sync():
    global icloud_sync
    
    if not icloud_sync:
        return jsonify({"success": False, "error": "Нет активного подключения"})
    
    thread = threading.Thread(target=lambda: start_sync_process())
    thread.start()
    
    return jsonify({"success": True, "message": "Синхронизация начата"})

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    page = request.json.get('page', 1)
    per_page = request.json.get('per_page', 30)
    
    logger.info(f"Поисковый запрос: '{query}' (страница {page}, элементов на странице {per_page})")
    
    if not query:
        logger.warning("Получен пустой поисковый запрос")
        return jsonify({"results": [], "has_more": False})
    
    try:
        # Получаем все результаты
        logger.debug(f"Выполнение поиска с параметрами: query='{query}', top_k=200")
        all_results = engine.search_images(query, top_k=200)
        
        # Разбиваем на страницы
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_results = all_results[start_idx:end_idx]
        
        logger.info(f"Найдено результатов: {len(all_results)}, отображается: {len(page_results)}")
        
        return jsonify({
            "results": page_results,
            "has_more": end_idx < len(all_results)
        })
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        return jsonify({"results": [], "has_more": False, "error": str(e)})

@app.route('/update_index', methods=['POST'])
def update_index():
    try:
        global indexing_progress
        logger.info("Начало процесса индексации")
        indexing_progress = {
            "status": "running",
            "current": 0,
            "total": len(os.listdir(app.config['IMAGES_DIR'])),
            "message": ""
        }
        
        def update_progress(current, total):
            global indexing_progress
            with sync_lock:
                # Проверяем валидность значений
                if total <= 0:
                    logger.warning("Получено некорректное значение total: %d", total)
                    return
                    
                if current > total:
                    logger.warning("current (%d) больше total (%d), корректируем", current, total)
                    current = total
                    
                indexing_progress["current"] = current
                indexing_progress["total"] = total
                progress = round((current / total * 100))
                
                logger.info(f"Прогресс индексации: {current}/{total} ({progress}%)")
                
                # Обновляем статус и сообщение
                if total == 0:
                    indexing_progress["status"] = "no_new_files"
                    indexing_progress["message"] = "Новых файлов для индексации не найдено"
                else:
                    indexing_progress["message"] = f"Обработано {current} из {total} файлов ({progress}%)"
                    if current >= total:
                        logger.info("Индексация завершена")
                        indexing_progress["status"] = "completed"
        
        # Запускаем индексацию в отдельном потоке
        def index_thread():
            try:
                logger.info("Запуск индексации в отдельном потоке")
                result = engine.update_index(progress_callback=update_progress)
                logger.info(f"Результат индексации: {'Новых файлов нет' if result else 'Файлы обработаны'}")
                if result:  # True если новых файлов нет
                    with sync_lock:
                        indexing_progress["status"] = "no_new_files"
                        indexing_progress["message"] = "Новых файлов для индексации не найдено"
            except Exception as e:
                logger.error(f"Ошибка в потоке индексации: {str(e)}")
                with sync_lock:
                    indexing_progress["status"] = "error"
                    indexing_progress["message"] = f"Ошибка: {str(e)}"
        
        threading.Thread(target=index_thread).start()
        logger.info("Поток индексации запущен")
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Ошибка при запуске индексации: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/indexing_status')
def indexing_status():
    """Возвращает текущий статус индексации"""
    global indexing_progress
    with sync_lock:
        # Если процесс индексации активен, но прогресс равен 100%, считаем его завершенным
        if indexing_progress["status"] == "running" and indexing_progress["current"] >= indexing_progress["total"]:
            indexing_progress["status"] = "completed"
        return jsonify(indexing_progress)

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    try:
        # Преобразуем путь в абсолютный
        abs_path = os.path.abspath(image_path)
        # Проверяем, что путь находится внутри разрешенной директории
        if os.path.commonpath([abs_path, os.path.abspath("Photos")]) == os.path.abspath("Photos"):
            return send_file(abs_path)
        else:
            return "Доступ запрещен", 403
    except Exception as e:
        return str(e), 404

@app.route('/media/<path:media_path>')
def serve_media(media_path):
    try:
        # Преобразуем путь в абсолютный
        abs_path = os.path.abspath(media_path)
        # Проверяем, что путь находится внутри разрешенной директории
        if os.path.commonpath([abs_path, os.path.abspath("Photos")]) != os.path.abspath("Photos"):
            return "Доступ запрещен", 403

        # Получаем расширение файла
        file_ext = os.path.splitext(abs_path)[1].lower()
        
        # Список поддерживаемых видео форматов
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        
        if file_ext in video_extensions:
            # Для видео используем потоковую передачу
            def generate():
                with open(abs_path, 'rb') as video_file:
                    data = video_file.read(1024*1024)  # Читаем по 1MB
                    while data:
                        yield data
                        data = video_file.read(1024*1024)
            
            # Определяем MIME-тип для видео
            mime_types = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.mkv': 'video/x-matroska'
            }
            
            return Response(
                generate(),
                mimetype=mime_types.get(file_ext, 'video/mp4'),
                headers={
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            # Для изображений используем обычную отправку файла
            return send_file(abs_path)
            
    except Exception as e:
        logger.error(f"Ошибка при отправке медиафайла {media_path}: {str(e)}")
        return str(e), 404

@app.route('/icloud/check_auth')
def check_auth():
    global icloud_sync
    try:
        if icloud_sync and icloud_sync.api:
            # Проверяем валидность сессии
            try:
                icloud_sync.api.devices
                return jsonify({"authenticated": True})
            except:
                return jsonify({"authenticated": False})
        return jsonify({"authenticated": False})
    except Exception as e:
        return jsonify({"authenticated": False, "error": str(e)})

@app.route('/icloud/stop_sync', methods=['POST'])
def stop_sync():
    global icloud_sync, sync_progress
    try:
        with sync_lock:
            if sync_progress["status"] == "syncing":
                sync_progress["status"] = "stopped"
                sync_progress["message"] = "Синхронизация остановлена пользователем"
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Синхронизация не выполняется"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/indexing_progress')
def indexing_progress_stream():
    return Response(generate_indexing_events(), mimetype='text/event-stream')

@app.route('/sync_progress')
def sync_progress_stream():
    return Response(generate_progress_events(), mimetype='text/event-stream')

@app.route('/check_index')
def check_index():
    try:
        index_exists = engine.check_index_exists()
        return jsonify({"exists": index_exists})
    except Exception as e:
        logger.error(f"Error checking index: {str(e)}")
        return jsonify({"exists": False, "error": str(e)})

@app.route('/stats')
def get_stats():
    try:
        # Считаем файлы изображений и видео
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.HEIC', '.PNG'}
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.MP4', '.MOV'}
        
        total_files = 0
        total_images = 0
        total_videos = 0
        
        if os.path.exists(app.config['IMAGES_DIR']):
            for f in os.listdir(app.config['IMAGES_DIR']):
                if os.path.isfile(os.path.join(app.config['IMAGES_DIR'], f)):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in image_extensions:
                        total_images += 1
                    elif ext in video_extensions:
                        total_videos += 1
        
        total_files = total_images + total_videos
        
        # Получаем время последнего обновления
        last_update_time = engine.get_last_update_time()
        if last_update_time == "Никогда":
            last_update = "Никогда" if request.accept_languages.best_match(['ru']) else "Never"
        else:
            try:
                # Парсим время из строки
                last_update_dt = datetime.strptime(last_update_time, "%a %b %d %H:%M:%S %Y")
                # Вычисляем разницу
                now = datetime.now()
                diff = now - last_update_dt
                
                # Форматируем разницу в зависимости от языка
                is_ru = request.accept_languages.best_match(['ru'])
                if diff.days > 0:
                    if diff.days == 1:
                        last_update = "вчера" if is_ru else "yesterday"
                    else:
                        last_update = f"{diff.days} дней назад" if is_ru else f"{diff.days} days ago"
                else:
                    hours = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    if hours > 0:
                        last_update = f"{hours} часов назад" if is_ru else f"{hours} hours ago"
                    elif minutes > 0:
                        last_update = f"{minutes} минут назад" if is_ru else f"{minutes} minutes ago"
                    else:
                        last_update = "только что" if is_ru else "just now"
            except Exception as e:
                logger.error(f"Ошибка при парсинге времени: {e}")
                last_update = last_update_time
        
        is_ru = request.accept_languages.best_match(['ru'])
        sync_status = ("Синхронизировано" if is_ru else "Synchronized") if icloud_sync and icloud_sync.is_authenticated() else ("Не синхронизировано" if is_ru else "Not synchronized")
        
        return jsonify({
            "total_files": total_files,
                "total_images": total_files,  # Теперь total_images включает все файлы
            "total_videos": total_videos,
            "last_update": last_update,
            "sync_status": sync_status
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        is_ru = request.accept_languages.best_match(['ru'])
        return jsonify({
            "total_files": 0,
            "total_images": 0,
            "total_videos": 0,
            "last_update": "Никогда" if is_ru else "Never",
            "sync_status": "Ошибка" if is_ru else "Error"
        })

@app.route('/stop_indexing', methods=['POST'])
def stop_indexing():
    global indexing_progress
    try:
        with sync_lock:
            if indexing_progress["status"] == "running":
                indexing_progress["status"] = "stopped"
                indexing_progress["message"] = "Индексация остановлена пользователем"
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Индексация не выполняется"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/restart_server', methods=['POST'])
def restart_server():
    try:
        # Запускаем новый процесс с текущим скриптом
        subprocess.Popen([sys.executable, __file__])
        # Завершаем текущий процесс
        os._exit(0)
    except Exception as e:
        logger.error(f"Ошибка при перезапуске сервера: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

def convert_heic_to_jpeg(heic_path):
    """Конвертирует HEIC файл в JPEG формат"""
    try:
        # Получаем путь для нового JPEG файла
        jpeg_path = os.path.splitext(heic_path)[0] + '.jpg'
        
        # Если JPEG файл уже существует, пропускаем конвертацию
        if os.path.exists(jpeg_path):
            return jpeg_path
            
        # Читаем HEIC файл
        heif_file = pillow_heif.read_heif(heic_path)
        # Конвертируем в PIL Image
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )
        
        # Сохраняем как JPEG
        image.save(jpeg_path, 'JPEG', quality=95)
        
        # Удаляем оригинальный HEIC файл
        os.remove(heic_path)
        
        logger.info(f"Успешно конвертирован файл {heic_path} в JPEG")
        return jpeg_path
    except Exception as e:
        logger.error(f"Ошибка при конвертации {heic_path}: {str(e)}")
        return None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False) 