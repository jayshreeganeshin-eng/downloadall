"""
Universal Downloader - Web Server & CLI
Production-ready Flask application with REST API and command-line interface
Supports 1871+ platforms via yt-dlp
"""

import os
import sys
import uuid
import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

try:
    from core.engine import UniversalDownloader, TelegramDownloader
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
telegram_client_session = None

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
    
    if not data.get('url') and not data.get('username'):
        return jsonify({
            'success': False,
            'error': 'URL or username is required'
        }), 400
    
    try:
        # Create and execute download
        task = universal_downloader.create_task(
            url=data.get('url', ''),
            quality=data.get('quality', 'best'),
            audio_only=data.get('audio_only', False),
            playlist=data.get('playlist', False),
            username=data.get('username')
        )
        
        # Execute download in background thread
        def run_download():
            universal_downloader.download(task.id)
        
        import threading
        thread = threading.Thread(target=run_download)
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
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


@app.route('/api/files')
def list_files():
    """List downloaded files"""
    download_dir = Path('./downloads')
    files = []
    
    if download_dir.exists():
        for f in download_dir.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    'path': str(f)
                })
    
    # Also check telegram downloads
    telegram_dir = Path('./downloads/telegram')
    if telegram_dir.exists():
        for f in telegram_dir.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    'path': str(f)
                })
    
    return jsonify({'success': True, 'files': files})


@app.route('/api/files/<path:filename>')
def download_file(filename: str):
    """Download a file"""
    return send_from_directory('./downloads', filename, as_attachment=True)


@app.route('/api/files/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename: str):
    """Delete a file"""
    try:
        filepath = Path('./downloads') / filename
        if filepath.exists():
            filepath.unlink()
            return jsonify({'success': True, 'message': 'File deleted'})
        
        # Try telegram dir
        filepath = Path('./downloads/telegram') / filename
        if filepath.exists():
            filepath.unlink()
            return jsonify({'success': True, 'message': 'File deleted'})
        
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
            'message': 'Telegram configured successfully. Connect to start session.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/telegram/connect', methods=['POST'])
async def connect_telegram():
    """Connect to Telegram"""
    global telegram_downloader, telegram_client_session
    
    if not telegram_downloader:
        return jsonify({
            'success': False,
            'error': 'Telegram not configured. Call /api/telegram/configure first'
        }), 400
    
    try:
        await telegram_downloader.connect()
        return jsonify({
            'success': True,
            'message': 'Connected to Telegram'
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
            'error': 'Telegram not configured'
        }), 400
    
    data = request.json
    task_id = f"tg_{uuid.uuid4().hex[:8]}"
    
    try:
        channel = data.get('channel')
        limit = int(data.get('limit', 100))
        
        def progress_callback(count, total):
            pass  # Could update task status here
        
        files = await telegram_downloader.download_channel_media(
            channel=channel,
            limit=limit,
            callback=progress_callback
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'files_downloaded': len(files),
            'message': f'Downloaded {len(files)} files from {channel}'
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
    task_id = f"tc_{uuid.uuid4().hex[:8]}"
    
    try:
        source = data.get('clone_source')
        dest = data.get('clone_dest')
        clone_type = data.get('clone_type', 'channel')
        limit = int(data.get('limit', 100))
        
        def progress_callback(count, total):
            pass
        
        if clone_type == 'group':
            count = await telegram_downloader.clone_group(
                source=source,
                destination=dest,
                limit=limit,
                callback=progress_callback
            )
        else:
            count = await telegram_downloader.clone_channel(
                source=source,
                destination=dest,
                limit=limit,
                callback=progress_callback
            )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'messages_cloned': count,
            'message': f'Cloned {count} messages from {source} to {dest}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/telegram/disconnect', methods=['POST'])
async def disconnect_telegram():
    """Disconnect from Telegram"""
    global telegram_downloader
    
    if telegram_downloader:
        await telegram_downloader.disconnect()
    
    return jsonify({
        'success': True,
        'message': 'Disconnected from Telegram'
    })


# ==================== UTILITY ROUTES ====================

@app.route('/api/stats')
def get_stats():
    """Get application statistics"""
    download_dir = Path('./downloads')
    total_size = sum(f.stat().st_size for f in download_dir.glob('*') if f.is_file())
    
    telegram_dir = Path('./downloads/telegram')
    if telegram_dir.exists():
        total_size += sum(f.stat().st_size for f in telegram_dir.glob('*') if f.is_file())
    
    return jsonify({
        'total_downloads': len(universal_downloader.list_tasks()),
        'completed': len([t for t in universal_downloader.list_tasks() if t['status'] == 'completed']),
        'failed': len([t for t in universal_downloader.list_tasks() if t['status'] == 'failed']),
        'total_size_mb': round(total_size / 1024 / 1024, 2),
        'supported_platforms': len(UniversalDownloader.SUPPORTED_PLATFORMS) + 1850,
        'telegram_configured': telegram_downloader is not None
    })


# ==================== CLI INTERFACE ====================

def run_cli():
    """Run command-line interface"""
    parser = argparse.ArgumentParser(
        description='Universal Downloader - Download from any social media platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py -u "https://youtube.com/watch?v=ID" -q 1080
  python app.py -u "https://youtube.com/playlist?list=ID" -p
  python app.py -u "https://youtube.com/watch?v=ID" -a
  python app.py --username myuser --platform instagram
  python app.py --web --port 5000

Telegram Examples:
  python app.py --telegram --api-id ID --api-hash HASH --phone +1234567890 --channel @channel
  python app.py --telegram --api-id ID --api-hash HASH --phone +1234567890 \\
           --clone-source @src --clone-dest @dest --clone-type channel
        """
    )
    
    # Download options
    parser.add_argument('-u', '--url', help='URL to download')
    parser.add_argument('--username', help='Username for profile download')
    parser.add_argument('-P', '--platform', help='Platform (youtube, instagram, tiktok, twitter, etc.)')
    parser.add_argument('-q', '--quality', choices=['2160', '1440', '1080', '720', '480', '360', 'best'],
                       default='best', help='Video quality')
    parser.add_argument('-a', '--audio-only', action='store_true', help='Download audio only (MP3)')
    parser.add_argument('-l', '--playlist', action='store_true', help='Download playlist')
    
    # Telegram options
    parser.add_argument('--telegram', action='store_true', help='Use Telegram downloader')
    parser.add_argument('--api-id', type=int, help='Telegram API ID')
    parser.add_argument('--api-hash', help='Telegram API Hash')
    parser.add_argument('--phone', help='Telegram phone number')
    parser.add_argument('--channel', help='Telegram channel to download')
    parser.add_argument('--clone-source', help='Source channel/group for cloning')
    parser.add_argument('--clone-dest', help='Destination channel/group for cloning')
    parser.add_argument('--clone-type', choices=['channel', 'group'], default='channel',
                       help='Type of clone operation')
    parser.add_argument('--limit', type=int, default=100, help='Limit number of messages/media')
    
    # Web server options
    parser.add_argument('--web', action='store_true', help='Start web interface')
    parser.add_argument('--port', type=int, default=5000, help='Web server port')
    parser.add_argument('--host', default='127.0.0.1', help='Web server host')
    
    args = parser.parse_args()
    
    # Web mode
    if args.web:
        print(f"🌐 Starting Universal Downloader Web Interface")
        print(f"📍 Open http://{args.host}:{args.port} in your browser")
        print(f"💡 Press Ctrl+C to stop")
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
        return
    
    # Telegram mode
    if args.telegram:
        if not all([args.api_id, args.api_hash, args.phone]):
            print("❌ Error: Telegram requires --api-id, --api-hash, and --phone")
            sys.exit(1)
        
        tg = TelegramDownloader(args.api_id, args.api_hash, args.phone)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print("🔌 Connecting to Telegram...")
            loop.run_until_complete(tg.connect())
            
            if args.clone_source and args.clone_dest:
                print(f"🔄 Cloning {args.clone_type} from {args.clone_source} to {args.clone_dest}")
                if args.clone_type == 'group':
                    count = loop.run_until_complete(
                        tg.clone_group(args.clone_source, args.clone_dest, args.limit)
                    )
                else:
                    count = loop.run_until_complete(
                        tg.clone_channel(args.clone_source, args.clone_dest, args.limit)
                    )
                print(f"✅ Cloned {count} messages")
            
            elif args.channel:
                print(f"📥 Downloading media from {args.channel}")
                files = loop.run_until_complete(
                    tg.download_channel_media(args.channel, args.limit)
                )
                print(f"✅ Downloaded {len(files)} files")
            
            else:
                print("❌ Error: Specify --channel or --clone-source/--clone-dest")
            
            loop.run_until_complete(tg.disconnect())
            
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            sys.exit(1)
        finally:
            loop.close()
        return
    
    # Standard download mode
    if args.url or args.username:
        downloader = UniversalDownloader()
        
        print(f"🎯 Platform: {args.platform or 'auto-detect'}")
        print(f"📥 URL: {args.url or f'@{args.username}'}")
        print(f"🎬 Quality: {args.quality}")
        print(f"🎵 Audio-only: {args.audio_only}")
        print(f"📋 Playlist: {args.playlist}")
        print()
        
        task = downloader.create_task(
            url=args.url or '',
            quality=args.quality,
            audio_only=args.audio_only,
            playlist=args.playlist,
            username=args.username
        )
        
        print(f"⏳ Starting download (Task ID: {task.id})...")
        success = downloader.download(task.id)
        
        if success:
            print(f"✅ Download completed: {task.filename}")
        else:
            print(f"❌ Download failed: {task.error}")
            sys.exit(1)
        return
    
    # No arguments provided
    parser.print_help()


if __name__ == '__main__':
    # Check if running as CLI or just importing
    if len(sys.argv) > 1 or 'FLASK_APP' not in os.environ:
        run_cli()
    else:
        # Running as Flask app (e.g., flask run)
        pass
