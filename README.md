# 🔍 iCloudVision

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![iCloud](https://img.shields.io/badge/iCloud-3693F3?style=for-the-badge&logo=icloud&logoColor=white)](https://www.icloud.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Smart AI-Powered Search Through Your iCloud Photos**

[🇷🇺 Russian version](README.ru.md) | [🇬🇧 English version](README.md)

<img src="https://raw.githubusercontent.com/Sppqq/iCloudVision/main/static/preview.gif" alt="iCloudVision Demo" width="600"/>

</div>

## ✨ Features

🔄 **iCloud Sync**
- Automatic photo synchronization with your iCloud
- Two-factor authentication support
- Real-time progress tracking

🔍 **Smart Search**
- Search photos using natural language descriptions
- Powered by state-of-the-art AI models for image understanding
- Instant results through index caching

📸 **Image Processing**
- HEIC/HEIF format support with automatic conversion
- Optimized handling of large collections
- Multi-threaded processing for maximum performance

## 🚀 Quick Start

### 1️⃣ Installation

```bash
# Clone the repository
git clone https://github.com/Sppqq/iCloudVision.git
cd iCloudVision

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Launch

```bash
python app.py
```

Open your browser and navigate to `http://localhost:5000`

## 💡 How to Use

1. **Authorization**
   - Log in to your iCloud account
   - Confirm two-factor authentication (if enabled)

2. **Synchronization**
   - Wait for initial synchronization to complete
   - Monitor progress in real-time

3. **Search**
   - Enter text description of the photo you're looking for
   - Use natural language for descriptions
   - Example queries:
     - "Sunset at the beach"
     - "Birthday party photos"
     - "Selfie in mountains"

## 🛠 Technologies

- **Backend**: Flask, PyiCloud
- **AI**: CLIP (OpenAI)
- **Image Processing**: Pillow, pillow-heif
- **Frontend**: JavaScript, Server-Sent Events
- **Concurrency**: Python Threading

## 📋 System Requirements

- Python 3.7 or higher
- Microsoft Visual C++ Build Tools (for Windows)
- Stable internet connection
- Sufficient disk space for photo storage

## 🔒 Security

- ✅ Secure credentials storage
- ✅ iCloud two-factor authentication support
- ✅ Local image index storage
- ✅ Session encryption

## 🤝 Contributing

We welcome your contributions to the project!

1. Fork the repository
2. Create a branch for your changes
3. Make changes and create a Pull Request

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

If you have questions or issues:
- Create an Issue in the repository
- Email us at sppqq@duck.com

---

<div align="center">
Made with ❤️ for the community
</div> 