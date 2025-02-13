from flask import Flask, render_template, jsonify, request, send_file
import os
from search_images import ImageSearchEngine
from pathlib import Path
from icloud_sync import ICloudSync
import threading
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Отключаем автоматическую перезагрузку при изменении файлов
app.config['DEBUG'] = True
app.config['USE_RELOADER'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False

engine = ImageSearchEngine()
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
        sync_progress["progress"] = progress
        sync_progress["downloaded"] = downloaded
        sync_progress["total"] = total
        sync_progress["new_photos"] = new_photos
        sync_progress["message"] = f"Загружено {downloaded} из {total} фотографий. Новых: {new_photos}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/icloud/connect', methods=['POST'])
def icloud_connect():
    global icloud_sync
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        logger.error("Не указан логин или пароль")
        return jsonify({"success": False, "error": "Не указан логин или пароль"})
    
    logger.info("Попытка подключения к iCloud...")
    icloud_sync = ICloudSync(username, password)
    success, message = icloud_sync.connect()
    
    if success:
        logger.info("Успешное подключение к iCloud")
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
    return jsonify({"success": success})

@app.route('/icloud/sync_status')
def sync_status():
    global sync_progress
    with sync_lock:
        return jsonify(sync_progress)

@app.route('/icloud/sync', methods=['POST'])
def start_sync():
    global icloud_sync, sync_progress
    
    if not icloud_sync:
        return jsonify({"success": False, "error": "Нет активного подключения"})
    
    with sync_lock:
        if sync_progress["status"] == "syncing":
            return jsonify({"success": False, "error": "Синхронизация уже выполняется"})
        sync_progress = {
            "status": "syncing",
            "progress": 0,
            "message": "Начинаем синхронизацию...",
            "total": 0,
            "downloaded": 0,
            "new_photos": 0,
            "failed_photos": []
        }
    
    def sync_thread():
        global sync_progress
        try:
            success, message, failed_photos = icloud_sync.sync_photos(progress_callback)
            with sync_lock:
                sync_progress["status"] = "completed" if success else "error"
                sync_progress["message"] = message
                sync_progress["failed_photos"] = failed_photos
            
            # Обновляем индекс после успешной синхронизации
            if success:
                engine.update_index("Photos")
                
        except Exception as e:
            with sync_lock:
                sync_progress["status"] = "error"
                sync_progress["message"] = str(e)
    
    thread = threading.Thread(target=sync_thread)
    thread.start()
    
    return jsonify({"success": True, "message": "Синхронизация начата"})

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    page = request.json.get('page', 1)
    per_page = request.json.get('per_page', 30)
    
    if not query:
        return jsonify({"results": [], "has_more": False})
    
    # Получаем все результаты
    all_results = engine.search_images(query, top_k=200)  # Увеличиваем лимит
    
    # Разбиваем на страницы
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = all_results[start_idx:end_idx]
    
    return jsonify({
        "results": page_results,
        "has_more": end_idx < len(all_results)
    })

@app.route('/update_index', methods=['POST'])
def update_index():
    global indexing_progress
    try:
        indexing_progress["status"] = "running"
        engine.update_index("Photos", progress_callback=update_indexing_progress)
        indexing_progress["status"] = "completed"
        return jsonify({"success": True})
    except Exception as e:
        indexing_progress["status"] = "error"
        indexing_progress["message"] = str(e)
        return jsonify({"success": False, "error": str(e)})

@app.route('/indexing_status')
def indexing_status():
    return jsonify(indexing_progress)

def update_indexing_progress(current, total):
    global indexing_progress
    indexing_progress["current"] = current
    indexing_progress["total"] = total
    indexing_progress["message"] = f"Обработано {current} из {total} изображений"

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False) 