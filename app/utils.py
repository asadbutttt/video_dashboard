import os
import ffmpeg
from pathlib import Path
from config import Config

def get_video_info(file_path):
    """Get video information using ffprobe"""
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
                'duration': duration,
                'format': probe['format']['format_name']
            }
    except Exception as e:
        print(f"Error getting video info for {file_path}: {e}")
        return None

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def scan_input_folder():
    """Scan INPUT folder for new video files"""
    input_folder = Config.INPUT_FOLDER
    supported_formats = Config.SUPPORTED_FORMATS
    
    video_files = []
    
    if not input_folder.exists():
        return video_files
    
    for file_path in input_folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_formats:
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

def create_output_directory(movie_id):
    """Create output directory structure for a movie"""
    output_dir = Config.OUTPUT_FOLDER / movie_id
    output_dir.mkdir(exist_ok=True)
    
    # Create quality subdirectories
    for quality in Config.QUALITIES.keys():
        quality_dir = output_dir / quality
        quality_dir.mkdir(exist_ok=True)
    
    return output_dir

def create_master_playlist(movie_id, qualities):
    """Create master HLS playlist for adaptive streaming"""
    output_dir = Config.OUTPUT_FOLDER / movie_id
    master_playlist_path = output_dir / 'master.m3u8'
    
    playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    
    # Quality settings for bitrates
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
    
    return str(master_playlist_path)

def get_status_color(status):
    """Get color class for status"""
    status_colors = {
        'NEW': 'warning',      # Yellow
        'QUEUED': 'info',      # Blue  
        'IN_PROGRESS': 'danger', # Red
        'DONE': 'success',     # Green
        'ERROR': 'dark'        # Dark
    }
    return status_colors.get(status, 'secondary')

def get_status_icon(status):
    """Get icon for status"""
    status_icons = {
        'NEW': '🟡',
        'QUEUED': '🔵', 
        'IN_PROGRESS': '🔴',
        'DONE': '🟢',
        'ERROR': '⚫'
    }
    return status_icons.get(status, '⚪')

def cleanup_temp_files(movie_id):
    """Clean up temporary files after conversion"""
    output_dir = Config.OUTPUT_FOLDER / movie_id
    
    # Remove any temporary files (e.g., .tmp, .part files)
    for temp_file in output_dir.rglob('*.tmp'):
        try:
            temp_file.unlink()
        except:
            pass
    
    for temp_file in output_dir.rglob('*.part'):
        try:
            temp_file.unlink()
        except:
            pass
