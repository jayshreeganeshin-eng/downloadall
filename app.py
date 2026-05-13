#!/usr/bin/env python3
"""
Universal Downloader - Production Ready
Web GUI + CLI Interface
Supports: 1871+ Social Media, Torrents, Tor, Telegram
"""

import os
import sys
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import click

# Import core engine
from core.engine import (
    UniversalDownloader,
    URLDetector,
    DownloadType,
    DownloadStatus,
    TelegramDownloader
)

# Initialize Flask app
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# Global downloader instance
downloader = None
download_tasks = {}


def get_downloader():
    """Get or create downloader instance"""
    global downloader
    if downloader is None:
        downloader = UniversalDownloader('downloads')
    return downloader


# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Serve main web interface"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get API status"""
    return jsonify({
        'status': 'online',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'features': {
            'social_media': True,
            'torrent': True,
            'tor': True,
            'telegram': True
        }
    })


@app.route('/api/download', methods=['POST'])
def api_download():
    """Start a new download"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get options
        quality = data.get('quality', 'best')
        audio_only = data.get('audio_only', False)
        is_playlist = data.get('is_playlist', False)
        username = data.get('username')
        platform = data.get('platform')
        
        # Start download in background thread
        def run_download():
            try:
                dler = get_downloader()
                task = dler.download(
                    url,
                    quality=quality,
                    audio_only=audio_only,
                    is_playlist=is_playlist,
                    username=username,
                    platform=platform
                )
                download_tasks[task.id] = task
            except Exception as e:
                print(f"Download error: {e}")
        
        thread = threading.Thread(target=run_download)
        thread.daemon = True
        thread.start()
        
        # Return initial task info
        download_type = URLDetector.detect_type(url)
        return jsonify({
            'success': True,
            'message': 'Download started',
            'type': download_type.value,
            'estimated_time': 'Starting...'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/downloads')
def api_downloads():
    """Get all active downloads"""
    try:
        dler = get_downloader()
        tasks = dler.list_active_downloads()
        return jsonify({
            'downloads': [task.to_dict() for task in tasks],
            'count': len(tasks)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<task_id>')
def api_download_status(task_id):
    """Get specific download status"""
    try:
        dler = get_downloader()
        task = dler.get_progress(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<task_id>/cancel', methods=['POST'])
def api_cancel_download(task_id):
    """Cancel a download"""
    try:
        dler = get_downloader()
        success = dler.cancel_download(task_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Download cancelled'})
        else:
            return jsonify({'error': 'Task not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/telegram/clone', methods=['POST'])
def api_telegram_clone():
    """Clone Telegram channel/group"""
    try:
        data = request.json
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        phone = data.get('phone')
        source = data.get('source')
        dest = data.get('dest')
        clone_type = data.get('clone_type', 'channel')
        limit = data.get('limit', 100)
        
        if not all([api_id, api_hash, phone, source, dest]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Run cloning in background
        async def run_clone():
            tg = TelegramDownloader(int(api_id), api_hash, phone)
            await tg.connect()
            
            if clone_type == 'channel':
                result = await tg.clone_channel(source, dest, limit)
            else:
                result = await tg.clone_group(source, dest, limit)
            
            await tg.disconnect()
            return result
        
        # Start async task
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(run_clone())
        
        return jsonify({
            'success': True,
            'cloned_count': result,
            'message': f'Cloned {result} messages'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files')
def api_files():
    """List downloaded files"""
    try:
        download_dir = Path('downloads')
        if not download_dir.exists():
            return jsonify({'files': []})
        
        files = []
        for file_path in download_dir.rglob('*'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path.relative_to(download_dir)),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return jsonify({'files': files, 'count': len(files)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/<path:filename>')
def api_download_file(filename):
    """Download a file"""
    return send_from_directory('downloads', filename, as_attachment=True)


# ==================== CLI INTERFACE ====================

@click.group()
@click.version_option(version='2.0.0')
def cli():
    """
    Universal Downloader - Production Ready
    
    Download from 1871+ platforms including YouTube, Instagram, TikTok,
    Twitter, Facebook, Telegram, Torrents, Tor networks, and more.
    
    Examples:
    
      # Download YouTube video
      $ python app.py -u "https://youtube.com/watch?v=ID" -q 1080
      
      # Download audio only
      $ python app.py -u "https://youtube.com/watch?v=ID" -a
      
      # Download playlist
      $ python app.py -u "https://youtube.com/playlist?list=ID" -l
      
      # Download Instagram profile
      $ python app.py --username username --platform instagram
      
      # Download torrent
      $ python app.py -u "magnet:?xt=urn:btih:HASH"
      
      # Download from Tor
      $ python app.py -u "http://example.onion/file.zip"
      
      # Clone Telegram channel
      $ python app.py --telegram --api-id ID --api-hash HASH \\
          --phone +1234567890 --clone-source @src --clone-dest @dest
      
      # Start web interface
      $ python app.py --web --port 5000
    """
    pass


@cli.command()
@click.option('-u', '--url', help='URL to download')
@click.option('-q', '--quality', default='best', 
              type=click.Choice(['8k', '4k', '1440', '1080', '720', '480', '360', 'best']),
              help='Video quality')
@click.option('-a', '--audio-only', is_flag=True, help='Download audio only (MP3)')
@click.option('-l', '--playlist', is_flag=True, help='Download playlist')
@click.option('--username', help='Username for profile download')
@click.option('-P', '--platform', help='Platform name (instagram, tiktok, twitter, etc)')
@click.option('--telegram', is_flag=True, help='Use Telegram mode')
@click.option('--api-id', help='Telegram API ID')
@click.option('--api-hash', help='Telegram API hash')
@click.option('--phone', help='Telegram phone number')
@click.option('--channel', help='Telegram channel to download')
@click.option('--clone-source', help='Source channel/group for cloning')
@click.option('--clone-dest', help='Destination channel/group for cloning')
@click.option('--clone-type', type=click.Choice(['channel', 'group']), default='channel')
@click.option('--limit', default=100, help='Message limit for Telegram')
@click.option('-o', '--output', default='downloads', help='Output directory')
def download(url, quality, audio_only, playlist, username, platform,
             telegram, api_id, api_hash, phone, channel, 
             clone_source, clone_dest, clone_type, limit, output):
    """Download content from various platforms"""
    
    try:
        dler = UniversalDownloader(output)
        
        # Telegram mode
        if telegram:
            if not all([api_id, api_hash, phone]):
                click.echo("❌ Error: Telegram requires --api-id, --api-hash, and --phone")
                return
            
            if clone_source and clone_dest:
                # Clone channel/group
                click.echo(f"🔄 Cloning {clone_type} from {clone_source} to {clone_dest}...")
                
                async def run_clone():
                    tg = TelegramDownloader(int(api_id), api_hash, phone)
                    await tg.connect()
                    
                    if clone_type == 'channel':
                        result = await tg.clone_channel(clone_source, clone_dest, limit)
                    else:
                        result = await tg.clone_group(clone_source, clone_dest, limit)
                    
                    await tg.disconnect()
                    return result
                
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(run_clone())
                click.echo(f"✅ Cloned {result} messages")
                
            elif channel:
                # Download channel media
                click.echo(f"📥 Downloading media from {channel}...")
                
                async def run_download():
                    tg = TelegramDownloader(int(api_id), api_hash, phone)
                    await tg.connect()
                    files = await tg.download_channel_media(channel, output, limit)
                    await tg.disconnect()
                    return files
                
                loop = asyncio.new_event_loop()
                files = loop.run_until_complete(run_download())
                click.echo(f"✅ Downloaded {len(files)} files")
            else:
                click.echo("❌ Error: Specify --channel or --clone-source/--clone-dest")
            return
        
        # Auto-detect and download
        if url:
            click.echo(f"📥 Downloading: {url}")
            click.echo(f"   Type: {URLDetector.detect_type(url).value}")
            click.echo(f"   Quality: {quality}")
            click.echo(f"   Audio Only: {audio_only}")
            
            task = dler.download(
                url,
                quality=quality,
                audio_only=audio_only,
                is_playlist=playlist,
                username=username,
                platform=platform
            )
            
            if task.status == DownloadStatus.COMPLETED:
                click.echo(f"✅ Downloaded: {task.filename}")
            elif task.status == DownloadStatus.FAILED:
                click.echo(f"❌ Failed: {task.error}")
            else:
                click.echo(f"⏳ Status: {task.status.value} ({task.progress}%)")
        else:
            click.echo("❌ Error: Provide a URL with -u or --url")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.option('--port', default=5000, help='Port to run web server')
@click.option('--host', default='127.0.0.1', help='Host to bind')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def web(port, host, debug):
    """Start web interface"""
    click.echo(f"🚀 Starting web interface at http://{host}:{port}")
    click.echo("   Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=debug)


@cli.command()
def info():
    """Show system information"""
    from core.engine import (
        YTDLP_AVAILABLE, LIBTORRENT_AVAILABLE, 
        TELETHON_AVAILABLE, REQUESTS_AVAILABLE
    )
    
    try:
        import yt_dlp
        ytdlp_version = yt_dlp.version.__version__
    except:
        ytdlp_version = 'Not installed'
    
    try:
        import libtorrent
        lt_version = libtorrent.__version__
    except:
        lt_version = 'Not installed'
    
    click.echo("📊 Universal Downloader - System Info")
    click.echo("=" * 40)
    click.echo(f"Version: 2.0.0")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo("")
    click.echo("Features:")
    click.echo(f"  ✓ yt-dlp: {ytdlp_version} ({'Available' if YTDLP_AVAILABLE else 'Not available'})")
    click.echo(f"  ✓ libtorrent: {lt_version} ({'Available' if LIBTORRENT_AVAILABLE else 'Not available'})")
    click.echo(f"  ✓ Telethon: {'Available' if TELETHON_AVAILABLE else 'Not available'}")
    click.echo(f"  ✓ Requests: {'Available' if REQUESTS_AVAILABLE else 'Not available'}")
    click.echo("")
    click.echo("Supported Platforms: 1871+")
    click.echo("  YouTube, Instagram, TikTok, Twitter/X, Facebook,")
    click.echo("  LinkedIn, Snapchat, Pinterest, Reddit, Twitch,")
    click.echo("  Vimeo, Dailymotion, Bilibili, Discord, and more...")


@cli.command()
def test():
    """Run self-test"""
    click.echo("🧪 Running self-test...")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Import core
    tests_total += 1
    try:
        from core.engine import UniversalDownloader, URLDetector
        click.echo("✓ Core engine import")
        tests_passed += 1
    except Exception as e:
        click.echo(f"✗ Core engine import: {e}")
    
    # Test 2: URL detection
    tests_total += 1
    try:
        assert URLDetector.detect_type('https://youtube.com/watch?v=ID') == DownloadType.SOCIAL_MEDIA
        assert URLDetector.detect_type('magnet:?xt=urn:btih:HASH') == DownloadType.TORRENT
        assert URLDetector.detect_type('http://test.onion/file') == DownloadType.TOR
        click.echo("✓ URL detection")
        tests_passed += 1
    except Exception as e:
        click.echo(f"✗ URL detection: {e}")
    
    # Test 3: Create downloader
    tests_total += 1
    try:
        dler = UniversalDownloader('downloads')
        click.echo("✓ Downloader initialization")
        tests_passed += 1
    except Exception as e:
        click.echo(f"✗ Downloader initialization: {e}")
    
    # Test 4: yt-dlp available
    tests_total += 1
    try:
        import yt_dlp
        click.echo(f"✓ yt-dlp v{yt_dlp.version.__version__}")
        tests_passed += 1
    except Exception as e:
        click.echo(f"✗ yt-dlp: {e}")
    
    # Summary
    click.echo("")
    click.echo(f"Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        click.echo("✅ All tests passed!")
        return 0
    else:
        click.echo("⚠️ Some tests failed")
        return 1


if __name__ == '__main__':
    cli()
