# 🌐 Universal Downloader - Production Ready

A powerful localhost downloader web application with both GUI and CLI interfaces supporting **1871+ platforms** via yt-dlp, plus **Torrent downloads**, **Tor/Onion sites**, and full **Telegram channel/group cloning** capabilities.

## ✨ Features

### Supported Platforms (1871+)
- **YouTube** - Videos, playlists, channels, shorts (up to 8K)
- **Instagram** - Posts, reels, stories, profile videos
- **TikTok** - Videos, profiles
- **X (Twitter)** - Tweets, threads, profiles
- **Facebook** - Videos, reels
- **LinkedIn** - Videos, posts
- **Snapchat** - Stories, spotlights
- **Pinterest** - Pins, boards, profiles
- **Reddit** - Posts, subreddits
- **Twitch** - Clips, videos
- **Vimeo** - Videos
- **Dailymotion** - Videos
- **Bilibili** - Videos
- **Discord** - Messages, media (via URL)
- **And 1850+ more platforms!**

### Download Options
- 🎬 Video quality: 8K, 4K (2160p), 2K (1440p), 1080p, 720p, 480p, 360p
- 🎵 Audio-only extraction (MP3, FLAC, AAC)
- 📺 Playlist/Channel bulk download
- 👤 Profile video downloads
- 🔄 Batch downloads

### Torrent Downloads
- 🧲 Magnet link support
- 📄 .torrent file downloads
- ⏸️ Pause/Resume functionality
- 📊 Real-time progress tracking
- 🌐 DHT, LSD, PEX support

### Tor/Onion Sites
- 🧅 .onion site downloads
- 🔒 Anonymous downloading via Tor network
- 🌐 Automatic Tor proxy configuration
- 📄 Fetch onion page content

### Telegram Features
- 📥 Download all media from channels/groups
- 🔄 Clone entire channels to other channels
- 🔄 Clone groups to other groups
- ⚙️ Configurable message limits
- 🔐 Secure authentication

## 📁 Project Structure

```
/workspace/
├── app.py                 # Main application (Flask + CLI)
├── core/
│   └── engine.py          # Core download engine
├── web/
│   ├── templates/
│   │   └── index.html     # Web interface
│   └── static/
│       ├── style.css      # Modern dark theme
│       └── app.js         # Frontend JavaScript
├── downloads/             # Downloaded files
├── logs/                  # Application logs
└── README.md              # This file
```

## 🚀 Quick Start

### Installation

Dependencies are pre-installed. If needed:
```bash
pip install yt-dlp telethon flask flask-cors requests beautifulsoup4 lxml
```

### Web Interface (GUI)

```bash
# Start web server
python app.py --web

# Or with custom port
python app.py --web --port 8080

# Accessible at http://127.0.0.1:5000
```

### Command Line (CLI)

```bash
# Download YouTube video (1080p)
python app.py -u "https://youtube.com/watch?v=VIDEO_ID" -q 1080

# Download audio only (MP3)
python app.py -u "https://youtube.com/watch?v=VIDEO_ID" -a

# Download playlist
python app.py -u "https://youtube.com/playlist?list=PLAYLIST_ID" -l

# Download Instagram profile
python app.py --username username -P instagram

# Download TikTok profile
python app.py --username username -P tiktok

# Download X/Twitter profile
python app.py --username username -P twitter
```

### Telegram Operations

```bash
# Download channel media
python app.py --telegram \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone +1234567890 \
  --channel @channelname

# Clone channel to another channel
python app.py --telegram \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone +1234567890 \
  --clone-source @source_channel \
  --clone-dest @dest_channel \
  --clone-type channel \
  --limit 100

# Clone group to another group
python app.py --telegram \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone +1234567890 \
  --clone-source @source_group \
  --clone-dest @dest_group \
  --clone-type group
```

## 📖 API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/platforms` | GET | List supported platforms |
| `/api/download` | POST | Start new download |
| `/api/status/<id>` | GET | Get task status |
| `/api/tasks` | GET | List all tasks |
| `/api/cancel/<id>` | POST | Cancel task |
| `/api/downloads` | GET | List downloaded files |
| `/api/telegram/configure` | POST | Configure Telegram |
| `/api/telegram/download` | POST | Download from Telegram |
| `/api/telegram/clone` | POST | Clone channel/group |
| `/api/telegram/status` | GET | Check Telegram status |

### Download Request Format

```json
{
  "url": "https://...",        // Optional: URL to download
  "username": "user",          // Optional: Username for profile
  "platform": "youtube",       // Optional: Platform name
  "quality": "1080",           // Optional: Quality (2160/1440/1080/720/480/360/best)
  "audio_only": false,         // Optional: Extract audio only
  "playlist": false            // Optional: Download playlist
}
```

## 🛠️ Configuration

### Getting Telegram API Credentials

1. Visit https://my.telegram.org
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy your `api_id` and `api_hash`

### Quality Options

| Quality | Resolution | Best For |
|---------|------------|----------|
| 2160 | 4K UHD | Highest quality, large files |
| 1440 | 2K QHD | High quality monitors |
| 1080 | Full HD | Standard HD, good balance |
| 720 | HD | Faster downloads, decent quality |
| 480 | SD | Mobile devices, slow connections |
| 360 | Low | Minimal bandwidth |
| best | Auto | Best available quality |

## 🔧 Troubleshooting

### Common Issues

**Module not found errors:**
```bash
pip install -U yt-dlp telethon flask flask-cors
```

**Telegram connection failed:**
- Verify API credentials from my.telegram.org
- Ensure phone number includes country code (+1...)
- Check if account requires 2FA

**Download fails for specific platform:**
- Update yt-dlp: `pip install -U yt-dlp`
- Check if URL is valid and public
- Some platforms may have geo-restrictions

**Port already in use:**
```bash
python app.py --web --port 8080
```

### Logs

Check logs for detailed error information:
- General downloads: `./logs/downloader.log`
- Telegram operations: `./logs/telegram.log`

## 📝 Examples

### Batch Download Multiple Videos
```bash
# Create a list of URLs
echo "https://youtube.com/watch?v=ID1" > urls.txt
echo "https://youtube.com/watch?v=ID2" >> urls.txt
echo "https://youtube.com/watch?v=ID3" >> urls.txt

# Process each URL
while read url; do
  python app.py -u "$url" -q 1080
done < urls.txt
```

### Download Entire YouTube Channel
```bash
python app.py -u "https://youtube.com/@ChannelName" -l
```

### Extract Audio from Playlist
```bash
python app.py -u "https://youtube.com/playlist?list=ID" -a -l
```

## ⚡ Performance Tips

1. **Use appropriate quality**: Lower quality = faster downloads
2. **Limit playlist downloads**: Use `-l` with care for large playlists
3. **Telegram limits**: Set reasonable `--limit` values (100-500 recommended)
4. **Concurrent downloads**: Run multiple instances for parallel downloads

## 🔒 Security Notes

- Never share your Telegram API credentials
- Downloads are stored locally in `./downloads/`
- Web interface binds to localhost by default
- Use strong passwords for Telegram 2FA

## 📄 License

This project is provided as-is for educational purposes. Please respect copyright and terms of service of all platforms.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional platform support
- UI enhancements
- Performance optimizations
- Bug fixes

---

**Built with ❤️ using yt-dlp, Telethon, and Flask**
