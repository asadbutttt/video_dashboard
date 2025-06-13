import os
from pathlib import Path

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///video_dashboard.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    
    # Celery settings
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # File paths
    BASE_DIR = Path(__file__).parent

    


    INPUT_FOLDER = BASE_DIR / 'INPUT'
    OUTPUT_FOLDER = BASE_DIR / 'OUTPUT'
    
    # Video processing settings
    SEGMENT_DURATION = 10  # seconds
    QUALITIES = {
        '720p': {'resolution': '1280:720', 'bitrate': '2500k'},
        '480p': {'resolution': '854:480', 'bitrate': '1000k'},
        '360p': {'resolution': '640:360', 'bitrate': '600k'}
    }
    
    # Supported video formats
    SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    @staticmethod
    def init_app(app):
        # Create directories if they don't exist
        Config.INPUT_FOLDER.mkdir(exist_ok=True)
        Config.OUTPUT_FOLDER.mkdir(exist_ok=True)
