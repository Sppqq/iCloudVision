# iCloudVision

🔍 Smart semantic search for your iCloud photos

[Русская версия](README.ru.md)

## Features
- Automatic photo synchronization with iCloud
- Semantic image search using natural language descriptions
- HEIC format support with automatic conversion
- Real-time progress tracking web interface
- Multi-threaded processing for fast synchronization
- Image index caching for optimized search performance

## Technologies
- Flask web interface
- CLIP model for semantic search
- PyiCloud for iCloud API integration
- Pillow and pillow-heif for image processing
- Threading for asynchronous operations

## Installation
1. Clone the repository:
```bash
git clone https://github.com/Sppqq/iCloudVision.git
cd iCloudVision
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage
1. Start the web server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`
3. Log in to your iCloud account
4. After synchronization, use search to find your photos

## Security
- iCloud two-factor authentication support
- Secure credentials storage
- Local image index storage

## License
MIT License 