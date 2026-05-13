"""
Universal Downloader Core Engine
Supports: Social Media (1871+), Torrents, Tor/Onion, Telegram
Production Ready - Optimized & Error Handled
"""

import os
import re
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Third-party imports with error handling
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    yt_dlp = None

try:
    import libtorrent as lt
    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
    lt = None

try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    TelegramClient = None

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DownloadType(Enum):
    SOCIAL_MEDIA = "social_media"
    TORRENT = "torrent"
    TOR = "tor"
    TELEGRAM = "telegram"
    DIRECT = "direct"


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Real-time download progress tracking"""
    id: str
    url: str
    type: DownloadType
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed: str = "0 MB/s"
    eta: str = "Unknown"
    downloaded: str = "0 MB"
    total: str = "Unknown"
    filename: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "type": self.type.value,
            "status": self.status.value,
            "progress": round(self.progress, 2),
            "speed": self.speed,
            "eta": self.eta,
            "downloaded": self.downloaded,
            "total": self.total,
            "filename": self.filename,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class URLDetector:
    """Intelligent URL type detection"""
    
    TORRENT_PATTERNS = [
        r'^magnet:\?',
        r'\.torrent$',
        r'^https?://.*\.torrent',
    ]
    
    TOR_PATTERNS = [
        r'\.onion',
        r'^http[s]?://[a-z2-7]{16,56}\.onion',
    ]
    
    SOCIAL_MEDIA_DOMAINS = [
        'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com',
        'twitter.com', 'x.com', 'facebook.com', 'fb.watch',
        'linkedin.com', 'snapchat.com', 'pinterest.com', 'reddit.com',
        'twitch.tv', 'vimeo.com', 'dailymotion.com', 'bilibili.com',
        'discord.com', 'discord.gg'
    ]

    @classmethod
    def detect_type(cls, url: str) -> DownloadType:
        """Detect download type from URL"""
        if not url:
            return DownloadType.DIRECT

        url_lower = url.lower()

        # Check for torrent
        for pattern in cls.TORRENT_PATTERNS:
            if re.search(pattern, url_lower):
                return DownloadType.TORRENT

        # Check for Tor
        for pattern in cls.TOR_PATTERNS:
            if re.search(pattern, url_lower):
                return DownloadType.TOR

        # Check for social media
        for domain in cls.SOCIAL_MEDIA_DOMAINS:
            if domain in url_lower:
                return DownloadType.SOCIAL_MEDIA

        # Default to direct download
        return DownloadType.DIRECT

    @classmethod
    def is_playlist(cls, url: str) -> bool:
        """Check if URL is a playlist"""
        playlist_indicators = ['playlist', 'list=', '/channel/', '/c/', '/@']
        return any(indicator in url.lower() for indicator in playlist_indicators)


class TorrentDownloader:
    """High-performance torrent downloader with libtorrent"""
    
    def __init__(self, download_dir: str = "downloads"):
        if not LIBTORRENT_AVAILABLE:
            raise ImportError("libtorrent not available")
        
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = lt.session({'listen_interfaces': '0.0.0.0:6881'})
        self.torrents: Dict[str, Any] = {}
        logger.info("Torrent downloader initialized")

    def add_magnet(self, magnet_link: str, progress_callback: Optional[Callable] = None) -> str:
        """Add magnet link to download queue"""
        try:
            params = {
                'save_path': str(self.download_dir),
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'flags': lt.torrent_flags.auto_managed
            }
            
            info = lt.parse_magnet_uri(magnet_link)
            params['ti'] = info
            
            handle = self.session.add_torrent(params)
            torrent_id = str(handle.info_hash())
            
            self.torrents[torrent_id] = {
                'handle': handle,
                'callback': progress_callback,
                'start_time': time.time()
            }
            
            logger.info(f"Added magnet: {torrent_id[:8]}...")
            return torrent_id
            
        except Exception as e:
            logger.error(f"Error adding magnet: {e}")
            raise

    def add_torrent_file(self, torrent_path: str, progress_callback: Optional[Callable] = None) -> str:
        """Add .torrent file to download queue"""
        try:
            info = lt.torrent_info(torrent_path)
            params = {
                'ti': info,
                'save_path': str(self.download_dir),
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                'flags': lt.torrent_flags.auto_managed
            }
            
            handle = self.session.add_torrent(params)
            torrent_id = str(handle.info_hash())
            
            self.torrents[torrent_id] = {
                'handle': handle,
                'callback': progress_callback,
                'start_time': time.time()
            }
            
            logger.info(f"Added torrent file: {torrent_id[:8]}...")
            return torrent_id
            
        except Exception as e:
            logger.error(f"Error adding torrent file: {e}")
            raise

    def get_progress(self, torrent_id: str) -> Dict[str, Any]:
        """Get torrent download progress"""
        if torrent_id not in self.torrents:
            raise ValueError(f"Torrent {torrent_id} not found")
        
        handle = self.torrents[torrent_id]['handle']
        status = handle.status()
        
        progress = status.progress * 100
        download_rate = status.download_rate / 1024 / 1024  # MB/s
        uploaded_rate = status.upload_rate / 1024 / 1024
        total_download = status.total_done / 1024 / 1024
        total_size = status.total_wanted / 1024 / 1024
        
        eta_seconds = int(status.eta)
        eta_str = f"{eta_seconds // 3600}h {(eta_seconds % 3600) // 60}m" if eta_seconds > 0 else "Unknown"
        
        state_map = {
            lt.torrent_status.downloading: DownloadStatus.DOWNLOADING,
            lt.torrent_status.seeding: DownloadStatus.COMPLETED,
            lt.torrent_status.finished: DownloadStatus.COMPLETED,
            lt.torrent_status.paused: DownloadStatus.PAUSED,
        }
        
        status_enum = state_map.get(status.state, DownloadStatus.DOWNLOADING)
        
        return {
            'progress': progress,
            'speed': f"{download_rate:.2f} MB/s",
            'upload_speed': f"{uploaded_rate:.2f} MB/s",
            'eta': eta_str,
            'downloaded': f"{total_download:.2f} MB",
            'total': f"{total_size:.2f} MB",
            'peers': status.num_peers,
            'seeds': status.num_seeds,
            'status': status_enum.value,
            'name': status.name or "Unknown"
        }

    def pause(self, torrent_id: str):
        """Pause torrent download"""
        if torrent_id in self.torrents:
            self.torrents[torrent_id]['handle'].pause()
            logger.info(f"Paused torrent: {torrent_id[:8]}...")

    def resume(self, torrent_id: str):
        """Resume paused torrent"""
        if torrent_id in self.torrents:
            self.torrents[torrent_id]['handle'].resume()
            logger.info(f"Resumed torrent: {torrent_id[:8]}...")

    def cancel(self, torrent_id: str):
        """Cancel and remove torrent"""
        if torrent_id in self.torrents:
            self.session.remove_torrent(self.torrents[torrent_id]['handle'])
            del self.torrents[torrent_id]
            logger.info(f"Cancelled torrent: {torrent_id[:8]}...")

    def run_session(self, interval: float = 1.0):
        """Run torrent session loop (call in background thread)"""
        while True:
            try:
                self.session.post_torrent_updates()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Session error: {e}")
                break


class TorDownloader:
    """Tor network downloader for .onion sites"""
    
    def __init__(self, tor_proxy: str = "socks5://127.0.0.1:9050"):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not available")
        
        self.tor_proxy = tor_proxy
        self.session = self._create_tor_session()
        logger.info("Tor downloader initialized")

    def _create_tor_session(self) -> requests.Session:
        """Create requests session with Tor proxy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        proxies = {
            'http': self.tor_proxy,
            'https': self.tor_proxy
        }
        
        session.proxies.update(proxies)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session

    def download(self, url: str, save_path: Optional[str] = None, 
                 progress_callback: Optional[Callable] = None) -> str:
        """Download file from Tor network"""
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            filename = self._extract_filename(url, response)
            output_path = Path(save_path or "downloads") / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress, downloaded, total_size)
            
            logger.info(f"Downloaded from Tor: {filename}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Tor download error: {e}")
            raise

    def fetch_page(self, url: str) -> str:
        """Fetch HTML content from .onion site"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Tor page fetch error: {e}")
            raise

    def _extract_filename(self, url: str, response: requests.Response) -> str:
        """Extract filename from URL or response headers"""
        # Check Content-Disposition header
        content_disp = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[1].strip('"\'')
            return filename
        
        # Extract from URL
        parsed = url.split('/')[-1]
        if parsed and '.' in parsed:
            return parsed
        
        # Generate timestamp-based name
        return f"tor_download_{int(time.time())}.bin"


class TelegramDownloader:
    """Telegram media downloader and cloner"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str, 
                 session_name: str = "telegram_downloader"):
        if not TELETHON_AVAILABLE:
            raise ImportError("telethon not available")
        
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        logger.info("Telegram downloader initialized")

    async def connect(self):
        """Connect to Telegram"""
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start(phone=self.phone)
        logger.info("Connected to Telegram")

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")

    async def download_channel_media(self, channel_username: str, 
                                     output_dir: str = "downloads/telegram",
                                     limit: int = 100,
                                     progress_callback: Optional[Callable] = None) -> List[str]:
        """Download all media from a Telegram channel"""
        if not self.client:
            raise RuntimeError("Not connected to Telegram")
        
        output_path = Path(output_dir) / channel_username.replace('@', '')
        output_path.mkdir(parents=True, exist_ok=True)
        
        downloaded_files = []
        entity = await self.client.get_entity(channel_username)
        
        count = 0
        async for message in self.client.iter_messages(entity, limit=limit):
            if message.media:
                try:
                    file_path = await self.client.download_media(
                        message,
                        output_path,
                        progress_callback=progress_callback
                    )
                    if file_path:
                        downloaded_files.append(file_path)
                        count += 1
                        logger.info(f"Downloaded {count}/{limit} files")
                except Exception as e:
                    logger.error(f"Error downloading message: {e}")
        
        logger.info(f"Downloaded {len(downloaded_files)} files from {channel_username}")
        return downloaded_files

    async def clone_channel(self, source_channel: str, dest_channel: str,
                           limit: int = 100,
                           progress_callback: Optional[Callable] = None) -> int:
        """Clone messages from source channel to destination channel"""
        if not self.client:
            raise RuntimeError("Not connected to Telegram")
        
        source = await self.client.get_entity(source_channel)
        dest = await self.client.get_entity(dest_channel)
        
        cloned_count = 0
        async for message in self.client.iter_messages(source, limit=limit):
            try:
                # Forward message
                await self.client.forward_messages(dest, message)
                cloned_count += 1
                
                if progress_callback:
                    await progress_callback(cloned_count, limit)
                    
            except Exception as e:
                logger.error(f"Error cloning message: {e}")
        
        logger.info(f"Cloned {cloned_count} messages from {source_channel} to {dest_channel}")
        return cloned_count

    async def clone_group(self, source_group: str, dest_group: str,
                         limit: int = 100,
                         progress_callback: Optional[Callable] = None) -> int:
        """Clone messages from source group to destination group"""
        return await self.clone_channel(source_group, dest_group, limit, progress_callback)


class SocialMediaDownloader:
    """Universal social media downloader using yt-dlp"""
    
    def __init__(self, download_dir: str = "downloads"):
        if not YTDLP_AVAILABLE:
            raise ImportError("yt-dlp not available")
        
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Social media downloader initialized")

    def download(self, url: str, quality: str = "best", 
                 audio_only: bool = False,
                 is_playlist: bool = False,
                 username: Optional[str] = None,
                 platform: Optional[str] = None,
                 progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download from social media platforms"""
        
        # Build yt-dlp options
        ydl_opts = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Quality settings
        if audio_only:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            quality_map = {
                '8k': 'bestvideo[height<=4320]+bestaudio/best',
                '4k': 'bestvideo[height<=2160]+bestaudio/best',
                '1440': 'bestvideo[height<=1440]+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best',
                '720': 'bestvideo[height<=720]+bestaudio/best',
                '480': 'bestvideo[height<=480]+bestaudio/best',
                '360': 'bestvideo[height<=360]+bestaudio/best',
                'best': 'bestvideo+bestaudio/best',
            }
            ydl_opts['format'] = quality_map.get(quality.lower(), 'best')
        
        # Playlist handling
        if is_playlist or ('playlist' in url.lower() or 'list=' in url.lower()):
            ydl_opts['ignoreerrors'] = True
            ydl_opts['max_downloads'] = 100  # Limit for safety
        
        # Username/platform specific
        if username and platform:
            if platform.lower() == 'instagram':
                url = f"https://instagram.com/{username}"
            elif platform.lower() == 'tiktok':
                url = f"https://tiktok.com/@{username}"
            elif platform.lower() == 'twitter':
                url = f"https://twitter.com/{username}"
            elif platform.lower() == 'youtube':
                url = f"https://youtube.com/@{username}"
        
        # Progress callback wrapper
        def progress_hook(d):
            if progress_callback:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    progress = (downloaded / total * 100) if total > 0 else 0
                    progress_callback({
                        'status': 'downloading',
                        'progress': progress,
                        'speed': f"{speed / 1024 / 1024:.2f} MB/s" if speed else "0 MB/s",
                        'eta': f"{eta // 60}m {eta % 60}s" if eta else "Unknown",
                        'downloaded': f"{downloaded / 1024 / 1024:.2f} MB",
                        'total': f"{total / 1024 / 1024:.2f} MB" if total else "Unknown"
                    })
                elif d['status'] == 'finished':
                    progress_callback({
                        'status': 'processing',
                        'progress': 100,
                        'speed': "0 MB/s",
                        'eta': "Processing...",
                        'downloaded': "Complete",
                        'total': "Complete"
                    })
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get filename
                filename = ydl.prepare_filename(info)
                if audio_only:
                    filename = filename.rsplit('.', 1)[0] + '.mp3'
                
                return {
                    'success': True,
                    'filename': filename,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'platform': info.get('extractor', 'unknown'),
                    'url': url
                }
                
        except Exception as e:
            logger.error(f"Social media download error: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }


class UniversalDownloader:
    """Main unified downloader interface"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.social_downloader = SocialMediaDownloader(download_dir)
        self.torrent_downloader = TorrentDownloader(download_dir) if LIBTORRENT_AVAILABLE else None
        self.tor_downloader = TorDownloader() if REQUESTS_AVAILABLE else None
        self.telegram_client = None
        
        self.active_downloads: Dict[str, DownloadProgress] = {}
        logger.info("Universal downloader initialized")

    def create_download_task(self, url: str, **kwargs) -> DownloadProgress:
        """Create a new download task"""
        import uuid
        
        download_type = URLDetector.detect_type(url)
        task_id = str(uuid.uuid4())[:8]
        
        progress = DownloadProgress(
            id=task_id,
            url=url,
            type=download_type,
            filename=kwargs.get('filename', '')
        )
        
        self.active_downloads[task_id] = progress
        return progress

    def download(self, url: str, **kwargs) -> DownloadProgress:
        """Main download method - auto-detects type and downloads"""
        
        task = self.create_download_task(url, **kwargs)
        download_type = URLDetector.detect_type(url)
        
        try:
            if download_type == DownloadType.TORRENT:
                return self._download_torrent(task, url, **kwargs)
            elif download_type == DownloadType.TOR:
                return self._download_tor(task, url, **kwargs)
            elif download_type == DownloadType.SOCIAL_MEDIA:
                return self._download_social(task, url, **kwargs)
            else:
                return self._download_direct(task, url, **kwargs)
                
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now()
            logger.error(f"Download failed: {e}")
            return task

    def _download_torrent(self, task: DownloadProgress, url: str, **kwargs) -> DownloadProgress:
        """Handle torrent download"""
        if not self.torrent_downloader:
            raise RuntimeError("Torrent downloader not available")
        
        task.status = DownloadStatus.DOWNLOADING
        
        if url.startswith('magnet:'):
            torrent_id = self.torrent_downloader.add_magnet(url)
        else:
            torrent_id = self.torrent_downloader.add_torrent_file(url)
        
        # Get initial progress
        progress_info = self.torrent_downloader.get_progress(torrent_id)
        task.progress = progress_info['progress']
        task.speed = progress_info['speed']
        task.eta = progress_info['eta']
        task.downloaded = progress_info['downloaded']
        task.total = progress_info['total']
        task.filename = progress_info['name']
        task.updated_at = datetime.now()
        
        return task

    def _download_tor(self, task: DownloadProgress, url: str, **kwargs) -> DownloadProgress:
        """Handle Tor download"""
        if not self.tor_downloader:
            raise RuntimeError("Tor downloader not available")
        
        task.status = DownloadStatus.DOWNLOADING
        
        def progress_cb(progress, downloaded, total):
            task.progress = progress
            task.downloaded = f"{downloaded / 1024 / 1024:.2f} MB"
            task.total = f"{total / 1024 / 1024:.2f} MB" if total > 0 else "Unknown"
            task.updated_at = datetime.now()
        
        output_path = self.tor_downloader.download(url, str(self.download_dir), progress_cb)
        
        task.status = DownloadStatus.COMPLETED
        task.progress = 100
        task.filename = Path(output_path).name
        task.updated_at = datetime.now()
        
        return task

    def _download_social(self, task: DownloadProgress, url: str, **kwargs) -> DownloadProgress:
        """Handle social media download"""
        task.status = DownloadStatus.DOWNLOADING
        
        def progress_cb(info):
            task.progress = info.get('progress', 0)
            task.speed = info.get('speed', '0 MB/s')
            task.eta = info.get('eta', 'Unknown')
            task.downloaded = info.get('downloaded', '0 MB')
            task.total = info.get('total', 'Unknown')
            task.status = DownloadStatus.PROCESSING if info.get('status') == 'processing' else DownloadStatus.DOWNLOADING
            task.updated_at = datetime.now()
        
        result = self.social_downloader.download(
            url,
            quality=kwargs.get('quality', 'best'),
            audio_only=kwargs.get('audio_only', False),
            is_playlist=kwargs.get('is_playlist', False),
            username=kwargs.get('username'),
            platform=kwargs.get('platform'),
            progress_callback=progress_cb
        )
        
        if result.get('success'):
            task.status = DownloadStatus.COMPLETED
            task.progress = 100
            task.filename = Path(result['filename']).name
            task.metadata = {
                'title': result.get('title'),
                'duration': result.get('duration'),
                'platform': result.get('platform')
            }
        else:
            task.status = DownloadStatus.FAILED
            task.error = result.get('error', 'Unknown error')
        
        task.updated_at = datetime.now()
        return task

    def _download_direct(self, task: DownloadProgress, url: str, **kwargs) -> DownloadProgress:
        """Handle direct HTTP download"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests not available")
        
        task.status = DownloadStatus.DOWNLOADING
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            filename = self._extract_filename(url, response)
            output_path = self.download_dir / filename
            
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            task.progress = (downloaded / total_size) * 100
                        
                        task.downloaded = f"{downloaded / 1024 / 1024:.2f} MB"
                        task.total = f"{total_size / 1024 / 1024:.2f} MB"
                        task.updated_at = datetime.now()
            
            task.status = DownloadStatus.COMPLETED
            task.progress = 100
            task.filename = filename
            task.updated_at = datetime.now()
            
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now()
        
        return task

    def _extract_filename(self, url: str, response: Optional[Any] = None) -> str:
        """Extract filename from URL or response"""
        if response and hasattr(response, 'headers'):
            content_disp = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disp:
                return content_disp.split('filename=')[1].strip('"\'')
        
        parsed = url.split('/')[-1]
        if parsed and '.' in parsed:
            return parsed
        
        return f"download_{int(time.time())}.bin"

    def get_progress(self, task_id: str) -> Optional[DownloadProgress]:
        """Get progress for a specific task"""
        return self.active_downloads.get(task_id)

    def list_active_downloads(self) -> List[DownloadProgress]:
        """List all active downloads"""
        return list(self.active_downloads.values())

    def cancel_download(self, task_id: str) -> bool:
        """Cancel a download task"""
        if task_id in self.active_downloads:
            task = self.active_downloads[task_id]
            if task.type == DownloadType.TORRENT:
                # Cancel torrent
                pass
            task.status = DownloadStatus.CANCELLED
            task.updated_at = datetime.now()
            return True
        return False

    def cleanup_completed(self, max_age_hours: int = 24):
        """Remove completed downloads older than max_age_hours"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task in self.active_downloads.items():
            if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                age = (now - task.updated_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_downloads[task_id]
        
        return len(to_remove)


# Export main classes
__all__ = [
    'UniversalDownloader',
    'SocialMediaDownloader',
    'TorrentDownloader',
    'TorDownloader',
    'TelegramDownloader',
    'URLDetector',
    'DownloadProgress',
    'DownloadType',
    'DownloadStatus'
]
