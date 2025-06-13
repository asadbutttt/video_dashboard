from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess
import threading
import time
from pathlib import Path
import ffmpeg
from datetime import datetime, timezone
import random
import string
import json

# Simple Flask app without Celery
app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-video-dashboard'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_video_dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuration
BASE_DIR = Path(__file__).parent
INPUT_FOLDER = BASE_DIR / 'INPUT'
OUTPUT_FOLDER = BASE_DIR / 'OUTPUT'
SEGMENT_DURATION = 10
QUALITIES = {
    '720p': {'resolution': '1280:720', 'bitrate': '2500k'},
    '480p': {'resolution': '854:480', 'bitrate': '1000k'},
    '360p': {'resolution': '640:360', 'bitrate': '600k'}
}
SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']

# Create directories
INPUT_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Global conversion status
conversion_status = {}

# Database Models
class Movie(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    source_resolution = db.Column(db.String(20))
    status = db.Column(db.String(20), default='NEW')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    overall_progress = db.Column(db.Integer, default=0)
    
    def __init__(self, **kwargs):
        super(Movie, self).__init__(**kwargs)
        if not self.id:
            self.id = self.generate_movie_id()
    
    @staticmethod
    def generate_movie_id():
        while True:
            digits = ''.join(random.choices(string.digits, k=random.randint(5, 6)))
            movie_id = f"MOV{digits}"
            if not Movie.query.filter_by(id=movie_id).first():
                return movie_id
    
    def get_target_qualities(self):
        if not self.source_resolution:
            return ['720p', '480p', '360p']
        
        height = int(self.source_resolution.split('x')[1]) if 'x' in self.source_resolution else 1080
        
        if height >= 1080:
            return ['720p', '480p', '360p']
        elif height >= 720:
            return ['480p', '360p']
        elif height >= 480:
            return ['360p']
        else:
            return []

# Utility Functions
def get_video_info(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            duration = float(probe['format']['duration'])
            
            return {
                'resolution': f"{width}x{height}",
                'width': width,
                'height': height,
                'duration': duration
            }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def scan_input_folder():
    video_files = []
    
    if not INPUT_FOLDER.exists():
        return video_files
    
    for file_path in INPUT_FOLDER.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
            try:
                file_size = file_path.stat().st_size
                video_info = get_video_info(str(file_path))
                
                video_files.append({
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'file_size': file_size,
                    'video_info': video_info
                })
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
    
    return video_files

# def convert_video_simple(movie_id):
#     """Simple video conversion with better error handling"""
#     global conversion_status
    
#     with app.app_context():
#         try:
#             movie = db.session.get(Movie, movie_id)  # Fixed SQLAlchemy call
#             if not movie:
#                 return
            
#             # Update status
#             movie.status = 'IN_PROGRESS'
#             movie.overall_progress = 0
#             db.session.commit()
#             conversion_status[movie_id] = {'status': 'IN_PROGRESS', 'progress': 0}
            
#             # Check if input file exists
#             if not os.path.exists(movie.file_path):
#                 raise FileNotFoundError(f"Input file not found: {movie.file_path}")
            
#             # Get video info
#             if not movie.source_resolution:
#                 video_info = get_video_info(movie.file_path)
#                 if video_info:
#                     movie.source_resolution = video_info['resolution']
#                     db.session.commit()
            
#             # Create output directory
#             output_dir = OUTPUT_FOLDER / movie_id
#             output_dir.mkdir(exist_ok=True)
            
#             target_qualities = movie.get_target_qualities()
            
#             if not target_qualities:
#                 movie.status = 'DONE'
#                 movie.overall_progress = 100
#                 movie.completed_at = datetime.now(timezone.utc)
#                 db.session.commit()
#                 conversion_status[movie_id] = {'status': 'DONE', 'progress': 100}
#                 return
            
#             # Convert each quality
#             completed_qualities = []
#             total_qualities = len(target_qualities)
            
#             for i, quality in enumerate(target_qualities):
#                 try:
#                     quality_config = QUALITIES[quality]
#                     quality_dir = output_dir / quality
#                     quality_dir.mkdir(exist_ok=True)
#                     playlist_path = quality_dir / 'playlist.m3u8'
                    
#                     # Update progress
#                     progress = int((i / total_qualities) * 90)
#                     movie.overall_progress = progress
#                     db.session.commit()
#                     conversion_status[movie_id] = {'status': 'IN_PROGRESS', 'progress': progress}
                    
#                     print(f"Converting {movie.filename} to {quality}...")
                    
#                     # More detailed FFmpeg command
#                     try:
#                         input_stream = ffmpeg.input(movie.file_path)

#                         # Use the following line to create a basic HLS output
#                         # output_stream = input_stream.output(
#                         #     str(playlist_path),
#                         #     vf=f"scale={quality_config['resolution']}",
#                         #     vcodec='libx264',
#                         #     vb=quality_config['bitrate'],
#                         #     acodec='aac',
#                         #     ab='128k',
#                         #     f='hls',
#                         #     hls_time=SEGMENT_DURATION,
#                         #     hls_playlist_type='vod',
#                         #     hls_segment_filename=str(quality_dir / 'segment_%03d.ts'),
#                         #     hls_flags='independent_segments'
#                         # )

#                         # ADD THESE TO FORCE CONSISTENT SEGMENTS using Claude troubleshooting
#                         output_stream = input_stream.output(
#                             str(playlist_path),
#                             vf=f"scale={quality_config['resolution']}",
#                             vcodec='libx264',
#                             vb=quality_config['bitrate'],
#                             acodec='aac',
#                             ab='128k',
#                             f='hls',
#                             hls_time=SEGMENT_DURATION,
#                             hls_playlist_type='vod',
#                             hls_segment_filename=str(quality_dir / 'segment_%03d.ts'),
#                             hls_flags='independent_segments',
    
#                             # ADD THESE TO FORCE CONSISTENT SEGMENTS:
#                             force_key_frames=f'expr:gte(t,n_forced*{SEGMENT_DURATION})',  # Force keyframes every 10 seconds
#                             g=f'{SEGMENT_DURATION * 25}',  # GOP size (assuming 25fps)
#                             keyint_min=f'{SEGMENT_DURATION * 25}',  # Minimum keyframe interval
#                             sc_threshold=0,  # Disable scene change detection
#                         )
                        
#                         # Run with error capture
#                         ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
#                         completed_qualities.append(quality)
#                         print(f"Completed {quality} conversion")
                        
#                     except ffmpeg.Error as e:
#                         error_message = e.stderr.decode('utf-8') if e.stderr else "Unknown FFmpeg error"
#                         print(f"FFmpeg error for {quality}: {error_message}")
#                         # Continue with other qualities
                        
#                 except Exception as e:
#                     print(f"Error converting {quality}: {e}")
            
#             # Create master playlist
#             if completed_qualities:
#                 create_master_playlist(movie_id, completed_qualities)
#                 print(f"Created master playlist with qualities: {completed_qualities}")
            
#             # Update final status
#             movie.status = 'DONE' if completed_qualities else 'ERROR'
#             movie.overall_progress = 100
#             movie.completed_at = datetime.now(timezone.utc)
#             db.session.commit()
            
#             conversion_status[movie_id] = {
#                 'status': movie.status, 
#                 'progress': 100,
#                 'completed_qualities': completed_qualities
#             }
            
#             print(f"Conversion completed for {movie.filename} - Status: {movie.status}")
            
#         except Exception as e:
#             print(f"Error in conversion: {e}")
#             try:
#                 movie = db.session.get(Movie, movie_id)  # Fixed SQLAlchemy call
#                 if movie:
#                     movie.status = 'ERROR'
#                     movie.completed_at = datetime.now()
#                     db.session.commit()
#             except:
#                 pass
#             conversion_status[movie_id] = {'status': 'ERROR', 'progress': 0}

import threading
import time
import re
from datetime import datetime

def convert_video_simple(movie_id):
    """Simple video conversion with real-time progress updates"""
    global conversion_status
    
    with app.app_context():
        try:
            movie = db.session.get(Movie, movie_id)
            if not movie:
                return
            
            # Update status
            movie.status = 'IN_PROGRESS'
            movie.overall_progress = 0
            db.session.commit()
            conversion_status[movie_id] = {'status': 'IN_PROGRESS', 'progress': 0}
            
            print(f"\n🎬 Starting conversion for Movie ID: {movie_id}")
            print(f"📁 File: {movie.filename}")
            print("=" * 60)
            
            # Get video info including duration
            video_info = get_video_info(movie.file_path)
            total_duration = video_info.get('duration', 0) if video_info else 0
            
            if not movie.source_resolution and video_info:
                movie.source_resolution = video_info['resolution']
                db.session.commit()
            
            # Create output directory
            output_dir = OUTPUT_FOLDER / movie_id
            output_dir.mkdir(exist_ok=True)
            
            target_qualities = movie.get_target_qualities()
            
            if not target_qualities:
                movie.status = 'DONE'
                movie.overall_progress = 100
                movie.completed_at = datetime.now(timezone.utc)
                db.session.commit()
                conversion_status[movie_id] = {'status': 'DONE', 'progress': 100}
                return
            
            # Start progress monitoring thread
            progress_data = {'current_progress': 0, 'current_quality': '', 'stop_monitoring': False}
            monitor_thread = threading.Thread(
                target=monitor_progress, 
                args=(movie_id, movie.filename, progress_data),
                daemon=True
            )
            monitor_thread.start()
            
            # Convert each quality
            completed_qualities = []
            total_qualities = len(target_qualities)
            
            for i, quality in enumerate(target_qualities):
                try:
                    quality_config = QUALITIES[quality]
                    quality_dir = output_dir / quality
                    quality_dir.mkdir(exist_ok=True)
                    playlist_path = quality_dir / 'playlist.m3u8'
                    
                    # Update current quality being processed
                    progress_data['current_quality'] = quality
                    progress_data['current_progress'] = 0
                    
                    print(f"\n🔄 Converting to {quality}...")
                    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Create FFmpeg command with progress
                    input_stream = ffmpeg.input(movie.file_path)
                    output_stream = input_stream.output(
                        str(playlist_path),
                        vf=f"scale={quality_config['resolution']}",
                        vcodec='libx264',
                        vb=quality_config['bitrate'],
                        acodec='aac',
                        ab='128k',
                        f='hls',
                        hls_time=SEGMENT_DURATION,
                        hls_playlist_type='vod',
                        hls_segment_filename=str(quality_dir / 'segment_%03d.ts'),
                        hls_flags='independent_segments',
                        force_key_frames=f'expr:gte(t,n_forced*{SEGMENT_DURATION})',
                        g=250,
                        keyint_min=250,
                        sc_threshold=0,
                    )
                    
                    # Run FFmpeg with progress monitoring
                    process = ffmpeg.run_async(
                        output_stream, 
                        pipe_stderr=True, 
                        overwrite_output=True,
                        quiet=False
                    )
                    
                    # Monitor FFmpeg progress
                    monitor_ffmpeg_progress(process, total_duration, progress_data, quality)
                    
                    # Wait for completion
                    process.wait()
                    
                    if process.returncode == 0:
                        completed_qualities.append(quality)
                        print(f"✅ Completed {quality} conversion at {datetime.now().strftime('%H:%M:%S')}")
                        
                        # Update overall progress
                        overall_progress = int(((i + 1) / total_qualities) * 90)
                        movie.overall_progress = overall_progress
                        db.session.commit()
                        conversion_status[movie_id] = {'status': 'IN_PROGRESS', 'progress': overall_progress}
                    else:
                        print(f"❌ Failed {quality} conversion")
                        
                except Exception as e:
                    print(f"❌ Error converting {quality}: {e}")
            
            # Stop progress monitoring
            progress_data['stop_monitoring'] = True
            
            # Create master playlist
            if completed_qualities:
                create_master_playlist(movie_id, completed_qualities)
                print(f"\n📋 Created master playlist with qualities: {completed_qualities}")
            
            # Update final status
            movie.status = 'DONE' if completed_qualities else 'ERROR'
            movie.overall_progress = 100
            movie.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            conversion_status[movie_id] = {
                'status': movie.status, 
                'progress': 100,
                'completed_qualities': completed_qualities
            }
            
            print(f"\n🎉 Conversion completed for {movie.filename}")
            print(f"📊 Final Status: {movie.status}")
            print(f"🏁 Finished at: {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 60)
            
        except Exception as e:
            print(f"💥 Error in conversion: {e}")
            try:
                movie = db.session.get(Movie, movie_id)
                if movie:
                    movie.status = 'ERROR'
                    movie.completed_at = datetime.now()
                    db.session.commit()
            except:
                pass
            conversion_status[movie_id] = {'status': 'ERROR', 'progress': 0}

def monitor_ffmpeg_progress(process, total_duration, progress_data, quality):
    """Monitor FFmpeg stderr for progress information"""
    try:
        current_time = 0
        
        while True:
            line = process.stderr.readline()
            if not line:
                break
                
            line = line.decode('utf-8', errors='ignore')
            
            # Parse FFmpeg progress line
            # Look for time=00:01:23.45 format
            time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = float(time_match.group(3))
                
                current_time = hours * 3600 + minutes * 60 + seconds
                
                if total_duration > 0:
                    progress = (current_time / total_duration) * 100
                    progress_data['current_progress'] = min(progress, 100)
                    
    except Exception as e:
        print(f"Error monitoring FFmpeg progress: {e}")

def monitor_progress(movie_id, filename, progress_data):
    """Background thread to display progress every 30 seconds"""
    last_update = time.time()
    
    while not progress_data['stop_monitoring']:
        current_time = time.time()
        
        # Update every 30 seconds
        if current_time - last_update >= 30:
            if progress_data['current_quality'] and progress_data['current_progress'] > 0:
                print(f"\n📈 PROGRESS UPDATE:")
                print(f"   🎬 Movie ID: {movie_id}")
                print(f"   📁 File: {filename}")
                print(f"   🎯 Quality: {progress_data['current_quality']}")
                print(f"   ⚡ Progress: {progress_data['current_progress']:.3f}%")
                print(f"   🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 40)
            
            last_update = current_time
        
        time.sleep(5)  # Check every 5 seconds, update every 30

def create_master_playlist(movie_id, qualities):
    output_dir = OUTPUT_FOLDER / movie_id
    master_playlist_path = output_dir / 'master.m3u8'
    
    playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    
    quality_settings = {
        '720p': {'bandwidth': 2500000, 'resolution': '1280x720'},
        '480p': {'bandwidth': 1000000, 'resolution': '854x480'},
        '360p': {'bandwidth': 600000, 'resolution': '640x360'}
    }
    
    for quality in qualities:
        if quality in quality_settings:
            settings = quality_settings[quality]
            playlist_content += f"#EXT-X-STREAM-INF:BANDWIDTH={settings['bandwidth']},RESOLUTION={settings['resolution']}\n"
            playlist_content += f"{quality}/playlist.m3u8\n"
    
    with open(master_playlist_path, 'w') as f:
        f.write(playlist_content)

# Routes
@app.route('/')
def index():
    movies = Movie.query.order_by(Movie.created_at.desc()).all()
    
    movie_data = []
    for movie in movies:
        movie_dict = {
            'id': movie.id,
            'filename': movie.filename,
            'file_size': movie.file_size,
            'file_size_formatted': format_file_size(movie.file_size),
            'source_resolution': movie.source_resolution,
            'status': movie.status,
            'overall_progress': movie.overall_progress,
            'target_qualities': movie.get_target_qualities(),
            'created_at': movie.created_at.strftime('%Y-%m-%d %H:%M') if movie.created_at else ''
        }
        movie_data.append(movie_dict)
    
    return render_template('simple_index.html', movies=movie_data)

@app.route('/scan', methods=['POST'])
def scan_folder():
    try:
        video_files = scan_input_folder()
        new_files = 0
        
        for file_info in video_files:
            existing_movie = Movie.query.filter_by(filename=file_info['filename']).first()
            
            if not existing_movie:
                movie = Movie(
                    filename=file_info['filename'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size']
                )
                
                if file_info['video_info']:
                    movie.source_resolution = file_info['video_info']['resolution']
                
                db.session.add(movie)
                new_files += 1
        
        db.session.commit()
        return jsonify({'success': True, 'new_files': new_files})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert/<movie_id>', methods=['POST'])
def start_conversion(movie_id):
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        if movie.status not in ['NEW', 'ERROR']:
            return jsonify({'error': 'Movie is not in a convertible state'}), 400
        
        # Check if another conversion is running
        active_movie = Movie.query.filter_by(status='IN_PROGRESS').first()
        if active_movie:
            return jsonify({'error': 'Another conversion is already in progress'}), 400
        
        # Start conversion in background thread
        thread = threading.Thread(target=convert_video_simple, args=(movie_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Conversion started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<movie_id>')
def get_status(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    status_info = conversion_status.get(movie_id, {})
    
    return jsonify({
        'status': movie.status,
        'progress': movie.overall_progress,
        'live_status': status_info
    })

@app.route('/delete/<movie_id>', methods=['POST'])
def delete_movie(movie_id):
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        if movie.status == 'IN_PROGRESS':
            return jsonify({'error': 'Cannot delete movie that is being processed'}), 400
        
        # Delete output files
        output_dir = OUTPUT_FOLDER / movie_id
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
        
        # Delete from database
        db.session.delete(movie)
        db.session.commit()
        
        # Clean up status
        if movie_id in conversion_status:
            del conversion_status[movie_id]
        
        return jsonify({'success': True, 'message': 'Movie deleted'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("Simple Video Processing Dashboard")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    # Disable auto-reload to fix Python 3.13 compatibility
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
