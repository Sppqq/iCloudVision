# iCloudVision

🔍 Smart search through your iCloud photos

[Русская версия](README.ru.md)

## Features
- Automatic photo synchronization with iCloud
- Semantic image search using text descriptions
- HEIC format support with automatic conversion
- Web interface with real-time progress tracking
- Multi-threaded processing for fast synchronization
- Image index caching for search optimization

## Technologies
- Flask for web interface
- CLIP model for semantic search
- PyiCloud for iCloud API integration
- Pillow and pillow-heif for image processing
- Threading for asynchronous operations

## Requirements
- Python 3.7+
- Microsoft Visual C++ Build Tools (for Windows)
- Internet connection (for iCloud sync)
- Sufficient disk space for photo storage

## Installation

### 1. System Preparation

#### Windows
1. Install [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - During installation, select "C++ build tools"
   - A system restart might be required after installation

#### Linux/macOS
- Install required build tools:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install build-essential python3-dev
  
  # macOS
  xcode-select --install
  ```

### 2. Project Installation
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

2. Open your browser and go to `http://localhost:5000`
3. Log in to your iCloud account
4. After synchronization, use search to find the photos you need

### Image Search
- For best results, use specific descriptions in English
- Search supports both simple queries ("cat", "beach") and complex descriptions ("black cat on white sofa")

## Security
- iCloud two-factor authentication support
- Secure credentials storage
- Local image index storage

## Troubleshooting

### Windows
- If you encounter errors with `annoy` or other libraries during installation, make sure Microsoft Visual C++ Build Tools is properly installed
- Try restarting your command prompt after installing Build Tools

### Linux/macOS
- If you experience compilation issues, ensure all necessary development tools are installed

## License
MIT License 