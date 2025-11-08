#!/usr/bin/env python3
"""
KLF Remixes Downloader V6 - Sequential Order Edition
Downloads files in EXACT PAGE ORDER with correct names from the start

APPROACH:
1. Parse page HTML to extract track names in order
2. Find the audio element for each track (in order)
3. Download sequentially with correct naming
4. No guessing, no post-facto renaming needed
"""
import os
import time
import json
import requests
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
DOWNLOAD_DIR = Path.home() / "Desktop" / "klf-remixes-v6"
TRACKS_DIR = DOWNLOAD_DIR / "tracks"
MANIFEST_FILE = DOWNLOAD_DIR / "download_manifest.json"

TRACKS_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name):
    """Clean filename for filesystem"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200] if name else "unnamed"

def load_manifest():
    """Load existing download manifest"""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {'tracks': [], 'downloaded': 0}

def save_manifest(manifest):
    """Save download manifest"""
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)

def parse_page_structure(driver):
    """
    Parse the page to extract tracks in EXACT order
    Returns list of dicts: {'index': 0, 'section': 'section name', 'track': 'track name', 'element': element}
    """
    print("\n🔍 Parsing page structure to extract track order...")

    # JavaScript to parse the page structure
    tracks = driver.execute_script("""
        var tracks = [];
        var currentSection = 'Unknown Section';

        // Strategy 1: Find all play buttons and their associated text
        var playButtons = document.querySelectorAll('[data-hook="playPauseButton"]');

        console.log('Found ' + playButtons.length + ' play buttons');

        for(var i = 0; i < playButtons.length; i++) {
            var button = playButtons[i];
            var trackName = 'Unknown Track ' + (i + 1);
            var sectionName = 'Unknown Section';

            // Try to find the track name by looking at parent elements
            var parent = button;
            var maxLevels = 15; // Look up to 15 levels
            var level = 0;

            while(parent && level < maxLevels) {
                parent = parent.parentElement;
                level++;

                if(!parent) break;

                // Look for section headers (h1, h2, h3, etc.)
                var headers = parent.querySelectorAll('h1, h2, h3, h4, h5, h6, [role="heading"]');
                for(var h = 0; h < headers.length; h++) {
                    var headerText = headers[h].textContent.trim();
                    if(headerText.length > 2 && headerText.length < 100) {
                        sectionName = headerText;
                        break;
                    }
                }

                // Look for track title (common selectors)
                var titleSelectors = [
                    '[data-hook="title"]',
                    '.track-title',
                    '.song-title',
                    'p', 'span', 'div'
                ];

                for(var s = 0; s < titleSelectors.length; s++) {
                    var titles = parent.querySelectorAll(titleSelectors[s]);
                    for(var t = 0; t < titles.length; t++) {
                        var titleText = titles[t].textContent.trim();

                        // Filter out obvious non-track text
                        if(titleText.length > 5 &&
                           titleText.length < 200 &&
                           !titleText.includes('http') &&
                           !titleText.includes('www.') &&
                           !titleText.startsWith('Welcome') &&
                           !titleText.includes('Section') &&
                           titleText.match(/[a-zA-Z]/)) {

                            // This looks like a track name
                            if(trackName.startsWith('Unknown')) {
                                trackName = titleText;
                                break;
                            }
                        }
                    }
                    if(!trackName.startsWith('Unknown')) break;
                }

                if(!trackName.startsWith('Unknown') && !sectionName.startsWith('Unknown')) {
                    break; // Found both
                }
            }

            tracks.push({
                index: i,
                section: sectionName,
                track: trackName,
                hasButton: true
            });
        }

        return tracks;
    """)

    print(f"  ✓ Found {len(tracks)} tracks in page order")

    # Show first 10 for verification
    print(f"\n📋 First 10 tracks found:")
    for i, track in enumerate(tracks[:10]):
        print(f"  [{i+1:03d}] {track['section']} - {track['track']}")

    return tracks

def get_audio_url_for_track(driver, track_index, wait_time=3):
    """
    Click the play button for a specific track and capture its audio URL
    Returns the MP3 URL or None
    """
    try:
        # Find the specific play button by index
        play_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-hook="playPauseButton"]')

        if track_index >= len(play_buttons):
            return None

        button = play_buttons[track_index]

        # Scroll button into view
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
            button
        )
        time.sleep(0.5)

        # Clear network logs before clicking
        driver.get_log('performance')

        # Click the button
        try:
            button.click()
        except:
            driver.execute_script("arguments[0].click();", button)

        # Wait for audio to load
        time.sleep(wait_time)

        # Check network logs for MP3 URL
        logs = driver.get_log('performance')
        mp3_url = None

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

                    if url and ('.mp3' in url.lower() or 'wixstatic.com/mp3' in url):
                        mp3_url = url
                        break
            except:
                pass

        # Also try to get from audio element directly
        if not mp3_url:
            audio_elements = driver.find_elements(By.TAG_NAME, "audio")
            for audio in audio_elements:
                try:
                    src = audio.get_attribute('src')
                    if src and '.mp3' in src.lower():
                        mp3_url = src
                        break
                except:
                    pass

        return mp3_url

    except Exception as e:
        print(f"    ⚠️  Error getting URL: {e}")
        return None

def download_file(url, filepath, max_attempts=3):
    """Download a file with retry logic"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            if filepath.exists() and filepath.stat().st_size > 0:
                return True

        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(2)
            else:
                print(f"    ✗ Download failed: {e}")
                return False

    return False

def main():
    print("="*80)
    print(" KLF REMIXES DOWNLOADER V6 - SEQUENTIAL ORDER EDITION")
    print("="*80)
    print(f"\nOutput directory: {DOWNLOAD_DIR}")
    print("\nThis version downloads files in EXACT PAGE ORDER")
    print("with correct names from the start.\n")

    # Load manifest
    manifest = load_manifest()
    already_downloaded = manifest.get('downloaded', 0)

    if already_downloaded > 0:
        print(f"📂 Found existing download: {already_downloaded} tracks")
        resume = input("Resume from where you left off? (y/n): ").lower().strip()
        if resume != 'y':
            manifest = {'tracks': [], 'downloaded': 0}
            already_downloaded = 0

    # Setup Chrome
    chrome_options = Options()
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    chrome_options.add_argument('--window-size=1920,1080')

    print("\nStarting Chrome...")
    driver = webdriver.Chrome(options=chrome_options)

    url = "https://www.klf-kommunications.com/theremixeskollection"
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(8)

    # Slow scroll to load everything
    print("\n📜 Scrolling to load all content...")
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")

    current_position = 0
    while current_position < total_height:
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(1.5)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > total_height:
            total_height = new_height

        current_position += viewport_height // 2

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    print("  ✓ Page fully loaded")

    # Parse page structure
    tracks = parse_page_structure(driver)

    if not tracks:
        print("\n✗ ERROR: Could not parse track structure!")
        driver.quit()
        return

    print(f"\n✓ Found {len(tracks)} tracks in sequential order")

    # Verify with user
    print("\n" + "="*80)
    print("⚠️  VERIFICATION REQUIRED")
    print("="*80)
    print("\nPlease check the first 10 tracks above.")
    print("Do they look correct? (Check section names and track names)")
    verify = input("\nProceed with download? (y/n): ").lower().strip()

    if verify != 'y':
        print("\n❌ Download cancelled. Please review the track list.")
        driver.quit()
        return

    # Download tracks in order
    print("\n" + "="*80)
    print(f"💾 DOWNLOADING {len(tracks)} TRACKS IN ORDER...")
    print("="*80)

    start_from = already_downloaded
    downloaded_count = start_from
    failed_count = 0

    for idx in range(start_from, len(tracks)):
        track = tracks[idx]
        track_num = idx + 1

        print(f"\n[{track_num:03d}/{len(tracks)}] {track['track']}")

        # Get audio URL for this specific track
        print(f"  🔍 Finding audio URL...")
        mp3_url = get_audio_url_for_track(driver, idx)

        if not mp3_url:
            print(f"  ✗ Could not find audio URL")
            failed_count += 1

            # Save progress
            track['downloaded'] = False
            track['url'] = None
            manifest['tracks'].append(track)
            manifest['downloaded'] = downloaded_count
            save_manifest(manifest)
            continue

        print(f"  ✓ Found: {mp3_url[:60]}...")

        # Create filename
        section_clean = sanitize_filename(track['section'])
        track_clean = sanitize_filename(track['track'])
        filename = f"{track_num:03d}_{track_clean}.mp3"
        filepath = TRACKS_DIR / filename

        # Download
        print(f"  💾 Downloading...")
        if download_file(mp3_url, filepath):
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  ✓ Downloaded ({size_mb:.2f} MB)")

            downloaded_count += 1
            track['downloaded'] = True
            track['url'] = mp3_url
            track['filename'] = filename
        else:
            print(f"  ✗ Download failed")
            failed_count += 1
            track['downloaded'] = False
            track['url'] = mp3_url

        # Save progress every 10 tracks
        manifest['tracks'].append(track)
        manifest['downloaded'] = downloaded_count

        if downloaded_count % 10 == 0:
            save_manifest(manifest)
            print(f"\n  💾 Progress saved: {downloaded_count}/{len(tracks)}")

    # Final save
    save_manifest(manifest)
    driver.quit()

    # Final report
    print("\n" + "="*80)
    print(" DOWNLOAD COMPLETE!")
    print("="*80)
    print(f"\n📊 STATISTICS:")
    print(f"  Total tracks found:     {len(tracks)}")
    print(f"  Successfully downloaded: {downloaded_count}")
    print(f"  Failed:                 {failed_count}")
    print(f"\n📁 OUTPUT:")
    print(f"  Tracks: {TRACKS_DIR}")
    print(f"  Manifest: {MANIFEST_FILE}")

    success_rate = (downloaded_count / len(tracks) * 100) if len(tracks) > 0 else 0
    print(f"\n✓ Success rate: {success_rate:.1f}%")
    print("="*80)

if __name__ == "__main__":
    main()
