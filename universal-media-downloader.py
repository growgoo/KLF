#!/usr/bin/env python3
"""
Universal Media Downloader
Download all media (audio, video, images) from any webpage with proper naming

FEATURES:
- Supports multiple media types (MP3, MP4, WAV, FLAC, JPG, PNG, GIF, etc.)
- Extracts and preserves context/names from page structure
- Retry logic and resume capability
- Progress tracking and detailed manifest
- Works on any webpage with linked media

USAGE:
  python3 universal-media-downloader.py <url> [options]

  Options:
    --types TYPE1,TYPE2   Media types to download (default: all)
                         Examples: mp3,mp4 or jpg,png or audio,video,image
    --output DIR          Output directory (default: ./downloads)
    --scroll              Enable scrolling to load lazy content
    --click-players       Click play buttons to reveal audio sources
    --max-size SIZE       Maximum file size in MB (default: unlimited)
    --min-size SIZE       Minimum file size in KB (default: 1)
"""

import os
import sys
import time
import json
import requests
import re
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException

# Media type definitions
MEDIA_TYPES = {
    'audio': ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'],
    'video': ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv'],
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico']
}

class UniversalMediaDownloader:
    def __init__(self, url, output_dir, media_types=None, scroll=False, click_players=False,
                 max_size=None, min_size=1):
        self.url = url
        self.output_dir = Path(output_dir)
        self.temp_dir = self.output_dir / "_raw_downloads"
        self.final_dir = self.output_dir / "_organized"
        self.manifest_file = self.output_dir / "manifest.json"

        # Media types to download
        if media_types:
            self.extensions = []
            for mtype in media_types:
                if mtype in MEDIA_TYPES:
                    self.extensions.extend(MEDIA_TYPES[mtype])
                elif mtype.startswith('.'):
                    self.extensions.append(mtype.lower())
                else:
                    self.extensions.append(f'.{mtype.lower()}')
        else:
            # All types
            self.extensions = []
            for exts in MEDIA_TYPES.values():
                self.extensions.extend(exts)

        self.scroll = scroll
        self.click_players = click_players
        self.max_size = max_size * 1024 * 1024 if max_size else None
        self.min_size = min_size * 1024 if min_size else 1024

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)

        self.manifest = self.load_manifest()
        self.driver = None

    def sanitize_filename(self, name):
        """Clean filename for filesystem"""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name[:200] if name else "unnamed"

    def load_manifest(self):
        """Load existing download manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {
            'url': self.url,
            'media': {},  # url -> media info
            'downloaded': [],
            'failed': []
        }

    def save_manifest(self):
        """Save download manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def setup_browser(self):
        """Initialize Selenium browser"""
        chrome_options = Options()
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        chrome_options.add_argument('--window-size=1920,1080')
        # Uncomment for headless mode
        # chrome_options.add_argument('--headless')

        self.driver = webdriver.Chrome(options=chrome_options)
        print(f"🌐 Loading: {self.url}")
        self.driver.get(self.url)
        time.sleep(5)

    def scroll_page(self):
        """Scroll through page to load lazy content"""
        if not self.scroll:
            return

        print("\n📜 Scrolling page to load lazy content...")
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        scroll_increment = viewport_height // 2

        current_position = 0
        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(1)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > total_height:
                total_height = new_height

            current_position += scroll_increment

        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        print(f"  ✓ Scrolling complete")

    def click_all_players(self):
        """Click all play/audio buttons to reveal sources"""
        if not self.click_players:
            return

        print("\n▶️  Clicking play buttons to reveal media...")

        # Common play button selectors
        selectors = [
            '[data-hook="playPauseButton"]',
            'button[aria-label*="play" i]',
            'button[aria-label*="Play" i]',
            '.play-button',
            '.player-button',
            'button.play',
            '[role="button"][aria-label*="play" i]'
        ]

        all_buttons = []
        for selector in selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                all_buttons.extend(buttons)
            except:
                pass

        # Remove duplicates
        all_buttons = list(set(all_buttons))

        print(f"  Found {len(all_buttons)} play buttons")

        for idx, button in enumerate(all_buttons, 1):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    button
                )
                time.sleep(0.5)

                try:
                    button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", button)

                if idx % 10 == 0:
                    print(f"  Clicked {idx}/{len(all_buttons)} buttons...")

                time.sleep(0.5)
            except:
                pass

        time.sleep(5)
        print(f"  ✓ Clicked {len(all_buttons)} buttons")

    def extract_media_urls(self):
        """Extract all media URLs from page"""
        print("\n🔍 Extracting media URLs...")
        media_found = {}

        # Method 1: Network logs
        print("  Method 1: Network performance logs...")
        try:
            logs = self.driver.get_log('performance')
            for log in logs:
                try:
                    log_data = json.loads(log['message'])
                    message = log_data.get('message', {})

                    if 'params' in message:
                        params = message['params']
                        url = None

                        if 'request' in params:
                            url = params['request'].get('url', '')
                        elif 'response' in params:
                            url = params['response'].get('url', '')

                        if url and any(ext in url.lower() for ext in self.extensions):
                            if url not in media_found:
                                media_found[url] = {
                                    'url': url,
                                    'type': self.get_media_type(url),
                                    'name': None,
                                    'context': None
                                }
                except:
                    pass
        except:
            print("    ⚠ Could not read performance logs")

        print(f"    Found {len(media_found)} URLs from logs")

        # Method 2: Media elements (audio, video, img)
        print("  Method 2: Querying media elements...")
        media_elements = self.driver.execute_script("""
            var media = [];

            // Audio elements
            var audios = document.getElementsByTagName('audio');
            for(var i = 0; i < audios.length; i++) {
                if(audios[i].src) media.push({url: audios[i].src, type: 'audio', element: 'audio'});
                var sources = audios[i].getElementsByTagName('source');
                for(var j = 0; j < sources.length; j++) {
                    if(sources[j].src) media.push({url: sources[j].src, type: 'audio', element: 'source'});
                }
            }

            // Video elements
            var videos = document.getElementsByTagName('video');
            for(var i = 0; i < videos.length; i++) {
                if(videos[i].src) media.push({url: videos[i].src, type: 'video', element: 'video'});
                var sources = videos[i].getElementsByTagName('source');
                for(var j = 0; j < sources.length; j++) {
                    if(sources[j].src) media.push({url: sources[j].src, type: 'video', element: 'source'});
                }
            }

            // Image elements
            var imgs = document.getElementsByTagName('img');
            for(var i = 0; i < imgs.length; i++) {
                if(imgs[i].src) media.push({url: imgs[i].src, type: 'image', element: 'img'});
            }

            return media;
        """)

        for item in media_elements:
            url = item['url']
            if any(ext in url.lower() for ext in self.extensions):
                if url not in media_found:
                    media_found[url] = {
                        'url': url,
                        'type': item['type'],
                        'name': None,
                        'context': None
                    }

        print(f"    Total: {len(media_found)} media elements")

        # Method 3: Parse all links
        print("  Method 3: Scanning all links...")
        all_links = self.driver.execute_script("""
            var links = [];
            var anchors = document.getElementsByTagName('a');
            for(var i = 0; i < anchors.length; i++) {
                if(anchors[i].href) links.push(anchors[i].href);
            }
            return links;
        """)

        for url in all_links:
            if any(ext in url.lower() for ext in self.extensions):
                if url not in media_found:
                    media_found[url] = {
                        'url': url,
                        'type': self.get_media_type(url),
                        'name': None,
                        'context': None
                    }

        print(f"    Total: {len(media_found)} URLs found")

        # Method 4: Try to extract context/names
        print("  Method 4: Extracting context and names...")
        for url, data in media_found.items():
            # Try to extract name from URL
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)

            if filename:
                # Clean up the filename
                name = os.path.splitext(filename)[0]
                name = re.sub(r'[_-]+', ' ', name)
                data['name'] = name

            # Try to find context on page
            # This is a heuristic - look for text near media elements
            # For simplicity, we'll just use the filename for now

        print(f"\n  ✓ Total media URLs discovered: {len(media_found)}")
        return media_found

    def get_media_type(self, url):
        """Determine media type from URL"""
        url_lower = url.lower()
        for type_name, extensions in MEDIA_TYPES.items():
            if any(ext in url_lower for ext in extensions):
                return type_name
        return 'unknown'

    def download_file(self, url, filepath, max_attempts=3):
        """Download a file with retry logic"""
        for attempt in range(max_attempts):
            try:
                # Handle relative URLs
                absolute_url = urljoin(self.url, url)

                response = requests.get(absolute_url, stream=True, timeout=30)
                response.raise_for_status()

                # Check content length
                content_length = int(response.headers.get('content-length', 0))
                if self.max_size and content_length > self.max_size:
                    print(f"    ⊘ Skipped (too large: {content_length/(1024*1024):.1f} MB)")
                    return False

                if content_length < self.min_size:
                    print(f"    ⊘ Skipped (too small: {content_length/1024:.1f} KB)")
                    return False

                # Download
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)

                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    return True

            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(2)
                else:
                    print(f"    ✗ Error: {e}")
                    return False

        return False

    def download_all(self, media_found):
        """Download all discovered media"""
        print("\n💾 Downloading media files...")

        downloaded = 0
        skipped = 0
        failed = 0

        for idx, (url, data) in enumerate(media_found.items(), 1):
            # Skip if already downloaded
            if url in self.manifest['downloaded']:
                print(f"[{idx}/{len(media_found)}] ⊙ Already downloaded")
                skipped += 1
                continue

            # Create filename
            name = data.get('name', f'media_{idx:04d}')
            name_clean = self.sanitize_filename(name)

            # Get extension from URL
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1]
            if not ext:
                # Try to determine from type
                if data['type'] == 'audio':
                    ext = '.mp3'
                elif data['type'] == 'video':
                    ext = '.mp4'
                elif data['type'] == 'image':
                    ext = '.jpg'
                else:
                    ext = '.dat'

            filename = f"{idx:04d}_{name_clean}{ext}"
            filepath = self.temp_dir / filename

            print(f"[{idx}/{len(media_found)}] {name_clean}{ext}")

            if self.download_file(url, filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"  ✓ Downloaded ({size_mb:.2f} MB)")

                self.manifest['downloaded'].append(url)
                self.manifest['media'][url] = data
                downloaded += 1

                # Save manifest every 10 downloads
                if downloaded % 10 == 0:
                    self.save_manifest()
            else:
                failed += 1
                self.manifest['failed'].append(url)

        self.save_manifest()

        print(f"\n  ✓ Downloaded: {downloaded}")
        print(f"  ⊙ Skipped: {skipped}")
        print(f"  ✗ Failed: {failed}")

        return downloaded

    def organize_files(self):
        """Organize downloaded files by type"""
        print("\n📁 Organizing files by type...")

        for media_type in ['audio', 'video', 'image', 'other']:
            type_dir = self.final_dir / media_type
            type_dir.mkdir(exist_ok=True)

        organized = 0

        for url, data in self.manifest['media'].items():
            if url in self.manifest['downloaded']:
                # Find file in temp dir
                name = data.get('name', 'media')
                name_clean = self.sanitize_filename(name)

                # Find matching file
                matches = list(self.temp_dir.glob(f"*{name_clean}*"))
                if matches:
                    temp_file = matches[0]

                    # Determine type directory
                    media_type = data.get('type', 'other')
                    if media_type not in ['audio', 'video', 'image']:
                        media_type = 'other'

                    type_dir = self.final_dir / media_type

                    # Copy to organized location
                    final_file = type_dir / temp_file.name
                    import shutil
                    shutil.copy2(temp_file, final_file)
                    organized += 1

        print(f"  ✓ Organized {organized} files")

    def run(self):
        """Main execution flow"""
        print("="*80)
        print(" UNIVERSAL MEDIA DOWNLOADER")
        print("="*80)
        print(f"\nTarget URL:      {self.url}")
        print(f"Output directory: {self.output_dir}")
        print(f"Media types:     {', '.join(self.extensions)}")
        print(f"Scroll page:     {self.scroll}")
        print(f"Click players:   {self.click_players}")

        try:
            # Setup browser
            self.setup_browser()

            # Scroll if requested
            self.scroll_page()

            # Click players if requested
            self.click_all_players()

            # Extract media URLs
            media_found = self.extract_media_urls()

            # Close browser
            if self.driver:
                self.driver.quit()

            if not media_found:
                print("\n⚠ No media found on this page!")
                return

            # Download all media
            downloaded = self.download_all(media_found)

            # Organize files
            if downloaded > 0:
                self.organize_files()

            # Final report
            print("\n" + "="*80)
            print(" DOWNLOAD COMPLETE!")
            print("="*80)
            print(f"\n📊 STATISTICS:")
            print(f"  Media discovered:  {len(media_found)}")
            print(f"  Successfully saved: {downloaded}")
            print(f"  Failed:            {len(self.manifest['failed'])}")
            print(f"\n📁 OUTPUT:")
            print(f"  Raw downloads:     {self.temp_dir}")
            print(f"  Organized:         {self.final_dir}")
            print(f"  Manifest:          {self.manifest_file}")
            print("="*80)

        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")
            if self.driver:
                self.driver.quit()
            self.save_manifest()
        except Exception as e:
            print(f"\n\n✗ Error: {e}")
            if self.driver:
                self.driver.quit()
            self.save_manifest()
            raise


def main():
    parser = argparse.ArgumentParser(
        description='Universal Media Downloader - Download media from any webpage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all media types
  python3 universal-media-downloader.py https://example.com/media

  # Download only audio files
  python3 universal-media-downloader.py https://example.com/music --types audio

  # Download images and videos with scrolling
  python3 universal-media-downloader.py https://example.com/gallery --types image,video --scroll

  # Download from music player page (click play buttons)
  python3 universal-media-downloader.py https://example.com/player --types audio --click-players --scroll
        """
    )

    parser.add_argument('url', help='URL to download media from')
    parser.add_argument('--types', help='Media types to download (comma-separated): audio,video,image or mp3,mp4,jpg')
    parser.add_argument('--output', default='./downloads', help='Output directory (default: ./downloads)')
    parser.add_argument('--scroll', action='store_true', help='Scroll page to load lazy content')
    parser.add_argument('--click-players', action='store_true', help='Click play buttons to reveal media')
    parser.add_argument('--max-size', type=float, help='Maximum file size in MB')
    parser.add_argument('--min-size', type=float, default=1, help='Minimum file size in KB (default: 1)')

    args = parser.parse_args()

    # Parse media types
    media_types = None
    if args.types:
        media_types = [t.strip() for t in args.types.split(',')]

    # Create downloader and run
    downloader = UniversalMediaDownloader(
        url=args.url,
        output_dir=args.output,
        media_types=media_types,
        scroll=args.scroll,
        click_players=args.click_players,
        max_size=args.max_size,
        min_size=args.min_size
    )

    downloader.run()


if __name__ == '__main__':
    main()
