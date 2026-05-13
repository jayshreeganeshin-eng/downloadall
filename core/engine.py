"""
Universal Downloader Core Engine
Supports 1871+ platforms via yt-dlp + Telegram API
Optimized for error handling, logging, and modularity
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Third-party imports
try:
    import yt_dlp
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel, Chat
    from telethon.tl.functions.messages import GetHistoryRequest
    from telethon.tl.functions.channels import GetFullChannelRequest
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install yt-dlp telethon flask flask-cors requests beautifulsoup4 lxml")
    sys.exit(1)


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    id: str
    url: Optional[str]
    username: Optional[str]
    platform: str
    quality: str
    audio_only: bool
    playlist: bool
    output_path: str
    status: DownloadStatus
    progress: float
    message: str
    files_downloaded: List[str]
    created_at: str
    completed_at: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        return d
    
    @classmethod
    def create(cls, task_id: str, **kwargs) -> 'DownloadTask':
        return cls(
            id=task_id,
            url=kwargs.get('url'),
            username=kwargs.get('username'),
            platform=kwargs.get('platform', 'unknown'),
            quality=kwargs.get('quality', 'best'),
            audio_only=kwargs.get('audio_only', False),
            playlist=kwargs.get('playlist', False),
            output_path=kwargs.get('output_path', './downloads'),
            status=DownloadStatus.PENDING,
            progress=0.0,
            message='Initializing...',
            files_downloaded=[],
            created_at=datetime.now().isoformat(),
            completed_at=None
        )


class ProgressHook:
    """yt-dlp progress hook for real-time updates"""
    
    def __init__(self, task_id: str, callback: Optional[Callable] = None):
        self.task_id = task_id
        self.callback = callback
        self.logger = logging.getLogger(f"hook.{task_id}")
    
    def __call__(self, d: Dict[str, Any]):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                progress = (downloaded / total) * 100
            else:
                progress = 0
            
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            msg = f"Downloading: {progress:.1f}%"
            if speed:
                msg += f" at {self._format_speed(speed)}"
            if eta:
                msg += f" ETA: {self._format_eta(eta)}"
            
            self._update_progress(progress, msg)
            
        elif d['status'] == 'finished':
            filename = d.get('filename', 'unknown')
            self._update_progress(100, f"Downloaded: {os.path.basename(filename)}")
            
        elif d['status'] == 'error':
            self._update_progress(0, f"Error: {d.get('message', 'Unknown error')}")
    
    def _update_progress(self, progress: float, message: str):
        if self.callback:
            self.callback(self.task_id, progress, message)
        self.logger.info(f"{progress:.1f}% - {message}")
    
    @staticmethod
    def _format_speed(speed: float) -> str:
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"
    
    @staticmethod
    def _format_eta(eta: int) -> str:
        if eta < 60:
            return f"{eta}s"
        elif eta < 3600:
            return f"{eta//60}m {eta%60}s"
        else:
            return f"{eta//3600}h {(eta%3600)//60}m"


class UniversalDownloader:
    """Main downloader class for all social media platforms"""
    
    SUPPORTED_PLATFORMS = {
        'youtube': ['youtube.com', 'youtu.be', 'youtube-nocookie.com'],
        'instagram': ['instagram.com'],
        'tiktok': ['tiktok.com', 'vm.tiktok.com'],
        'twitter': ['twitter.com', 'x.com'],
        'facebook': ['facebook.com', 'fb.watch'],
        'linkedin': ['linkedin.com'],
        'snapchat': ['snapchat.com'],
        'pinterest': ['pinterest.com', 'pin.it'],
        'reddit': ['reddit.com', 'redd.it'],
        'twitch': ['twitch.tv'],
        'vimeo': ['vimeo.com'],
        'dailymotion': ['dailymotion.com'],
        'bilibili': ['bilibili.com', 'b23.tv'],
        'telegram': ['t.me'],
    }
    
    def __init__(self, download_dir: str = './downloads', log_level: str = 'INFO'):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, DownloadTask] = {}
        self.logger = self._setup_logging(log_level)
        
    def _setup_logging(self, level: str) -> logging.Logger:
        logger = logging.getLogger('UniversalDownloader')
        logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler('./logs/downloader.log')
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    def detect_platform(self, url: Optional[str] = None, username: Optional[str] = None) -> str:
        """Detect platform from URL or username"""
        if url:
            for platform, domains in self.SUPPORTED_PLATFORMS.items():
                if platform != 'telegram':  # Telegram handled separately
                    for domain in domains:
                        if domain in url.lower():
                            return platform
        return 'unknown'
    
    def _get_ydl_options(self, task: DownloadTask, progress_hook: ProgressHook) -> Dict[str, Any]:
        """Build yt-dlp options based on task parameters"""
        output_template = str(self.download_dir / f'%(title)s_%(id)s.%(ext)s')
        
        opts = {
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
            'ignoreerrors': True,
            'retries': 3,
            'fragment_retries': 3,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        if task.audio_only:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # Quality mapping
            quality_map = {
                '2160': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best',
                '1440': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
                '360': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
                'best': 'bestvideo+bestaudio/best',
            }
            opts['format'] = quality_map.get(task.quality, 'best')
            opts['merge_output_format'] = 'mp4'
        
        if task.playlist:
            opts['playlistend'] = 100  # Limit to 100 by default, can be customized
        
        return opts
    
    async def download(self, task: DownloadTask, callback: Optional[Callable] = None) -> DownloadTask:
        """Execute download task"""
        self.tasks[task.id] = task
        
        try:
            task.status = DownloadStatus.DOWNLOADING
            task.message = "Starting download..."
            
            progress_hook = ProgressHook(task.id, callback)
            
            # Determine what to download
            urls = []
            if task.url:
                urls.append(task.url)
            elif task.username:
                # Construct profile URLs based on platform
                profile_urls = {
                    'instagram': f'https://instagram.com/{task.username}',
                    'tiktok': f'https://tiktok.com/@{task.username}',
                    'twitter': f'https://twitter.com/{task.username}',
                    'youtube': f'https://youtube.com/@{task.username}',
                    'pinterest': f'https://pinterest.com/{task.username}',
                }
                url = profile_urls.get(task.platform)
                if url:
                    urls.append(url)
                else:
                    raise ValueError(f"Unsupported platform for username: {task.platform}")
            
            if not urls:
                raise ValueError("No URL or username provided")
            
            # Run yt-dlp
            loop = asyncio.get_event_loop()
            
            def run_download():
                with yt_dlp.YoutubeDL(self._get_ydl_options(task, progress_hook)) as ydl:
                    for url in urls:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            entries = info.get('entries', [info])
                            for entry in entries:
                                if entry and 'filepath' in entry:
                                    task.files_downloaded.append(entry['filepath'])
            
            await loop.run_in_executor(None, run_download)
            
            task.status = DownloadStatus.COMPLETED
            task.progress = 100
            task.message = f"Completed! {len(task.files_downloaded)} file(s) downloaded"
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}", exc_info=True)
            task.status = DownloadStatus.FAILED
            task.message = f"Failed: {str(e)}"
            task.completed_at = datetime.now().isoformat()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values()]
    
    def cancel_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task and task.status == DownloadStatus.DOWNLOADING:
            task.status = DownloadStatus.CANCELLED
            task.message = "Cancelled by user"
            task.completed_at = datetime.now().isoformat()
            return True
        return False


class TelegramDownloader:
    """Telegram-specific downloader with channel/group cloning support"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str, 
                 download_dir: str = './downloads', log_level: str = 'INFO'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.client: Optional[TelegramClient] = None
        self.logger = self._setup_logging(log_level)
        self.tasks: Dict[str, DownloadTask] = {}
    
    def _setup_logging(self, level: str) -> logging.Logger:
        logger = logging.getLogger('TelegramDownloader')
        logger.setLevel(getattr(logging, level.upper()))
        
        ch = logging.StreamHandler()
        fh = logging.FileHandler('./logs/telegram.log')
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    async def connect(self) -> bool:
        """Connect to Telegram"""
        try:
            self.client = TelegramClient('session_name', self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            self.logger.info("Connected to Telegram successfully")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            self.logger.info("Disconnected from Telegram")
    
    async def download_channel_media(self, task: DownloadTask, channel: str, 
                                     limit: int = 100, callback: Optional[Callable] = None) -> DownloadTask:
        """Download all media from a channel"""
        self.tasks[task.id] = task
        
        try:
            task.status = DownloadStatus.DOWNLOADING
            task.message = f"Connecting to channel: {channel}"
            
            if not self.client:
                await self.connect()
            
            # Resolve channel
            entity = await self.client.get_entity(channel)
            task.message = f"Found channel: {entity.title}"
            
            downloaded_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.media:
                    if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                        path = await self.client.download_media(
                            message,
                            file=str(self.download_dir / f"{entity.title}_{message.id}")
                        )
                        if path:
                            task.files_downloaded.append(path)
                            downloaded_count += 1
                            
                            if callback:
                                progress = (downloaded_count / limit) * 100
                                callback(task.id, progress, f"Downloaded {downloaded_count}/{limit}")
            
            task.status = DownloadStatus.COMPLETED
            task.progress = 100
            task.message = f"Completed! {downloaded_count} files downloaded from {entity.title}"
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}", exc_info=True)
            task.status = DownloadStatus.FAILED
            task.message = f"Failed: {str(e)}"
            task.completed_at = datetime.now().isoformat()
        
        return task
    
    async def clone_channel(self, task: DownloadTask, source: str, dest: str,
                           limit: int = 100, callback: Optional[Callable] = None) -> DownloadTask:
        """Clone all messages from source channel to destination channel"""
        self.tasks[task.id] = task
        
        try:
            task.status = DownloadStatus.DOWNLOADING
            task.message = f"Cloning {source} to {dest}..."
            
            if not self.client:
                await self.connect()
            
            source_entity = await self.client.get_entity(source)
            dest_entity = await self.client.get_entity(dest)
            
            task.message = f"Found source: {source_entity.title}, destination: {dest_entity.title}"
            
            cloned_count = 0
            async for message in self.client.iter_messages(source_entity, limit=limit):
                try:
                    # Forward message
                    await self.client.forward_messages(dest_entity, message)
                    cloned_count += 1
                    
                    if callback:
                        progress = (cloned_count / limit) * 100
                        callback(task.id, progress, f"Cloned {cloned_count}/{limit} messages")
                
                except Exception as e:
                    self.logger.warning(f"Failed to clone message {message.id}: {e}")
                    continue
            
            task.status = DownloadStatus.COMPLETED
            task.progress = 100
            task.message = f"Completed! {cloned_count}/{limit} messages cloned"
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Clone failed: {e}", exc_info=True)
            task.status = DownloadStatus.FAILED
            task.message = f"Failed: {str(e)}"
            task.completed_at = datetime.now().isoformat()
        
        return task
    
    async def clone_group(self, task: DownloadTask, source: str, dest: str,
                         limit: int = 100, callback: Optional[Callable] = None) -> DownloadTask:
        """Clone all messages from source group to destination group"""
        # Same implementation as clone_channel for now
        return await self.clone_channel(task, source, dest, limit, callback)
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values()]
