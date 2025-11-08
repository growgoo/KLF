# Media Downloader Tools

Two powerful Python scripts for downloading media from web pages with proper naming and organization.

## 🎵 KLF V5 Robust Downloader

**File:** `klf-v5-robust.py`

Enhanced downloader specifically for the KLF Remixes archive that preserves original track names.

### Key Features

- ✅ **Name Preservation**: Extracts track names from page structure (not just ID3 tags)
- ✅ **Retry Logic**: Automatically retries failed downloads and clicks
- ✅ **Progress Tracking**: Saves manifest to resume interrupted downloads
- ✅ **URL Mapping**: Maps downloaded files to original track names
- ✅ **Multiple Capture Methods**: Network logs + audio elements + JS queries
- ✅ **Section Organization**: Organizes files by sections from the page
- ✅ **Detailed Reporting**: Shows what was found vs what was downloaded

### Improvements Over V4

| Feature | V4 | V5 |
|---------|----|----|
| Files captured | 333/685 (48.6%) | Improved discovery |
| Name preservation | ID3 only | Page structure + ID3 |
| Retry logic | None | Yes (3 attempts) |
| Resume capability | No | Yes (manifest-based) |
| Click retry | No | Yes (multiple passes) |
| URL-to-name mapping | No | Yes |
| Progress tracking | Basic | Detailed manifest |

### Usage

```bash
python3 klf-v5-robust.py
```

The script will:
1. Parse page structure to extract track names
2. Scroll slowly to load all content
3. Click all play buttons (with retry)
4. Capture MP3 URLs using multiple methods
5. Download files with retry logic
6. Organize by section with proper names
7. Save detailed manifest for resume

### Output Structure

```
~/Desktop/klf-remixes-v5/
├── _raw_downloads/          # Original downloads with hash IDs
│   ├── 001_Track_Name_abc123.mp3
│   └── ...
├── _named_tracks/           # Organized by section
│   ├── The_Queen_and_I/
│   │   ├── 001_The_Queen_and_I_Do_Not_Attempt.mp3
│   │   └── ...
│   └── Whitney_joins_the_jams/
│       └── ...
└── download_manifest.json   # Progress tracking
```

### Resume from Interruption

If the download is interrupted, simply run the script again:

```bash
python3 klf-v5-robust.py
```

It will ask: `Resume from previous run? (y/n):`
- Choose `y` to skip already downloaded files
- Choose `n` to start fresh

### Manifest File

The `download_manifest.json` tracks:
- All discovered URLs
- Track names and sections
- Successfully downloaded files
- Failed downloads
- Can be edited manually to retry specific files

---

## 🌐 Universal Media Downloader

**File:** `universal-media-downloader.py`

Generic tool for downloading any media (audio, video, images) from any webpage.

### Key Features

- ✅ **Multi-format Support**: Audio (MP3, WAV, FLAC, etc.), Video (MP4, WebM, etc.), Images (JPG, PNG, etc.)
- ✅ **Intelligent Extraction**: Multiple detection methods (network logs, elements, links)
- ✅ **Smart Naming**: Extracts context and names from page structure
- ✅ **Lazy Loading Support**: Optional scrolling to load dynamic content
- ✅ **Player Support**: Can click play buttons to reveal hidden audio sources
- ✅ **File Filtering**: Min/max size filtering
- ✅ **Resume Capability**: Manifest-based progress tracking
- ✅ **Auto-Organization**: Organizes by media type (audio/video/image)

### Usage

#### Basic Usage

```bash
# Download all media from a page
python3 universal-media-downloader.py https://example.com/media
```

#### Download Specific Types

```bash
# Audio only
python3 universal-media-downloader.py https://example.com/music --types audio

# Images and videos
python3 universal-media-downloader.py https://example.com/gallery --types image,video

# Specific formats
python3 universal-media-downloader.py https://example.com --types mp3,mp4,jpg
```

#### Advanced Options

```bash
# Music player page (scroll + click play buttons)
python3 universal-media-downloader.py https://example.com/player \
  --types audio \
  --scroll \
  --click-players

# Download with size filtering
python3 universal-media-downloader.py https://example.com/media \
  --max-size 100 \
  --min-size 100 \
  --types audio

# Custom output directory
python3 universal-media-downloader.py https://example.com/gallery \
  --output ~/Downloads/my_media \
  --types image
```

### Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `url` | Target webpage URL | `https://example.com` |
| `--types` | Media types to download | `audio,video` or `mp3,jpg` |
| `--output` | Output directory | `~/Downloads/media` |
| `--scroll` | Enable page scrolling | (flag, no value) |
| `--click-players` | Click play buttons | (flag, no value) |
| `--max-size` | Max file size in MB | `100` |
| `--min-size` | Min file size in KB | `50` |

### Supported Media Types

**Audio:** `.mp3`, `.wav`, `.flac`, `.m4a`, `.aac`, `.ogg`, `.wma`

**Video:** `.mp4`, `.webm`, `.mov`, `.avi`, `.mkv`, `.flv`, `.wmv`

**Image:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.ico`

### Output Structure

```
./downloads/
├── _raw_downloads/          # Original downloads
│   ├── 0001_track_name.mp3
│   ├── 0002_video_name.mp4
│   └── ...
├── _organized/              # Organized by type
│   ├── audio/
│   │   ├── 0001_track_name.mp3
│   │   └── ...
│   ├── video/
│   │   └── ...
│   └── image/
│       └── ...
└── manifest.json            # Progress tracking
```

### Example Use Cases

#### 1. KLF Archive (or similar music collections)
```bash
python3 universal-media-downloader.py \
  https://www.klf-kommunications.com/theremixeskollection \
  --types audio \
  --scroll \
  --click-players \
  --output ~/Desktop/klf-universal
```

#### 2. Image Gallery
```bash
python3 universal-media-downloader.py \
  https://example.com/gallery \
  --types image \
  --scroll \
  --min-size 50
```

#### 3. Video Archive
```bash
python3 universal-media-downloader.py \
  https://example.com/videos \
  --types video \
  --max-size 500 \
  --scroll
```

#### 4. Mixed Media Collection
```bash
python3 universal-media-downloader.py \
  https://example.com/archive \
  --types audio,video,image \
  --scroll \
  --click-players
```

---

## 🔧 Requirements

Install required packages:

```bash
pip install selenium requests mutagen
```

Also need Chrome and ChromeDriver:
- Chrome browser installed
- ChromeDriver matching your Chrome version

---

## 📊 Troubleshooting

### Not Finding All Files?

1. **Enable scrolling**: Many sites use lazy loading
   ```bash
   --scroll
   ```

2. **Click play buttons**: Some audio is only loaded when clicked
   ```bash
   --click-players
   ```

3. **Check manifest**: Look at `manifest.json` to see what was found vs downloaded

4. **Run multiple times**: Network issues may prevent some downloads

### Files Have Wrong Names?

- **KLF V5**: Uses page structure to extract names. If names are wrong, the page structure may have changed.
- **Universal**: Uses filename from URL. For better names, check if the site has metadata you can parse.

### Downloads Are Too Slow?

- Consider reducing the number of retries (edit `RETRY_ATTEMPTS` in the code)
- Run in headless mode (uncomment the headless option in code)

### Out of Memory?

- Use `--max-size` to limit file sizes
- Download in batches (interrupt and resume)

---

## 🎯 Comparison: Which Tool to Use?

### Use KLF V5 Robust when:
- Downloading from KLF archive specifically
- You need the exact track names and sections
- You want maximum compatibility with that specific site

### Use Universal Downloader when:
- Downloading from any other website
- You need flexibility in media types
- You want a general-purpose tool
- You need size filtering

---

## 📝 Tips

1. **Always test first**: Run on a small section to verify it works
2. **Monitor progress**: Watch the output to catch issues early
3. **Check manifests**: Review the JSON files to see what was found
4. **Resume interrupted**: Both tools support resuming from manifest
5. **Verify downloads**: Check file sizes and playability after download

---

## 🚀 Future Enhancements

Potential improvements:
- [ ] Parallel downloads for speed
- [ ] Better name extraction using NLP
- [ ] Support for authentication (login required sites)
- [ ] Duplicate detection (same file, different URLs)
- [ ] Metadata preservation (ID3 tags, EXIF, etc.)
- [ ] Progress bars with rich/tqdm
- [ ] Web UI for easier use

---

## 📄 License

Free to use and modify for personal use.
