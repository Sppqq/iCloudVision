# 🔍 iCloudVision

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![iCloud](https://img.shields.io/badge/iCloud-3693F3?style=for-the-badge&logo=icloud&logoColor=white)](https://www.icloud.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Умный AI-поиск по вашим фотографиям в iCloud**

[🇷🇺 Русская версия](README.ru.md) | [🇬🇧 Английская версия](README.md)

<img src="https://raw.githubusercontent.com/Sppqq/iCloudVision/main/static/preview.gif" alt="iCloudVision Demo" width="600"/>

</div>

## ✨ Возможности

🔄 **Синхронизация с iCloud**
- Автоматическая синхронизация фотографий с вашим iCloud
- Поддержка двухфакторной аутентификации
- Отслеживание прогресса в реальном времени

🔍 **Умный поиск**
- Поиск фотографий с помощью описания на естественном языке
- Работает на основе современных AI-моделей для понимания изображений
- Мгновенные результаты благодаря кэшированию индекса

📸 **Обработка изображений**
- Поддержка форматов HEIC/HEIF с автоматической конвертацией
- Оптимизированная обработка больших коллекций
- Многопоточная обработка для максимальной производительности

## 🚀 Быстрый старт

### 1️⃣ Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/Sppqq/iCloudVision.git
cd iCloudVision

# Установите зависимости
pip install -r requirements.txt
```

### 2️⃣ Запуск

```bash
python app.py
```

Откройте браузер и перейдите по адресу `http://localhost:5000`

## 💡 Как использовать

1. **Авторизация**
   - Войдите в свой аккаунт iCloud
   - Подтвердите двухфакторную аутентификацию (если включена)

2. **Синхронизация**
   - Дождитесь завершения начальной синхронизации
   - Следите за прогрессом в реальном времени

3. **Поиск**
   - Введите текстовое описание фотографии, которую ищете
   - Используйте естественный язык для описания
   - Примеры запросов:
     - "Закат на пляже"
     - "Фотографии с дня рождения"
     - "Селфи в горах"

## 🛠 Технологии

- **Бэкенд**: Flask, PyiCloud
- **AI**: CLIP (OpenAI)
- **Обработка изображений**: Pillow, pillow-heif
- **Фронтенд**: JavaScript, Server-Sent Events
- **Многопоточность**: Python Threading

## 📋 Системные требования

- Python 3.7 или выше
- Microsoft Visual C++ Build Tools (для Windows)
- Стабильное интернет-соединение
- Достаточно места на диске для хранения фотографий

## 🔒 Безопасность

- ✅ Безопасное хранение учетных данных
- ✅ Поддержка двухфакторной аутентификации iCloud
- ✅ Локальное хранение индекса изображений
- ✅ Шифрование сессий

## 🤝 Участие в разработке

Мы приветствуем ваш вклад в проект!

1. Сделайте форк репозитория
2. Создайте ветку для ваших изменений
3. Внесите изменения и создайте Pull Request

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. Подробности смотрите в файле [LICENSE](LICENSE).

## 🙋‍♂️ Поддержка

Если у вас есть вопросы или проблемы:
- Создайте Issue в репозитории
- Напишите нам на sppqq@duck.com

---

<div align="center">
Сделано с ❤️ для сообщества
</div> 