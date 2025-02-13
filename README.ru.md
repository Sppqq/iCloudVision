# 🔍 iCloudVision

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![iCloud](https://img.shields.io/badge/iCloud-3693F3?style=for-the-badge&logo=icloud&logoColor=white)](https://www.icloud.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Умный поиск по вашим фотографиям iCloud с использованием искусственного интеллекта**

[🇬🇧 English](README.md) | [🇷🇺 Русский](README.ru.md)

<img src="https://raw.githubusercontent.com/Sppqq/iCloudVision/main/static/preview.gif" alt="iCloudVision Demo" width="600"/>

</div>

## Возможности
- Автоматическая синхронизация фотографий с iCloud
- Семантический поиск изображений по текстовому описанию
- Поддержка HEIC формата с автоматической конвертацией
- Веб-интерфейс с отслеживанием прогресса в реальном времени
- Многопоточная обработка для быстрой синхронизации
- Кэширование индекса изображений для оптимизации поиска

## Технологии
- Flask для веб-интерфейса
- CLIP модель для семантического поиска
- PyiCloud для работы с iCloud API
- Pillow и pillow-heif для обработки изображений
- Threading для асинхронных операций

## Требования
- Python 3.7+
- Microsoft Visual C++ Build Tools (для Windows)
- Подключение к интернету (для синхронизации с iCloud)
- Достаточно места на диске для хранения фотографий

## Установка

### 1. Подготовка системы

#### Windows
1. Установите [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - При установке выберите "Средства сборки C++"
   - После установки может потребоваться перезагрузка компьютера

#### Linux/macOS
- Установите необходимые инструменты сборки:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install build-essential python3-dev
  
  # macOS
  xcode-select --install
  ```

### 2. Установка проекта
1. Клонируйте репозиторий:
```bash
git clone https://github.com/Sppqq/iCloudVision.git
cd iCloudVision
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Использование
1. Запустите веб-сервер:
```bash
python app.py
```

2. Откройте браузер и перейдите по адресу `http://localhost:5000`
3. Войдите в свой аккаунт iCloud
4. После синхронизации используйте поиск для нахождения нужных фотографий

### Поиск изображений
- Для лучших результатов используйте конкретные описания на английском языке
- Поиск поддерживает как простые запросы ("cat", "beach"), так и сложные описания ("black cat on white sofa")

## Безопасность
- Поддержка двухфакторной аутентификации iCloud
- Безопасное хранение учетных данных
- Локальное хранение индекса изображений

## Устранение проблем

### Windows
- Если при установке возникает ошибка с `annoy` или другими библиотеками, убедитесь, что Microsoft Visual C++ Build Tools установлен корректно
- Попробуйте перезапустить командную строку после установки Build Tools

### Linux/macOS
- При проблемах с компиляцией убедитесь, что установлены все необходимые инструменты разработки

## Лицензия
MIT License 