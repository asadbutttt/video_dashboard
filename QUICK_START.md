# Quick Start Guide - Video Processing Dashboard

## For Non-Technical Users

This guide will help you get the video processing dashboard running quickly and easily.

## Prerequisites (One-time setup)

### 1. Install Python
- Download Python 3.8+ from https://python.org/downloads/
- **IMPORTANT**: During installation, check "Add Python to PATH"
- Verify installation: Open Command Prompt and type `python --version`

### 2. Install FFmpeg
- Download from https://ffmpeg.org/download.html#build-windows
- Extract the zip file to `C:\ffmpeg`
- Add `C:\ffmpeg\bin` to your Windows PATH:
  1. Press Windows key + R, type `sysdm.cpl`, press Enter
  2. Click "Environment Variables"
  3. Under "System Variables", find "Path" and click "Edit"
  4. Click "New" and add `C:\ffmpeg\bin`
  5. Click OK on all windows
- Verify: Open new Command Prompt and type `ffmpeg -version`

### 3. Install Redis (Optional - for advanced features)
- Download Redis for Windows from https://github.com/microsoftarchive/redis/releases
- Install and start the Redis service
- Default settings work fine

## Running the Application

### Simple Method (Recommended)

1. **Double-click `start_dashboard.bat`**
   - This will automatically set up everything and start the web interface
   - Wait for the message "Running on http://127.0.0.1:5000"
   - Open your browser and go to http://localhost:5000

2. **For video processing to work, also double-click `start_worker.bat`**
   - This starts the background video processor
   - Keep both windows open while using the application

### Manual Method

If the batch files don't work, follow these steps:

1. **Open Command Prompt in the project folder**
2. **Create virtual environment:**
   ```
   python -m venv venv
   ```
3. **Activate virtual environment:**
   ```
   venv\Scripts\activate
   ```
4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
5. **Start the application:**
   ```
   python run.py
   ```
6. **In another Command Prompt window, start the worker:**
   ```
   venv\Scripts\activate
   celery -A celery_worker.celery worker --loglevel=info --pool=solo
   ```

## Using the Dashboard

### Step 1: Add Videos
- Copy your video files to the `INPUT` folder
- Supported formats: MP4, AVI, MOV, MKV, WMV, FLV, WEBM

### Step 2: Scan for Videos
- Open http://localhost:5000 in your browser
- Click "Scan INPUT Folder" button
- Your videos will appear in the table

### Step 3: Convert Videos
- Click the green "Convert" button next to each video
- Videos will be processed one at a time
- Watch the progress bar for updates

### Step 4: Access Converted Files
- Converted files will be in the `OUTPUT` folder
- Each video gets its own folder (e.g., `OUTPUT/MOV123456/`)
- Use the `master.m3u8` file for streaming

## Understanding the Status Colors

- 🟡 **NEW**: Video detected, ready to convert
- 🔵 **QUEUED**: Waiting in line for conversion
- 🔴 **IN PROGRESS**: Currently being converted
- 🟢 **DONE**: Conversion completed successfully
- ⚫ **ERROR**: Something went wrong

## Troubleshooting

### "Python is not recognized"
- Reinstall Python and make sure to check "Add Python to PATH"
- Restart your computer after installation

### "FFmpeg is not recognized"
- Make sure FFmpeg is installed and added to PATH
- Restart Command Prompt after adding to PATH
- Test with: `ffmpeg -version`

### Videos not converting
- Make sure both `start_dashboard.bat` AND `start_worker.bat` are running
- Check that your video files are in the `INPUT` folder
- Click "Scan INPUT Folder" to detect new files

### Conversion fails
- Check that FFmpeg is properly installed
- Make sure you have enough disk space
- Try with a different video file to test

### Browser shows "This site can't be reached"
- Make sure `start_dashboard.bat` is running
- Wait for the message "Running on http://127.0.0.1:5000"
- Try http://127.0.0.1:5000 instead of localhost:5000

## Tips for Best Results

1. **Keep both windows open** while using the application
2. **Don't close the Command Prompt windows** - they need to stay running
3. **Wait for conversions to complete** before closing the application
4. **Use common video formats** (MP4 works best)
5. **Have plenty of disk space** - converted files can be large

## Getting Help

If you're still having trouble:

1. Check the Command Prompt windows for error messages
2. Make sure all prerequisites are properly installed
3. Try restarting your computer and running the batch files again
4. Test with a small, simple MP4 file first

## Stopping the Application

- Close both Command Prompt windows (dashboard and worker)
- Or press Ctrl+C in each window
- Your converted files will remain in the OUTPUT folder
