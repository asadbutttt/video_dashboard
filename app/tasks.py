from celery import Celery
from app import db, socketio
from app.models import Movie, QualityVariant, ConversionQueue
from app.utils import get_video_info, create_output_directory, create_master_playlist, cleanup_temp_files
from config import Config
import ffmpeg
import os
from pathlib import Path
from datetime import datetime
import re

# Create Celery instance
celery = Celery('video_dashboard')
celery.config_from_object('config.Config')

@celery.task(bind=True)
def convert_video_task(self, movie_id):
    """Main task to convert video to multiple HLS qualities"""
    try:
        # Get movie from database
        movie = db.session.get(Movie, movie_id)
        if not movie:
            return {'error': 'Movie not found'}
        
        # Update status to IN_PROGRESS
        movie.status = 'IN_PROGRESS'
        movie.started_at = datetime.now()
        db.session.commit()
        
        # Emit status update
        socketio.emit('status_update', {
            'movie_id': movie_id,
            'status': 'IN_PROGRESS',
            'progress': 0
        })
        
        # Get video info if not already available
        if not movie.source_resolution:
            video_info = get_video_info(movie.file_path)
            if video_info:
                movie.source_resolution = video_info['resolution']
                db.session.commit()
        
        # Create output directory
        output_dir = create_output_directory(movie_id)
        
        # Get target qualities based on source resolution
        target_qualities = movie.get_target_qualities()
        
        if not target_qualities:
            movie.status = 'DONE'
            movie.completed_at = datetime.now()
            movie.overall_progress = 100
            db.session.commit()
            
            socketio.emit('status_update', {
                'movie_id': movie_id,
                'status': 'DONE',
                'progress': 100
            })
            return {'success': True, 'message': 'No conversion needed'}
        
        # Create quality variants in database
        for quality in target_qualities:
            variant = QualityVariant(
                movie_id=movie_id,
                quality=quality,
                status='PENDING'
            )
            db.session.add(variant)
        db.session.commit()
        
        # Convert each quality
        completed_qualities = []
        total_qualities = len(target_qualities)
        
        for i, quality in enumerate(target_qualities):
            try:
                # Update variant status
                variant = QualityVariant.query.filter_by(
                    movie_id=movie_id, 
                    quality=quality
                ).first()
                variant.status = 'IN_PROGRESS'
                db.session.commit()
                
                # Convert quality
                success = convert_quality(movie, quality, self)
                
                if success:
                    variant.status = 'DONE'
                    variant.progress = 100
                    variant.completed_at = datetime.now()
                    completed_qualities.append(quality)
                else:
                    variant.status = 'ERROR'
                    variant.error_message = 'Conversion failed'
                
                db.session.commit()
                
                # Update overall progress
                overall_progress = int(((i + 1) / total_qualities) * 100)
                movie.overall_progress = overall_progress
                db.session.commit()
                
                # Emit progress update
                socketio.emit('status_update', {
                    'movie_id': movie_id,
                    'status': 'IN_PROGRESS',
                    'progress': overall_progress,
                    'current_quality': quality
                })
                
            except Exception as e:
                print(f"Error converting {quality} for {movie_id}: {e}")
                variant.status = 'ERROR'
                variant.error_message = str(e)
                db.session.commit()
        
        # Create master playlist if any qualities were successful
        if completed_qualities:
            create_master_playlist(movie_id, completed_qualities)
        
        # Update movie status
        if len(completed_qualities) == len(target_qualities):
            movie.status = 'DONE'
        elif completed_qualities:
            movie.status = 'DONE'  # Partial success still counts as done
        else:
            movie.status = 'ERROR'
            movie.error_message = 'All quality conversions failed'
        
        movie.completed_at = datetime.now()
        movie.overall_progress = 100
        db.session.commit()
        
        # Remove from queue
        queue_entry = ConversionQueue.query.filter_by(movie_id=movie_id).first()
        if queue_entry:
            db.session.delete(queue_entry)
            db.session.commit()
        
        # Clean up temporary files
        cleanup_temp_files(movie_id)
        
        # Emit final status update
        socketio.emit('status_update', {
            'movie_id': movie_id,
            'status': movie.status,
            'progress': 100
        })
        
        # Process next item in queue
        process_next_in_queue()
        
        return {
            'success': True,
            'completed_qualities': completed_qualities,
            'total_qualities': len(target_qualities)
        }
        
    except Exception as e:
        print(f"Error in convert_video_task for {movie_id}: {e}")
        
        # Update movie status to error
        movie = db.session.get(Movie, movie_id)
        if movie:
            movie.status = 'ERROR'
            movie.error_message = str(e)
            movie.completed_at = datetime.now()
            db.session.commit()
            
            # Remove from queue
            queue_entry = ConversionQueue.query.filter_by(movie_id=movie_id).first()
            if queue_entry:
                db.session.delete(queue_entry)
                db.session.commit()
            
            socketio.emit('status_update', {
                'movie_id': movie_id,
                'status': 'ERROR',
                'error': str(e)
            })
        
        # Process next item in queue
        process_next_in_queue()
        
        return {'error': str(e)}

def convert_quality(movie, quality, task):
    """Convert video to specific quality"""
    try:
        quality_config = Config.QUALITIES[quality]
        output_dir = Config.OUTPUT_FOLDER / movie.id / quality
        playlist_path = output_dir / 'playlist.m3u8'
        
        # Build FFmpeg command
        input_stream = ffmpeg.input(movie.file_path)
        
        # Video filters and encoding
        video_stream = input_stream.video.filter(
            'scale', quality_config['resolution']
        ).output(
            str(playlist_path),
            vcodec='libx264',
            video_bitrate=quality_config['bitrate'],
            acodec='aac',
            audio_bitrate='128k',
            format='hls',
            hls_time=Config.SEGMENT_DURATION,
            hls_playlist_type='vod',
            hls_segment_filename=str(output_dir / 'segment_%03d.ts')
        )
        
        # Run FFmpeg with progress tracking
        process = ffmpeg.run_async(
            video_stream,
            pipe_stderr=True,
            overwrite_output=True
        )
        
        # Track progress (simplified - in production you'd parse FFmpeg output)
        while True:
            output = process.stderr.readline()
            if output == b'' and process.poll() is not None:
                break
            
            if output:
                line = output.decode('utf-8').strip()
                # Parse progress from FFmpeg output (simplified)
                if 'time=' in line:
                    # Extract time and calculate progress
                    # This is a simplified version - you'd want more robust parsing
                    pass
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            # Update variant with file info
            variant = QualityVariant.query.filter_by(
                movie_id=movie.id,
                quality=quality
            ).first()
            
            if variant:
                variant.file_path = str(playlist_path)
                # Count segments
                segment_files = list(output_dir.glob('segment_*.ts'))
                variant.segment_count = len(segment_files)
                db.session.commit()
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error converting {quality} for {movie.id}: {e}")
        return False

def process_next_in_queue():
    """Process the next movie in the conversion queue"""
    try:
        # Get next item in queue
        next_item = ConversionQueue.query.order_by(ConversionQueue.position).first()
        
        if next_item:
            # Start conversion
            convert_video_task.delay(next_item.movie_id)
            
    except Exception as e:
        print(f"Error processing next in queue: {e}")

@celery.task
def scan_input_folder_task():
    """Task to scan input folder for new files"""
    from app.utils import scan_input_folder
    
    try:
        video_files = scan_input_folder()
        new_files = 0
        
        for file_info in video_files:
            # Check if movie already exists
            existing_movie = Movie.query.filter_by(
                filename=file_info['filename']
            ).first()
            
            if not existing_movie:
                # Create new movie entry
                movie = Movie(
                    filename=file_info['filename'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size']
                )
                
                if file_info['video_info']:
                    movie.source_resolution = file_info['video_info']['resolution']
                
                db.session.add(movie)
                db.session.commit()
                new_files += 1
                
                # Emit new movie event
                socketio.emit('new_movie', movie.to_dict())
        
        return {'scanned_files': len(video_files), 'new_files': new_files}
        
    except Exception as e:
        print(f"Error scanning input folder: {e}")
        return {'error': str(e)}
