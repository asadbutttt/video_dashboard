from flask import Blueprint, render_template, request, jsonify, current_app
from app import db, socketio
from app.models import Movie, QualityVariant, ConversionQueue
from app.tasks import convert_video_task, scan_input_folder_task
from app.utils import scan_input_folder, format_file_size, format_duration, get_status_color, get_status_icon
from flask_socketio import emit
import os

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard page"""
    # Get all movies
    movies = Movie.query.order_by(Movie.created_at.desc()).all()
    
    # Get queue information
    queue = ConversionQueue.get_queue()
    
    # Prepare movie data for template
    movie_data = []
    for movie in movies:
        movie_dict = movie.to_dict()
        movie_dict['file_size_formatted'] = format_file_size(movie.file_size)
        movie_dict['status_color'] = get_status_color(movie.status)
        movie_dict['status_icon'] = get_status_icon(movie.status)
        movie_dict['target_qualities_str'] = ', '.join(movie.get_target_qualities())
        
        # Check if in queue
        queue_position = None
        for i, queue_item in enumerate(queue):
            if queue_item.movie_id == movie.id:
                queue_position = i + 1
                break
        movie_dict['queue_position'] = queue_position
        
        movie_data.append(movie_dict)
    
    return render_template('index.html', movies=movie_data, queue_length=len(queue))

@main.route('/api/movies')
def get_movies():
    """API endpoint to get all movies"""
    movies = Movie.query.order_by(Movie.created_at.desc()).all()
    return jsonify([movie.to_dict() for movie in movies])

@main.route('/api/movies/<movie_id>')
def get_movie(movie_id):
    """API endpoint to get specific movie"""
    movie = Movie.query.get_or_404(movie_id)
    return jsonify(movie.to_dict())

@main.route('/api/convert/<movie_id>', methods=['POST'])
def start_conversion(movie_id):
    """Start conversion for a movie"""
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        if movie.status not in ['NEW', 'ERROR']:
            return jsonify({'error': 'Movie is not in a convertible state'}), 400
        
        # Check if there's already a movie being processed
        active_movie = Movie.query.filter_by(status='IN_PROGRESS').first()
        
        if active_movie:
            # Add to queue
            queue_position = ConversionQueue.get_next_position()
            queue_entry = ConversionQueue(
                movie_id=movie_id,
                position=queue_position
            )
            db.session.add(queue_entry)
            movie.status = 'QUEUED'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Added to queue at position {queue_position}',
                'queue_position': queue_position
            })
        else:
            # Start conversion immediately
            movie.status = 'QUEUED'
            db.session.commit()
            
            # Add to queue with position 1
            queue_entry = ConversionQueue(
                movie_id=movie_id,
                position=1
            )
            db.session.add(queue_entry)
            db.session.commit()
            
            # Start the conversion task
            convert_video_task.delay(movie_id)
            
            return jsonify({
                'success': True,
                'message': 'Conversion started',
                'queue_position': 1
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/cancel/<movie_id>', methods=['POST'])
def cancel_conversion(movie_id):
    """Cancel a queued conversion"""
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        if movie.status != 'QUEUED':
            return jsonify({'error': 'Movie is not in queue'}), 400
        
        # Remove from queue
        queue_entry = ConversionQueue.query.filter_by(movie_id=movie_id).first()
        if queue_entry:
            db.session.delete(queue_entry)
            
            # Update positions of remaining queue items
            remaining_items = ConversionQueue.query.filter(
                ConversionQueue.position > queue_entry.position
            ).all()
            
            for item in remaining_items:
                item.position -= 1
            
            db.session.commit()
        
        # Update movie status
        movie.status = 'NEW'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Conversion cancelled'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/delete/<movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    """Delete a movie and its files"""
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        if movie.status == 'IN_PROGRESS':
            return jsonify({'error': 'Cannot delete movie that is being processed'}), 400
        
        # Remove from queue if queued
        queue_entry = ConversionQueue.query.filter_by(movie_id=movie_id).first()
        if queue_entry:
            db.session.delete(queue_entry)
        
        # Delete output files
        output_dir = current_app.config['OUTPUT_FOLDER'] / movie_id
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
        
        # Delete from database
        db.session.delete(movie)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Movie deleted'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/scan', methods=['POST'])
def scan_folder():
    """Manually scan input folder"""
    try:
        scan_input_folder_task.delay()
        return jsonify({'success': True, 'message': 'Folder scan initiated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/queue')
def get_queue():
    """Get current conversion queue"""
    try:
        queue = ConversionQueue.get_queue()
        queue_data = []
        
        for item in queue:
            movie_data = item.movie.to_dict()
            movie_data['queue_position'] = item.position
            queue_data.append(movie_data)
        
        return jsonify(queue_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    try:
        total_movies = Movie.query.count()
        completed_movies = Movie.query.filter_by(status='DONE').count()
        in_progress = Movie.query.filter_by(status='IN_PROGRESS').count()
        queued = Movie.query.filter_by(status='QUEUED').count()
        errors = Movie.query.filter_by(status='ERROR').count()
        
        return jsonify({
            'total_movies': total_movies,
            'completed_movies': completed_movies,
            'in_progress': in_progress,
            'queued': queued,
            'errors': errors,
            'completion_rate': round((completed_movies / total_movies * 100) if total_movies > 0 else 0, 1)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to video dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('request_status')
def handle_status_request(data):
    """Handle status request for specific movie"""
    movie_id = data.get('movie_id')
    if movie_id:
        movie = db.session.get(Movie, movie_id)
        if movie:
            emit('status_update', {
                'movie_id': movie_id,
                'status': movie.status,
                'progress': movie.overall_progress
            })
