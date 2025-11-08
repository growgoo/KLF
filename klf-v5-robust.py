#!/usr/bin/env python3
"""
KLF Remixes Downloader V5 - Robust Edition with Name Preservation
IMPROVEMENTS:
- Parses page structure to extract track names
- Maps URLs to original track names (not just ID3 metadata)
- Retry logic for failed clicks and downloads
- Progress tracking and resume capability
- Multiple capture passes
- Detailed manifest of found vs downloaded
"""
import os
import time
import json
import requests
import re
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# Configuration
DOWNLOAD_DIR = os.path.expanduser("~/Desktop/klf-remixes-v5")
TEMP_DIR = os.path.join(DOWNLOAD_DIR, "_raw_downloads")
FINAL_DIR = os.path.join(DOWNLOAD_DIR, "_named_tracks")
MANIFEST_FILE = os.path.join(DOWNLOAD_DIR, "download_manifest.json")
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

def sanitize_filename(name):
    """Clean filename for filesystem"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]

def load_manifest():
    """Load existing download manifest"""
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {
        'tracks': {},  # url -> track info
        'downloaded': [],  # list of successfully downloaded URLs
        'failed': []  # list of failed URLs
    }

def save_manifest(manifest):
    """Save download manifest"""
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"  💾 Manifest saved: {len(manifest['tracks'])} tracks tracked")

print("="*80)
print(" KLF REMIXES ROBUST DOWNLOADER V5 - WITH NAME PRESERVATION")
print("="*80)
print(f"\nDownload directory: {DOWNLOAD_DIR}")
print(f"Expected tracks: ~685")
print("\nThis version will:")
print("  ✓ Parse page structure to get track names")
print("  ✓ Map URLs to original track names")
print("  ✓ Retry failed operations")
print("  ✓ Resume from previous runs")
print("  ✓ Save detailed manifest\n")

# Load manifest
manifest = load_manifest()
if manifest['downloaded']:
    print(f"📂 Found existing manifest: {len(manifest['downloaded'])} already downloaded")
    resume = input("Resume from previous run? (y/n): ").lower().strip()
    if resume != 'y':
        print("Starting fresh...")
        manifest = {'tracks': {}, 'downloaded': [], 'failed': []}

# Setup Chrome
chrome_options = Options()
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
chrome_options.add_argument('--window-size=1920,1080')
# Run in headless mode for speed (remove this line if you want to see the browser)
# chrome_options.add_argument('--headless')

print("\nStarting Chrome...")
driver = webdriver.Chrome(options=chrome_options)

url = "https://www.klf-kommunications.com/theremixeskollection"
print(f"Loading {url}...")
driver.get(url)
time.sleep(8)

# ============================================================================
# STEP 1: PARSE PAGE STRUCTURE TO GET TRACK NAMES
# ============================================================================
print("\n" + "="*80)
print("STEP 1: Parsing page structure to extract track names...")
print("="*80)

# Strategy: Find all track containers with their names and associated media
# The page likely has a structure like sections > tracks > play buttons
# We need to map each play button to its track name

# Try multiple selectors to find track information
track_elements = []

print("  Searching for track containers...")

# Method 1: Find by common music player patterns
try:
    # Look for elements that might contain track titles
    potential_tracks = driver.execute_script("""
        var tracks = [];

        // Find all elements with play buttons
        var buttons = document.querySelectorAll('[data-hook="playPauseButton"]');

        for(var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            var trackInfo = {
                index: i,
                button: btn,
                name: 'Unknown Track ' + (i + 1),
                section: 'Unknown Section'
            };

            // Try to find track name by traversing up the DOM
            var parent = btn;
            var attempts = 0;
            while(parent && attempts < 10) {
                parent = parent.parentElement;
                attempts++;

                // Look for text content that might be the track name
                if(parent) {
                    // Check for specific data attributes
                    var titleEl = parent.querySelector('[data-hook="title"]');
                    if(titleEl && titleEl.textContent.trim()) {
                        trackInfo.name = titleEl.textContent.trim();
                    }

                    // Check for section headers
                    var sectionEl = parent.querySelector('h2, h3, [role="heading"]');
                    if(sectionEl && sectionEl.textContent.trim()) {
                        trackInfo.section = sectionEl.textContent.trim();
                    }

                    // Look for any text near the button that looks like a title
                    var textEls = parent.querySelectorAll('p, span, div');
                    for(var j = 0; j < textEls.length; j++) {
                        var text = textEls[j].textContent.trim();
                        if(text.length > 5 && text.length < 150 &&
                           !text.includes('http') &&
                           text.match(/[a-zA-Z]/)) {
                            // Looks like a potential track name
                            if(trackInfo.name.startsWith('Unknown')) {
                                trackInfo.name = text;
                                break;
                            }
                        }
                    }
                }
            }

            tracks.push({
                index: i,
                name: trackInfo.name,
                section: trackInfo.section
            });
        }

        return tracks;
    """)

    print(f"  Found {len(potential_tracks)} tracks with structure analysis")

    for track in potential_tracks:
        print(f"    Track {track['index']+1}: {track['section']} - {track['name']}")

    track_elements = potential_tracks

except Exception as e:
    print(f"  ⚠ Error parsing track structure: {e}")

# ============================================================================
# STEP 2: SLOW SCROLL TO LOAD EVERYTHING
# ============================================================================
print("\n" + "="*80)
print("STEP 2: Slow scrolling to load all content...")
print("="*80)

total_height = driver.execute_script("return document.body.scrollHeight")
viewport_height = driver.execute_script("return window.innerHeight")
scroll_increment = viewport_height // 2

current_position = 0
scroll_count = 0

while current_position < total_height:
    driver.execute_script(f"window.scrollTo(0, {current_position});")
    scroll_count += 1

    if scroll_count % 5 == 0:
        print(f"  Scroll {scroll_count}: {current_position}/{total_height}px")

    time.sleep(2)

    new_total_height = driver.execute_script("return document.body.scrollHeight")
    if new_total_height > total_height:
        total_height = new_total_height

    current_position += scroll_increment

driver.execute_script("window.scrollTo(0, 0);")
time.sleep(2)
print(f"  ✓ Scrolling complete ({total_height}px)")

# ============================================================================
# STEP 3: FIND ALL PLAY BUTTONS
# ============================================================================
print("\n" + "="*80)
print("STEP 3: Finding all play buttons...")
print("="*80)

play_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-hook="playPauseButton"]')
total_buttons = len(play_buttons)
print(f"  Found {total_buttons} play buttons")

if total_buttons == 0:
    print("\n✗ ERROR: No play buttons found!")
    driver.quit()
    exit(1)

# ============================================================================
# STEP 4: CLICK ALL BUTTONS WITH RETRY (Multiple passes)
# ============================================================================
print("\n" + "="*80)
print(f"STEP 4: Clicking all {total_buttons} buttons with retry logic...")
print("="*80)

def click_button_with_retry(button, index, max_attempts=3):
    """Try to click a button with retries"""
    for attempt in range(max_attempts):
        try:
            # Scroll into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                button
            )
            time.sleep(0.5)

            # Try regular click
            try:
                button.click()
                return True
            except ElementClickInterceptedException:
                # Try JavaScript click
                driver.execute_script("arguments[0].click();", button)
                return True

        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"    Retry {attempt + 1}/{max_attempts} for button {index}")
                time.sleep(1)
            else:
                print(f"    Failed after {max_attempts} attempts: {e}")
                return False
    return False

clicked_count = 0
failed_clicks = []

for idx, button in enumerate(play_buttons, 1):
    if click_button_with_retry(button, idx):
        clicked_count += 1
        if idx % 20 == 0:
            print(f"  [{idx}/{total_buttons}] Clicked {clicked_count} buttons...")
        time.sleep(1)
    else:
        failed_clicks.append(idx)

print(f"\n  Clicked: {clicked_count}/{total_buttons}")
print(f"  Failed: {len(failed_clicks)}")

# If we have failures, try one more pass
if failed_clicks and len(failed_clicks) < 20:
    print("\n  Retrying failed buttons...")
    retry_success = 0
    for idx in failed_clicks[:]:
        if idx <= len(play_buttons):
            if click_button_with_retry(play_buttons[idx-1], idx):
                retry_success += 1
                failed_clicks.remove(idx)
    print(f"  Recovered {retry_success} buttons on retry")

print("\n  Waiting for all audio to load...")
time.sleep(10)

# ============================================================================
# STEP 5: CAPTURE ALL MP3 URLS (Multiple methods + passes)
# ============================================================================
print("\n" + "="*80)
print("STEP 5: Capturing MP3 URLs with multiple methods...")
print("="*80)

mp3_data = {}  # url -> track info

# Method 1: Network logs
print("  Method 1: Network performance logs...")
logs = driver.get_log('performance')
for log in logs:
    try:
        log_data = json.loads(log['message'])
        message = log_data.get('message', {})
        if 'params' in message:
            params = message['params']
            url_found = None

            if 'request' in params:
                req_url = params['request'].get('url', '')
                if 'wixstatic.com/mp3' in req_url or req_url.endswith('.mp3'):
                    url_found = req_url

            if 'response' in params:
                resp_url = params['response'].get('url', '')
                if 'wixstatic.com/mp3' in resp_url or resp_url.endswith('.mp3'):
                    url_found = resp_url

            if url_found and url_found not in mp3_data:
                mp3_data[url_found] = {
                    'url': url_found,
                    'name': None,
                    'section': None,
                    'index': len(mp3_data)
                }
    except:
        pass

print(f"    Found {len(mp3_data)} URLs from network logs")

# Method 2: Audio elements
print("  Method 2: Querying audio elements...")
audio_sources = driver.execute_script("""
    var sources = [];
    var audios = document.getElementsByTagName('audio');
    for(var i = 0; i < audios.length; i++) {
        if(audios[i].src) {
            sources.push({
                url: audios[i].src,
                index: i
            });
        }
        // Also check source children
        var sourceEls = audios[i].getElementsByTagName('source');
        for(var j = 0; j < sourceEls.length; j++) {
            if(sourceEls[j].src) {
                sources.push({
                    url: sourceEls[j].src,
                    index: i
                });
            }
        }
    }
    return sources;
""")

for item in audio_sources:
    url = item['url']
    if ('.mp3' in url or 'wixstatic.com/mp3' in url) and url not in mp3_data:
        mp3_data[url] = {
            'url': url,
            'name': None,
            'section': None,
            'index': len(mp3_data)
        }

print(f"    Total unique URLs: {len(mp3_data)}")

# Method 3: Try to map URLs to track names
print("  Method 3: Mapping URLs to track names...")
if track_elements:
    # Re-scan to map audio elements to track names
    for i, track_info in enumerate(track_elements):
        # Try to find the audio element associated with this track
        # This is best-effort - the mapping may not be perfect
        if i < len(list(mp3_data.values())):
            url_list = list(mp3_data.keys())
            if i < len(url_list):
                url = url_list[i]
                mp3_data[url]['name'] = track_info.get('name', f'Track {i+1}')
                mp3_data[url]['section'] = track_info.get('section', 'Unknown Section')
                mp3_data[url]['index'] = i

# For any URLs without names, assign default names
for i, (url, data) in enumerate(mp3_data.items()):
    if not data['name']:
        data['name'] = f"Track_{i+1:03d}"
    if not data['section']:
        data['section'] = "Unknown_Section"

driver.quit()

print(f"\n  ✓ Total MP3 URLs captured: {len(mp3_data)}")

if not mp3_data:
    print("\n✗ ERROR: No MP3 URLs captured!")
    exit(1)

# Update manifest
for url, data in mp3_data.items():
    manifest['tracks'][url] = data

save_manifest(manifest)

# ============================================================================
# STEP 6: DOWNLOAD ALL FILES WITH RETRY
# ============================================================================
print("\n" + "="*80)
print(f"STEP 6: Downloading {len(mp3_data)} files with retry logic...")
print("="*80)

def download_file_with_retry(url, filepath, max_attempts=RETRY_ATTEMPTS):
    """Download a file with retry logic"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            # Verify file was downloaded
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return True

        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"    Retry {attempt + 1}/{max_attempts}...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"    Failed after {max_attempts} attempts: {e}")
                return False

    return False

downloaded_count = 0
failed_downloads = []

for idx, (url, data) in enumerate(mp3_data.items(), 1):
    # Skip if already downloaded
    if url in manifest['downloaded']:
        print(f"[{idx}/{len(mp3_data)}] ⊙ Already downloaded: {data['name']}")
        downloaded_count += 1
        continue

    # Create filename from track info
    section_clean = sanitize_filename(data['section'])
    name_clean = sanitize_filename(data['name'])

    # Use hash from URL as unique identifier
    url_hash = url.split('/')[-1].split('?')[0].split('.')[0][-8:]
    filename = f"{data['index']:03d}_{name_clean}_{url_hash}.mp3"

    filepath = os.path.join(TEMP_DIR, filename)

    print(f"[{idx}/{len(mp3_data)}] {data['name']}")

    if download_file_with_retry(url, filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  ✓ Downloaded ({size_mb:.2f} MB)")

        manifest['downloaded'].append(url)
        downloaded_count += 1

        # Save manifest every 10 downloads
        if downloaded_count % 10 == 0:
            save_manifest(manifest)
    else:
        failed_downloads.append(url)
        manifest['failed'].append(url)

# Final manifest save
save_manifest(manifest)

print(f"\n  ✓ Successfully downloaded: {downloaded_count}/{len(mp3_data)}")
print(f"  ✗ Failed downloads: {len(failed_downloads)}")

# ============================================================================
# STEP 7: ORGANIZE BY SECTION
# ============================================================================
print("\n" + "="*80)
print("STEP 7: Organizing files by section...")
print("="*80)

organized_count = 0

for url, data in mp3_data.items():
    if url in manifest['downloaded']:
        section_clean = sanitize_filename(data['section'])
        name_clean = sanitize_filename(data['name'])
        url_hash = url.split('/')[-1].split('?')[0].split('.')[0][-8:]

        temp_filename = f"{data['index']:03d}_{name_clean}_{url_hash}.mp3"
        temp_path = os.path.join(TEMP_DIR, temp_filename)

        if os.path.exists(temp_path):
            # Create section directory
            section_dir = os.path.join(FINAL_DIR, section_clean)
            os.makedirs(section_dir, exist_ok=True)

            # Final filename
            final_filename = f"{data['index']:03d}_{name_clean}.mp3"
            final_path = os.path.join(section_dir, final_filename)

            shutil.copy2(temp_path, final_path)
            organized_count += 1

print(f"  ✓ Organized {organized_count} files into sections")

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "="*80)
print(" DOWNLOAD COMPLETE!")
print("="*80)

print(f"\n📊 STATISTICS:")
print(f"  Buttons found:        {total_buttons}")
print(f"  Buttons clicked:      {clicked_count}")
print(f"  MP3 URLs discovered:  {len(mp3_data)}")
print(f"  Files downloaded:     {downloaded_count}")
print(f"  Files organized:      {organized_count}")
print(f"  Failed downloads:     {len(failed_downloads)}")

print(f"\n📁 DIRECTORIES:")
print(f"  Raw downloads:        {TEMP_DIR}")
print(f"  Organized by section: {FINAL_DIR}")
print(f"  Manifest:             {MANIFEST_FILE}")

expected = 685
actual = len(mp3_data)
success_rate = (downloaded_count / expected * 100) if expected > 0 else 0

print(f"\n📈 COVERAGE:")
print(f"  Expected tracks:      ~{expected}")
print(f"  URLs discovered:      {actual} ({actual/expected*100:.1f}%)")
print(f"  Successfully saved:   {downloaded_count} ({success_rate:.1f}%)")

if failed_downloads:
    print(f"\n⚠ FAILED DOWNLOADS:")
    for url in failed_downloads[:10]:
        track = mp3_data.get(url, {})
        print(f"    - {track.get('name', 'Unknown')}: {url[:60]}...")
    if len(failed_downloads) > 10:
        print(f"    ... and {len(failed_downloads) - 10} more")

print(f"\n💡 TIPS:")
print(f"  - Run this script again to retry failed downloads")
print(f"  - Check the manifest file for detailed tracking")
print(f"  - You can delete {TEMP_DIR} once you verify organized files")

print("="*80)
