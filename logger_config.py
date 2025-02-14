import logging
import logging.handlers
import os
import sys
from datetime import datetime
import colorama
from colorama import Fore, Style, Back
import threading

# Инициализация colorama для Windows
colorama.init()

# Создаем директорию для логов, если её нет
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Формат логов для файла (более подробный)
file_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d - %(threadName)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ColoredFormatter(logging.Formatter):
    """Форматтер, который добавляет цвета в консольный вывод"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    HIGHLIGHTS = {
        'ERROR': Back.RED + Fore.WHITE,
        'CRITICAL': Back.RED + Fore.WHITE + Style.BRIGHT
    }

    def format(self, record):
        # Сохраняем оригинальные значения
        orig_levelname = record.levelname
        orig_name = record.name
        orig_msg = record.msg
        orig_threadName = record.threadName
        
        # Добавляем цвет к уровню логирования
        if record.levelname in self.HIGHLIGHTS:
            record.levelname = f"{self.HIGHLIGHTS[record.levelname]}{record.levelname:^8}{Style.RESET_ALL}"
        elif record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname:^8}{Style.RESET_ALL}"
        
        # Добавляем цвет к имени логгера
        record.name = f"{Fore.BLUE}{record.name:12}{Style.RESET_ALL}"
        
        # Добавляем цвет к времени
        record.asctime = f"{Fore.MAGENTA}{self.formatTime(record, self.datefmt)}{Style.RESET_ALL}"
        
        # Добавляем цвет к имени потока
        record.threadName = f"{Fore.YELLOW}{record.threadName:15}{Style.RESET_ALL}"
        
        # Форматируем сообщение
        if record.levelname.strip() in ['ERROR', 'CRITICAL']:
            record.msg = f"{self.HIGHLIGHTS[orig_levelname]}{record.msg}{Style.RESET_ALL}"
        
        # Форматируем сообщение с помощью родительского класса
        formatted_message = super().format(record)
        
        # Восстанавливаем оригинальные значения
        record.levelname = orig_levelname
        record.name = orig_name
        record.msg = orig_msg
        record.threadName = orig_threadName
        
        return formatted_message

# Создаем форматтер для консоли с улучшенным форматированием
console_formatter = ColoredFormatter(
    '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def setup_logger(name):
    """Настраивает и возвращает логгер с указанным именем"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Проверяем, не были ли уже добавлены хендлеры
    if not logger.handlers:
        # Хендлер для записи в файл
        current_date = datetime.now().strftime('%Y-%m-%d')
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f'{current_date}.log'),
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Хендлер для вывода в консоль
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Добавляем хендлеры к логгеру
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Устанавливаем имя потока по умолчанию
        threading.current_thread().name = 'MainThread'
    
    return logger 