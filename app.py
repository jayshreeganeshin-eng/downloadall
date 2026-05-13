"""
Universal Downloader - Web Server & CLI
Optimized Flask application with REST API and command-line interface
"""

import os
import sys
import uuid
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

try:
    from core.engine import UniversalDownloader, TelegramDownloader, DownloadTask, DownloadStatus
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


# Initialize Flask app
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# Initialize downloaders
universal_downloader = UniversalDownloader(download_dir='./downloads')
telegram_downloader: Optional[TelegramDownloader] = None

# Store active telegram session config
telegram_config: Dict[str, Any] = {}


# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Serve main web interface"""
    return render_template('index.html')


@app.route('/api/platforms')
def get_platforms():
    """Get list of supported platforms"""
    return jsonify({
        'platforms': list(UniversalDownloader.SUPPORTED_PLATFORMS.keys()),
        'qualities': ['2160', '1440', '1080', '720', '480', '360', 'best'],
        'features': {
            'video_download': True,
            'audio_only': True,
            'playlist_support': True,
            'profile_download': True,
            'telegram_clone': True,
        }
    })


@app.route('/api/download', methods=['POST'])
def start_download():
    """Start a new download task"""
    data = request.json
    
    task_id = str(uuid.uuid4())[:8]
    
    try:
        # Create download task
        task = DownloadTask.create(
            task_id=task_id,
            url=data.get('url'),
            username=data.get('username'),
            platform=data.get('platform', 'unknown'),
            quality=data.get('quality', 'best'),
            audio_only=data.get('audio_only', False),
            playlist=data.get('playlist', False),
            output_path='./downloads'
        )
        
        # Auto-detect platform if not provided
        if task.platform == 'unknown' and task.url:
            task.platform = universal_downloader.detect_platform(url=task.url)
        
        # Start async download
        def progress_callback(tid, progress, message):
            task.progress = progress
            task.message = message
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(universal_downloader.download(task, progress_callback))
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Download started',
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status/<task_id>')
def get_status(task_id: str):
    """Get download task status"""
    task = universal_downloader.get_task(task_id)
    if task:
        return jsonify({'success': True, 'task': task.to_dict()})
    return jsonify({'success': False, 'error': 'Task not found'}), 404


@app.route('/api/tasks')
def list_tasks():
    """List all download tasks"""
    tasks = universal_downloader.list_tasks()
    return jsonify({'success': True, 'tasks': tasks})


@app.route('/api/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id: str):
    """Cancel a download task"""
    success = universal_downloader.cancel_task(task_id)
    return jsonify({'success': success})


# ==================== TELEGRAM ROUTES ====================

@app.route('/api/telegram/configure', methods=['POST'])
def configure_telegram():
    """Configure Telegram connection"""
    global telegram_downloader, telegram_config
    
    data = request.json
    try:
        telegram_config = {
            'api_id': int(data['api_id']),
            'api_hash': data['api_hash'],
            'phone': data['phone']
        }
        
        telegram_downloader = TelegramDownloader(
            api_id=telegram_config['api_id'],
            api_hash=telegram_config['api_hash'],
            phone=telegram_config['phone']
        )
        
        return jsonify({
            'success': True,
            'message': 'Telegram configured successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/telegram/download', methods=['POST'])
async def telegram_download():
    """Download media from Telegram channel"""
    global telegram_downloader
    
    if not telegram_downloader:
        return jsonify({
            'success': False,
            'error': 'Telegram not configured. Call /api/telegram/configure first'
        }), 400
    
    data = request.json
    task_id = str(uuid.uuid4())[:8]
    
    try:
        task = DownloadTask.create(
            task_id=task_id,
            platform='telegram',
            output_path='./downloads'
        )
        
        channel = data.get('channel')
        limit = int(data.get('limit', 100))
        
        def progress_callback(tid, progress, message):
            task.progress = progress
            task.message = message
        
        await telegram_downloader.download_channel_media(
            task, channel, limit, progress_callback
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/telegram/clone', methods=['POST'])
async def telegram_clone():
    """Clone Telegram channel/group"""
    global telegram_downloader
    
    if not telegram_downloader:
        return jsonify({
            'success': False,
            'error': 'Telegram not configured'
        }), 400
    
    data = request.json
    task_id = str(uuid.uuid4())[:8]
    
    try:
        task = DownloadTask.create(
            task_id=task_id,
            platform='telegram',
            output_path='./downloads'
        )
        
        source = data.get('source')
        dest = data.get('dest')
        clone_type = data.get('type', 'channel')
        limit = int(data.get('limit', 100))
        
        def progress_callback(tid, progress, message):
            task.progress = progress
            task.message = message
        
        if clone_type == 'group':
            await telegram_downloader.clone_group(task, source, dest, limit, progress_callback)
        else:
            await telegram_downloader.clone_channel(task, source, dest, limit, progress_callback)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/telegram/status')
def telegram_status():
    """Check Telegram connection status"""
    return jsonify({
        'configured': telegram_downloader is not None,
        'config': telegram_config if telegram_config else None
    })


# ==================== FILE SERVING ====================

@app.route('/downloads/<path:filename>')
def serve_download(filename):
    """Serve downloaded files"""
    return send_from_directory('./downloads', filename)


@app.route('/api/downloads')
def list_downloads():
    """List all downloaded files"""
    downloads_dir = Path('./downloads')
    if not downloads_dir.exists():
        return jsonify({'success': True, 'files': []})
    
    files = []
    for f in downloads_dir.iterdir():
        if f.is_file():
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'url': f'/downloads/{f.name}'
            })
    
    return jsonify({'success': True, 'files': sorted(files, key=lambda x: x['modified'], reverse=True)})


# ==================== CLI INTERFACE ====================

def run_cli():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Universal Downloader - Download from any social media platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -u "https://youtube.com/watch?v=ID" -q 1080
  %(prog)s -u "https://youtube.com/playlist?list=ID" -p
  %(prog)s -u "https://youtube.com/watch?v=ID" -a
  %(prog)s --username myuser --platform instagram
  %(prog)s --web --port 5000
  
Telegram Examples:
  %(prog)s --telegram --api-id ID --api-hash HASH --phone +1234567890 --channel @channel
  %(prog)s --telegram --api-id ID --api-hash HASH --phone +1234567890 \\
           --clone-source @src --clone-dest @dest --clone-type channel
        """
    )
    
    # Download options
    parser.add_argument('-u', '--url', help='URL to download')
    parser.add_argument('--username', help='Username for profile download')
    parser.add_argument('-P', '--platform', default='auto', 
                       help='Platform (youtube, instagram, tiktok, twitter, etc.)')
    parser.add_argument('-q', '--quality', default='best',
                       choices=['2160', '1440', '1080', '720', '480', '360', 'best'],
                       help='Video quality')
    parser.add_argument('-a', '--audio-only', action='store_true',
                       help='Download audio only (MP3)')
    parser.add_argument('-l', '--playlist', action='store_true',
                       help='Download playlist')
    
    # Telegram options
    parser.add_argument('--telegram', action='store_true',
                       help='Use Telegram downloader')
    parser.add_argument('--api-id', type=int, help='Telegram API ID')
    parser.add_argument('--api-hash', help='Telegram API Hash')
    parser.add_argument('--phone', help='Telegram phone number')
    parser.add_argument('--channel', help='Telegram channel to download')
    parser.add_argument('--clone-source', help='Source channel/group for cloning')
    parser.add_argument('--clone-dest', help='Destination channel/group for cloning')
    parser.add_argument('--clone-type', choices=['channel', 'group'], default='channel',
                       help='Type of clone operation')
    parser.add_argument('--limit', type=int, default=100,
                       help='Limit number of messages/media')
    
    # Web server options
    parser.add_argument('--web', action='store_true',
                       help='Start web interface')
    parser.add_argument('--port', type=int, default=5000,
                       help='Web server port')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Web server host')
    
    args = parser.parse_args()
    
    # Web mode
    if args.web:
        print(f"🚀 Starting web interface at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop")
        app.run(host=args.host, port=args.port, debug=False)
        return
    
    # Telegram mode
    if args.telegram:
        if not all([args.api_id, args.api_hash, args.phone]):
            print("❌ Error: Telegram requires --api-id, --api-hash, and --phone")
            sys.exit(1)
        
        tg = TelegramDownloader(
            api_id=args.api_id,
            api_hash=args.api_hash,
            phone=args.phone
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if args.clone_source and args.clone_dest:
                task = DownloadTask.create(
                    task_id='cli',
                    platform='telegram'
                )
                
                print(f"🔄 Cloning {args.clone_source} to {args.clone_dest}...")
                
                if args.clone_type == 'group':
                    result = loop.run_until_complete(
                        tg.clone_group(task, args.clone_source, args.clone_dest, args.limit)
                    )
                else:
                    result = loop.run_until_complete(
                        tg.clone_channel(task, args.clone_source, args.clone_dest, args.limit)
                    )
                
                print(f"✅ {result.message}")
            
            elif args.channel:
                task = DownloadTask.create(
                    task_id='cli',
                    platform='telegram'
                )
                
                print(f"📥 Downloading from {args.channel}...")
                result = loop.run_until_complete(
                    tg.download_channel_media(task, args.channel, args.limit)
                )
                
                print(f"✅ {result.message}")
                print(f"📁 Files: {len(result.files_downloaded)}")
            
            else:
                print("❌ Error: Specify --channel or --clone-source/--clone-dest")
                sys.exit(1)
        
        finally:
            loop.run_until_complete(tg.disconnect())
            loop.close()
        
        return
    
    # Standard download mode
    if not args.url and not args.username:
        print("❌ Error: Provide --url or --username")
        parser.print_help()
        sys.exit(1)
    
    ud = UniversalDownloader()
    
    task = DownloadTask.create(
        task_id='cli',
        url=args.url,
        username=args.username,
        platform=args.platform if args.platform != 'auto' else 'unknown',
        quality=args.quality,
        audio_only=args.audio_only,
        playlist=args.playlist
    )
    
    # Auto-detect platform
    if task.platform == 'unknown':
        task.platform = ud.detect_platform(url=args.url, username=args.username)
    
    print(f"🎯 Platform detected: {task.platform}")
    print(f"📥 Starting download...")
    
    def progress_callback(tid, progress, message):
        print(f"\r📊 {message}", end='', flush=True)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(ud.download(task, progress_callback))
        print(f"\n✅ {result.message}")
        print(f"📁 Files downloaded: {len(result.files_downloaded)}")
        
        for f in result.files_downloaded:
            print(f"   - {f}")
    
    finally:
        loop.close()


if __name__ == '__main__':
    # Check if running as CLI or web
    if len(sys.argv) > 1:
        run_cli()
    else:
        # Default to web mode
        print("🚀 Starting Universal Downloader Web Interface...")
        print("📱 Open http://127.0.0.1:5000 in your browser")
        print("💡 Use --help for CLI options")
        app.run(host='127.0.0.1', port=5000, debug=True)
