# Video Processing Dashboard

A Python Flask-based web application for converting video files to HLS (HTTP Live Streaming) format with multiple quality variants. Designed for non-technical users with a simple, intuitive interface.

## Features

- **Multi-Quality Conversion**: Automatically converts videos to 720p, 480p, and 360p (based on source resolution)
- **Smart Resolution Detection**: Only converts to lower resolutions to avoid upscaling
- **Queue Management**: Process one video at a time with queue system
- **Real-time Progress**: Live updates via WebSocket
- **Simple Interface**: Color-coded status system (🟡 NEW → 🟠 QUEUED → 🔴 IN PROGRESS → 🟢 DONE)
- **Unique Movie IDs**: Each video gets a 6-8 digit identifier (MOV######)
- **HLS Output**: Creates adaptive bitrate streaming files with master playlist
- **File Organization**: Clean folder structure for INPUT and OUTPUT

## Architecture

```
video_dashboard/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── routes.py            # Web routes and API endpoints
│   ├── tasks.py             # Celery background tasks
│   └── utils.py             # Utility functions
├── static/
│   ├── css/style.css        # Custom styles
│   └── js/app.js            # Frontend JavaScript
├── templates/
│   ├── base.html            # Base template
│   └── index.html           # Dashboard template
├── INPUT/                   # Source video files
├── OUTPUT/                  # Converted HLS files
├── config.py                # Configuration
├── requirements.txt         # Python dependencies
├── run.py                   # Flask application entry point
└── celery_worker.py         # Celery worker entry point
```

## Prerequisites

- Python 3.8+
- FFmpeg (for video processing)
- Redis (for Celery message broker)

### Installing FFmpeg

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract and add to PATH
3. Verify: `ffmpeg -version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Installing Redis

**Windows:**
1. Download Redis for Windows
2. Install and start Redis server
3. Default runs on localhost:6379

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

## Installation

1. **Clone or download the project:**
```bash
git clone <repository-url>
cd video_dashboard
```

2. **Create virtual environment:**
```bash
python -m venv venv
```

3. **Activate virtual environment:**

Windows:
```bash
venv\Scripts\activate
```

Linux/macOS:
```bash
source venv/bin/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Verify FFmpeg installation:**
```bash
ffmpeg -version
```

6. **Start Redis server** (if not already running)

## Usage

### Starting the Application

You need to run three components:

1. **Start Redis** (if not already running)

2. **Start Celery Worker** (in one terminal):
```bash
celery -A celery_worker.celery worker --loglevel=info
```

3. **Start Flask App** (in another terminal):
```bash
python run.py
```

4. **Open your browser** and go to: http://localhost:5000

### Using the Dashboard

1. **Add Videos**: Copy your video files to the `INPUT` folder
2. **Scan**: Click "Scan INPUT Folder" to detect new videos
3. **Convert**: Click the "Convert" button for each movie you want to process
4. **Monitor**: Watch real-time progress updates
5. **Access Files**: Converted HLS files will be in `OUTPUT/{movie_id}/`

### Output Structure

```
OUTPUT/
├── MOV123456/
│   ├── master.m3u8          # Master playlist (adaptive bitrate)
│   ├── 720p/
│   │   ├── playlist.m3u8    # 720p playlist
│   │   ├── segment_000.ts   # Video segments
│   │   └── segment_001.ts
│   ├── 480p/
│   │   ├── playlist.m3u8
│   │   └── segments...
│   └── 360p/
│       ├── playlist.m3u8
│       └── segments...
```

## Configuration

Edit `config.py` to customize:

- **Segment Duration**: Default 10 seconds
- **Quality Settings**: Bitrates and resolutions
- **Supported Formats**: Video file extensions
- **Database**: SQLite by default
- **Redis**: Connection settings

## Status System

- 🟡 **NEW**: File detected, ready for conversion
- 🔵 **QUEUED**: Added to conversion queue
- 🔴 **IN PROGRESS**: Currently converting
- 🟢 **DONE**: Conversion completed successfully
- ⚫ **ERROR**: Conversion failed

## Conversion Logic

The system intelligently determines target qualities based on source resolution:

- **1080p+ source** → Convert to 720p, 480p, 360p
- **720p source** → Convert to 480p, 360p (skip 720p)
- **480p source** → Convert to 360p only
- **360p or lower** → Keep original (no conversion needed)

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Ensure FFmpeg is installed and in PATH
   - Test with `ffmpeg -version`

2. **Redis connection error**
   - Start Redis server
   - Check Redis is running on localhost:6379

3. **Celery worker not starting**
   - Ensure Redis is running
   - Check Python virtual environment is activated

4. **Videos not detected**
   - Check files are in INPUT folder
   - Verify file extensions are supported
   - Click "Scan INPUT Folder" button

5. **Conversion fails**
   - Check FFmpeg installation
   - Verify video file is not corrupted
   - Check disk space for OUTPUT folder

### Logs

- Flask app logs appear in terminal
- Celery worker logs show conversion progress
- Check browser console for frontend errors

## Development

### Adding New Features

1. **Models**: Add database models in `app/models.py`
2. **Routes**: Add API endpoints in `app/routes.py`
3. **Tasks**: Add background tasks in `app/tasks.py`
4. **Frontend**: Modify templates and static files

### Database Migrations

The app uses SQLite and creates tables automatically. For production, consider using PostgreSQL and Flask-Migrate.

## Production Deployment

For production use:

1. **Use PostgreSQL** instead of SQLite
2. **Configure Redis** with persistence
3. **Use Gunicorn** instead of Flask dev server
4. **Set up reverse proxy** (Nginx)
5. **Configure SSL/HTTPS**
6. **Set environment variables** for secrets
7. **Use process manager** (systemd, supervisor)

## License

This project is open source. Feel free to modify and distribute.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all prerequisites are installed
3. Check logs for error messages
