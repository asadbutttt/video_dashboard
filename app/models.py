from app import db
from datetime import datetime
import random
import string
import json

class Movie(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    source_resolution = db.Column(db.String(20))
    status = db.Column(db.String(20), default='NEW')  # NEW, QUEUED, IN_PROGRESS, DONE, ERROR
    created_at = db.Column(db.DateTime, default=datetime.now)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    overall_progress = db.Column(db.Integer, default=0)
    quality_progress = db.Column(db.Text, default='{}')  # JSON string
    error_message = db.Column(db.Text)
    
    # Relationships
    quality_variants = db.relationship('QualityVariant', backref='movie', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Movie, self).__init__(**kwargs)
        if not self.id:
            self.id = self.generate_movie_id()
    
    @staticmethod
    def generate_movie_id():
        """Generate a unique 6-8 digit movie ID"""
        while True:
            # Generate 6-8 digit ID starting with 'MOV'
            digits = ''.join(random.choices(string.digits, k=random.randint(5, 6)))
            movie_id = f"MOV{digits}"
            
            # Check if ID already exists
            if not Movie.query.filter_by(id=movie_id).first():
                return movie_id
    
    def get_quality_progress(self):
        """Get quality progress as dictionary"""
        try:
            return json.loads(self.quality_progress) if self.quality_progress else {}
        except:
            return {}
    
    def set_quality_progress(self, progress_dict):
        """Set quality progress from dictionary"""
        self.quality_progress = json.dumps(progress_dict)
    
    def get_target_qualities(self):
        """Determine target qualities based on source resolution"""
        if not self.source_resolution:
            return ['720p', '480p', '360p']  # Default if unknown
        
        height = int(self.source_resolution.split('x')[1]) if 'x' in self.source_resolution else 1080
        
        if height >= 1080:
            return ['720p', '480p', '360p']
        elif height >= 720:
            return ['480p', '360p']
        elif height >= 480:
            return ['360p']
        else:
            return []  # Keep original only
    
    def update_overall_progress(self):
        """Calculate overall progress from quality variants"""
        variants = self.quality_variants
        if not variants:
            self.overall_progress = 0
            return
        
        total_progress = sum(variant.progress for variant in variants)
        self.overall_progress = total_progress // len(variants)
    
    def to_dict(self):
        """Convert movie to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'source_resolution': self.source_resolution,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'overall_progress': self.overall_progress,
            'target_qualities': self.get_target_qualities(),
            'quality_variants': [variant.to_dict() for variant in self.quality_variants]
        }

class QualityVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(8), db.ForeignKey('movie.id'), nullable=False)
    quality = db.Column(db.String(10), nullable=False)  # 720p, 480p, 360p
    status = db.Column(db.String(20), default='PENDING')  # PENDING, IN_PROGRESS, DONE, ERROR
    progress = db.Column(db.Integer, default=0)  # 0-100
    file_path = db.Column(db.String(500))
    segment_count = db.Column(db.Integer, default=0)
    duration = db.Column(db.Float)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        """Convert quality variant to dictionary for JSON serialization"""
        return {
            'quality': self.quality,
            'status': self.status,
            'progress': self.progress,
            'segment_count': self.segment_count,
            'duration': self.duration
        }

class ConversionQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(8), db.ForeignKey('movie.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    movie = db.relationship('Movie', backref='queue_entry')
    
    @staticmethod
    def get_next_position():
        """Get the next position in queue"""
        last_position = db.session.query(db.func.max(ConversionQueue.position)).scalar()
        return (last_position or 0) + 1
    
    @staticmethod
    def get_queue():
        """Get all movies in queue ordered by position"""
        return ConversionQueue.query.order_by(ConversionQueue.position).all()
