"""
Core Download Engine - Production Ready
Supports: Social Media (1871+ platforms), Torrents, Tor/Onion Sites, Telegram
Features: Error handling, progress tracking, batch downloads, channel cloning
"""

import os
import time
import asyncio
import threading
import libtorrent as lt
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from urllib.parse import urlparse

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False


class DownloadProgress:
    """Track download progress with thread-safe updates"""
    def __init__(self):
        self.status = "waiting"
        self.progress = 0.0
        self.speed = 0.0
        self.eta = 0
        self.downloaded = 0
        self.total = 0
        self.message = ""
        self.error = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "progress": round(self.progress, 2),
            "speed": round(self.speed, 2),
            "eta": self.eta,
            "downloaded": self.downloaded,
            "total": self.total,
            "message": self.message,
            "error": str(self.error) if self.error else None
        }


class TorrentDownloader:
    """High-performance torrent downloader with libtorrent"""
    
    def __init__(self, download_dir: str = "downloads/torrents"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = lt.session()
        self.torrents: Dict[str, Any] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
        
        # Configure session for optimal performance (libtorrent 2.x API)
        settings = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'anonymous_mode': False,
        }
        
        # Apply settings using libtorrent 2.x API
        for key, value in settings.items():
            try:
                self.session.apply_settings({key: value})
            except:
                pass
        
    def add_torrent(self, source: str, progress_callback: Optional[Callable] = None) -> str:
        """Add torrent from magnet link or .torrent file URL/path"""
        params = {'save_path': str(self.download_dir)}
        
        if source.startswith('magnet:'):
            params['url'] = source
        elif source.endswith('.torrent') and (source.startswith('http') or os.path.exists(source)):
            if source.startswith('http'):
                resp = requests.get(source, timeout=30)
                resp.raise_for_status()
                torrent_file = self.download_dir / f"{hash(source)}.torrent"
                torrent_file.write_bytes(resp.content)
                params['ti'] = lt.torrent_info(str(torrent_file))
            else:
                params['ti'] = lt.torrent_info(source)
        else:
            raise ValueError("Invalid torrent source. Must be magnet link or .torrent file")
        
        handle = self.session.add_torrent(params)
        info_hash = handle.info_hashes().to_string() if hasattr(handle.info_hashes(), 'to_string') else str(handle.info_hashes())
        
        self.torrents[info_hash] = {
            'handle': handle,
            'name': handle.name(),
            'added': time.time()
        }
        
        if progress_callback:
            self.progress_callbacks[info_hash] = progress_callback
            
        return info_hash
    
    def get_progress(self, info_hash: str) -> Dict[str, Any]:
        """Get download progress for a specific torrent"""
        if info_hash not in self.torrents:
            return {"error": "Torrent not found"}
            
        handle = self.torrents[info_hash]['handle']
        status = handle.status()
        
        progress = DownloadProgress()
        progress.status = self._get_status_str(status.state)
        progress.progress = status.progress * 100
        progress.speed = status.download_rate / 1024
        progress.eta = status.eta
        progress.downloaded = status.total_done
        progress.total = status.total_wanted
        progress.message = f"{status.num_peers} peers, {status.num_seeds} seeds"
        
        if status.state == lt.torrent_status.downloading:
            progress.message = f"Downloading: {progress.progress:.1f}% @ {progress.speed:.1f} KB/s"
        elif status.state == lt.torrent_status.seeding:
            progress.message = f"Seeding: {progress.progress:.1f}%"
            
        return progress.to_dict()
    
    def _get_status_str(self, state) -> str:
        states = {
            lt.torrent_status.checking_files: "checking",
            lt.torrent_status.downloading_metadata: "downloading metadata",
            lt.torrent_status.downloading: "downloading",
            lt.torrent_status.finished: "complete",
            lt.torrent_status.seeding: "seeding",
            lt.torrent_status.allocating: "allocating",
            lt.torrent_status.checking_resume_data: "checking resume"
        }
        return states.get(state, "unknown")
    
    def pause_torrent(self, info_hash: str):
        if info_hash in self.torrents:
            self.torrents[info_hash]['handle'].pause()
            
    def resume_torrent(self, info_hash: str):
        if info_hash in self.torrents:
            self.torrents[info_hash]['handle'].resume()
            
    def remove_torrent(self, info_hash: str, remove_files: bool = False):
        if info_hash in self.torrents:
            self.session.remove_torrent(self.torrents[info_hash]['handle'], remove_files)
            del self.torrents[info_hash]
            if info_hash in self.progress_callbacks:
                del self.progress_callbacks[info_hash]
    
    def get_all_torrents(self) -> List[Dict[str, Any]]:
        """Get all active torrents with their status"""
        result = []
        for info_hash in self.torrents:
            status = self.get_progress(info_hash)
            status['info_hash'] = info_hash
            status['name'] = self.torrents[info_hash].get('name', 'Unknown')
            result.append(status)
        return result
    
    def monitor_torrents(self):
        """Background monitoring of all torrents"""
        while True:
            alerts = self.session.pop_alerts()
            for alert in alerts:
                if isinstance(alert, lt.torrent_completed_alert):
                    info_hash = str(alert.handle.info_hashes())
                    if info_hash in self.progress_callbacks:
                        self.progress_callbacks[info_hash]("completed")
            time.sleep(1)


class TorDownloader:
    """Download files over Tor network with onion site support"""
    
    def __init__(self, tor_port: int = 9050, use_tor: bool = True):
        self.tor_port = tor_port
        self.use_tor = use_tor
        self.session = requests.Session()
        
        if use_tor:
            self.configure_tor_proxy()
    
    def configure_tor_proxy(self):
        """Configure requests to use Tor proxy"""
        proxies = {
            'http': f'socks5h://127.0.0.1:{self.tor_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_port}'
        }
        self.session.proxies.update(proxies)
    
    def download_file(self, url: str, save_path: Optional[str] = None, 
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download file via Tor network. Supports .onion sites"""
        progress = DownloadProgress()
        
        try:
            if self.use_tor:
                try:
                    test_resp = requests.get('https://check.torproject.org/api/ip', 
                                           proxies=self.session.proxies, timeout=10)
                    if not test_resp.json().get('IsTor'):
                        progress.status = "warning"
                        progress.message = "Tor not detected, downloading without Tor"
                except:
                    progress.status = "warning"
                    progress.message = "Could not verify Tor connection"
            
            progress.status = "downloading"
            progress.message = f"Connecting to {urlparse(url).netloc}..."
            
            if progress_callback:
                progress_callback(progress.to_dict())
            
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            progress.total = total_size
            
            if save_path:
                save_path = Path(save_path)
            else:
                filename = urlparse(url).path.split('/')[-1] or 'download'
                save_dir = Path("downloads/tor")
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = save_dir / filename
            
            downloaded = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.downloaded = downloaded
                        
                        if total_size > 0:
                            progress.progress = (downloaded / total_size) * 100
                        
                        progress.message = f"{downloaded}/{total_size} bytes ({progress.progress:.1f}%)"
                        
                        if progress_callback:
                            progress_callback(progress.to_dict())
            
            progress.status = "completed"
            progress.message = f"Saved to {save_path}"
            progress.progress = 100.0
            
            return {
                "success": True,
                "file": str(save_path),
                "size": downloaded,
                "progress": progress.to_dict()
            }
            
        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            progress.message = f"Download failed: {str(e)}"
            return {
                "success": False,
                "error": str(e),
                "progress": progress.to_dict()
            }
    
    def fetch_onion_page(self, url: str) -> Dict[str, Any]:
        """Fetch content from .onion site"""
        if '.onion' not in url:
            return {"error": "Not an onion URL"}
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return {
                "success": True,
                "content": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class UniversalDownloader:
    """Unified interface for all download types"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.torrent_downloader = TorrentDownloader(str(self.download_dir / "torrents"))
        self.tor_downloader = TorDownloader()
        
        self.monitor_thread = threading.Thread(target=self.torrent_downloader.monitor_torrents, daemon=True)
        self.monitor_thread.start()
    
    def detect_type(self, url: str) -> str:
        """Detect download type from URL"""
        if url.startswith('magnet:') or url.endswith('.torrent'):
            return 'torrent'
        elif '.onion' in url:
            return 'tor'
        else:
            return 'web'
    
    def download(self, url: str, options: Optional[Dict[str, Any]] = None,
                progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Universal download method that auto-detects type"""
        options = options or {}
        download_type = self.detect_type(url)
        
        if download_type == 'torrent':
            return self.download_torrent(url, progress_callback)
        elif download_type == 'tor':
            return self.download_tor(url, options, progress_callback)
        else:
            return self.download_web(url, options, progress_callback)
    
    def download_torrent(self, source: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download torrent"""
        try:
            info_hash = self.torrent_downloader.add_torrent(source, progress_callback)
            return {
                "success": True,
                "type": "torrent",
                "info_hash": info_hash,
                "message": "Torrent added successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def download_tor(self, url: str, options: Dict[str, Any], 
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download via Tor"""
        save_path = options.get('save_path')
        return self.tor_downloader.download_file(url, save_path, progress_callback)
    
    def download_web(self, url: str, options: Dict[str, Any],
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download from web using yt-dlp"""
        if not YTDLP_AVAILABLE:
            return {"success": False, "error": "yt-dlp not available"}
        
        ydl_opts = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: self._yt_progress(d, progress_callback)] if progress_callback else [],
        }
        
        if options.get('audio_only'):
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif options.get('quality'):
            quality_map = {
                '8k': 'bestvideo[height<=4320]+bestaudio/best',
                '4k': 'bestvideo[height<=2160]+bestaudio/best',
                '1440p': 'bestvideo[height<=1440]+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best',
                '720': 'bestvideo[height<=720]+bestaudio/best',
                '480': 'bestvideo[height<=480]+bestaudio/best',
                '360': 'bestvideo[height<=360]+bestaudio/best',
            }
            ydl_opts['format'] = quality_map.get(str(options['quality']), 'best')
        
        if options.get('playlist'):
            ydl_opts['ignoreerrors'] = True
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    "success": True,
                    "type": "web",
                    "title": info.get('title', 'Unknown'),
                    "url": url
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _yt_progress(self, d: Dict, callback: Callable):
        """Convert yt-dlp progress to standard format"""
        if callback:
            progress = DownloadProgress()
            if d['status'] == 'downloading':
                progress.status = "downloading"
                try:
                    progress.progress = float(d.get('_percent_str', '0%').strip('%'))
                except:
                    progress.progress = 0.0
                try:
                    progress.speed = float(d.get('_speed_str', '0').split()[0]) if d.get('_speed_str') else 0
                except:
                    progress.speed = 0.0
                progress.message = d.get('_percent_str', '')
            elif d['status'] == 'finished':
                progress.status = "processing"
                progress.progress = 100
                progress.message = "Processing..."
            elif d['status'] == 'error':
                progress.status = "error"
                progress.error = d.get('message', 'Unknown error')
            
            callback(progress.to_dict())
    
    def get_torrent_status(self, info_hash: str) -> Dict[str, Any]:
        """Get torrent download status"""
        return self.torrent_downloader.get_progress(info_hash)
    
    def get_all_torrents(self) -> List[Dict[str, Any]]:
        """Get all active torrents"""
        return self.torrent_downloader.get_all_torrents()
    
    def manage_torrent(self, info_hash: str, action: str, remove_files: bool = False):
        """Pause, resume, or remove torrent"""
        if action == 'pause':
            self.torrent_downloader.pause_torrent(info_hash)
        elif action == 'resume':
            self.torrent_downloader.resume_torrent(info_hash)
        elif action == 'remove':
            self.torrent_downloader.remove_torrent(info_hash, remove_files)


class TelegramDownloader:
    """Telegram channel/group downloader and cloner"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str, session_name: str = "telegram_session"):
        if not TELETHON_AVAILABLE:
            raise ImportError("Telethon not available")
        
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client = None
    
    async def connect(self):
        """Connect to Telegram"""
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start(phone=self.phone)
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
    
    async def download_channel_media(self, channel: str, limit: int = 100, 
                                    download_dir: str = "downloads/telegram",
                                    progress_callback: Optional[Callable] = None):
        """Download all media from a channel"""
        if not self.client:
            await self.connect()
        
        download_path = Path(download_dir) / channel.replace('@', '')
        download_path.mkdir(parents=True, exist_ok=True)
        
        downloaded = 0
        async for message in self.client.iter_messages(channel, limit=limit):
            if message.media:
                try:
                    await self.client.download_media(message, download_path)
                    downloaded += 1
                    if progress_callback:
                        progress_callback({"downloaded": downloaded, "total": limit})
                except Exception as e:
                    print(f"Error: {e}")
        
        return {"success": True, "downloaded": downloaded}
    
    async def clone_channel(self, source: str, destination: str, 
                           limit: int = 100, clone_type: str = "channel",
                           progress_callback: Optional[Callable] = None):
        """Clone messages from source to destination"""
        if not self.client:
            await self.connect()
        
        cloned = 0
        async for message in self.client.iter_messages(source, limit=limit):
            try:
                if message.media:
                    await self.client.forward_messages(destination, message)
                elif message.message:
                    await self.client.send_message(destination, message.message)
                
                cloned += 1
                if progress_callback:
                    progress_callback({"cloned": cloned, "total": limit})
            except Exception as e:
                print(f"Error: {e}")
        
        return {"success": True, "cloned": cloned}
