import os
from pathlib import Path
import base64
from cryptography.fernet import Fernet

# Генерируем ключ правильного формата
ENCRYPTION_KEY = Fernet.generate_key()

# Путь к файлу с сессией
SESSION_FILE = Path("icloud_session.dat") 