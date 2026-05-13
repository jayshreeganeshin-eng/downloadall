# Universal Downloader v2.0.0 - Production Ready

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 The Ultimate All-in-One Download Solution

A professional, production-ready localhost downloader web application with **both GUI and CLI interfaces** supporting **1,871+ platforms**.

### ✨ Key Features

#### 📺 Social Media Downloads (1,871+ Platforms)
- **YouTube**: Videos, playlists, channels, shorts (up to 8K)
- **Instagram**: Posts, reels, stories, profile videos
- **TikTok**: Videos, profiles, trending content
- **Twitter/X**: Videos, threads, media
- **Facebook**: Videos, reels, posts
- **LinkedIn**: Video content
- **Snapchat**: Spotlight videos
- **Pinterest**: Pins, boards
- **Reddit**: Videos, galleries
- **Twitch**: VODs, clips
- **Vimeo**: Videos (all qualities)
- **Discord**: Media files
- **And 1,850+ more platforms via yt-dlp**

#### 🧲 Torrent Downloads
- Magnet link support
- .torrent file downloads
- Real-time progress tracking
- Pause/Resume functionality
- DHT, LSD, PEX support
- Sequential downloading

#### 🌐 Tor Network Downloads
- .onion site downloads
- Anonymous downloading
- Automatic Tor proxy configuration
- Fetch onion page content

#### 💬 Telegram Tools
- Download all media from channels/groups
- Clone channels to other channels
- Clone groups to other groups
- Configurable message limits
- Media preservation

#### 🎯 Quality Options
- **Video**: 8K (4320p), 4K (2160p), 1440p, 1080p, 720p, 480p, 360p
- **Audio**: MP3, FLAC, AAC extraction
- **Best Available**: Auto-select highest quality

---

## 📦 Installation

### Prerequisites
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv ffmpeg

# Install Python dependencies
pip install yt-dlp flask flask-cors telethon libtorrent requests click beautifulsoup4 lxml
```

### Quick Start
```bash
# Clone or download the project
cd /workspace

# Verify installation
python app.py info

# Run self-test
python app.py test
```

---

## 🖥️ Usage

### Web Interface (GUI)

```bash
# Start web server
python app.py --web --port 5000

# Open in browser
http://127.0.0.1:5000
```

**Features:**
- Modern dark theme UI
- Real-time progress tracking
- Tab-based navigation
- File management
- Telegram cloning tools

### Command Line (CLI)

```bash
# Download YouTube video (1080p)
python app.py -u "https://youtube.com/watch?v=VIDEO_ID" -q 1080

# Download audio only (MP3)
python app.py -u "https://youtube.com/watch?v=VIDEO_ID" -a

# Download playlist
python app.py -u "https://youtube.com/playlist?list=PLAYLIST_ID" -l

# Download Instagram profile
python app.py --username username --platform instagram

# Download torrent
python app.py -u "magnet:?xt=urn:btih:HASH"

# Download from Tor
python app.py -u "http://example.onion/file.zip"

# Telegram channel download
python app.py --telegram \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone +1234567890 \
  --channel @channelname

# Clone Telegram channel
python app.py --telegram \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone +1234567890 \
  --clone-source @source_channel \
  --clone-dest @dest_channel \
  --clone-type channel \
  --limit 100
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-u, --url` | URL to download |
| `-q, --quality` | Video quality (8k/4k/1440/1080/720/480/360/best) |
| `-a, --audio-only` | Download audio only (MP3) |
| `-l, --playlist` | Download playlist/channel |
| `--username` | Username for profile download |
| `-P, --platform` | Platform name (instagram, tiktok, twitter, etc.) |
| `--telegram` | Use Telegram mode |
| `--api-id` | Telegram API ID |
| `--api-hash` | Telegram API hash |
| `--phone` | Telegram phone number |
| `--channel` | Telegram channel to download |
| `--clone-source` | Source channel/group for cloning |
| `--clone-dest` | Destination channel/group |
| `--clone-type` | Type: channel or group |
| `--limit` | Message limit for Telegram |
| `-o, --output` | Output directory |

---

## 🏗️ Project Structure

```
/workspace/
├── app.py                 # Main application (Flask + CLI)
├── core/
│   ├── __init__.py
│   └── engine.py          # Core download engine
├── web/
│   ├── __init__.py
│   ├── templates/
│   │   └── index.html     # Web UI
│   └── static/
│       ├── style.css      # Styling
│       └── app.js         # Frontend JavaScript
├── downloads/             # Download directory
└── README.md              # This file
```

---

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get API status |
| `/api/download` | POST | Start new download |
| `/api/downloads` | GET | List active downloads |
| `/api/download/<id>` | GET | Get download status |
| `/api/download/<id>/cancel` | POST | Cancel download |
| `/api/telegram/clone` | POST | Clone channel/group |
| `/api/files` | GET | List downloaded files |
| `/api/files/<path>` | GET | Download file |

---

## ✅ Tests

```bash
# Run self-test
python app.py test

# Expected output:
# ✓ Core engine import
# ✓ URL detection
# ✓ Downloader initialization
# ✓ yt-dlp available
# Results: 4/4 tests passed
```

---

## 🛡️ Error Handling

- Automatic retry on network failures
- Graceful degradation if optional dependencies missing
- Detailed error messages
- Progress preservation on interruptions
- Input validation and sanitization

---

## 📝 Notes

### Telegram Setup
1. Get API credentials at https://my.telegram.org
2. Use your phone number with country code
3. First run will require SMS verification

### Torrent Notes
- Ensure port 6881 is open for incoming connections
- DHT helps find peers without trackers

### Tor Notes
- Requires Tor daemon running on port 9050
- Install: `sudo apt install tor`

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🤝 Support

For issues and feature requests, please check documentation or report bugs.

**Built with ❤️ using Python, Flask, yt-dlp, and Telethon**
