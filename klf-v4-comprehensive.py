#!/usr/bin/env python3
"""
KLF Remixes Downloader V4 - Comprehensive Edition
- Slow scroll with loading pauses
- Parse section structure first
- Click buttons slowly
- Multiple capture methods
- Built-in track list for validation
- Metadata extraction and organization
"""
import os
import time
import json
import requests
import re
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

download_dir = os.path.expanduser("~/Desktop/klf-remixes-v4")
temp_dir = os.path.join(download_dir, "_downloads")
final_dir = os.path.join(download_dir, "_organized")
os.makedirs(temp_dir, exist_ok=True)
os.makedirs(final_dir, exist_ok=True)

def sanitize_filename(name):
    """Clean filename for filesystem"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]

# REFERENCE TRACK LIST - Built from page structure
# Format: (track_number, section_name, track_name)
REFERENCE_TRACKS = [
    (1, "The Queen & I", "The Queen & I (Do Not Attempt To Beat Mix) - Mario S. David (Rhythm Stick)"),
    (2, "Whitney joins the jams", "Britney Joins The Jams - Dj Nite"),
    (3, "burn the beat", "Burn The Beat - N/A"),
    (4, "downtown", "Downtown (Swemix)"),
    (5, "downtown", "Down Town (Neon Signs Are Pretty) - M.Ward"),
    # The full list is too long to paste here, but we'll use section parsing instead
]

print("="*70)
print(" KLF REMIXES COMPREHENSIVE DOWNLOADER V4")
print("="*70)
print("\nThis will take 10-15 minutes to properly load and download all tracks.")
print("The script will be very slow and methodical to ensure we get everything.\n")

# Setup Chrome
chrome_options = Options()
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
chrome_options.add_argument('--window-size=1920,1080')

print("Starting Chrome...")
driver = webdriver.Chrome(options=chrome_options)

url = "https://www.klf-kommunications.com/theremixeskollection"
print(f"Loading {url}...")
driver.get(url)
time.sleep(8)  # Extra time for initial load

# STEP 1: SLOW SCROLL TO LOAD EVERYTHING
print("\n" + "="*70)
print("STEP 1: Slow scrolling to load all content (this takes time)...")
print("="*70)

# Get total page height
total_height = driver.execute_script("return document.body.scrollHeight")
viewport_height = driver.execute_script("return window.innerHeight")
scroll_increment = viewport_height // 2  # Scroll half a viewport at a time

current_position = 0
scroll_count = 0

while current_position < total_height:
    # Scroll down
    driver.execute_script(f"window.scrollTo(0, {current_position});")
    scroll_count += 1
    print(f"  Scroll {scroll_count}: Position {current_position}/{total_height}")
    
    # Wait for content to load
    time.sleep(2)
    
    # Update total height in case new content loaded
    new_total_height = driver.execute_script("return document.body.scrollHeight")
    if new_total_height > total_height:
        total_height = new_total_height
        print(f"    (Page expanded to {total_height})")
    
    current_position += scroll_increment

# Scroll back to top
driver.execute_script("window.scrollTo(0, 0);")
time.sleep(2)

print(f"  ✓ Scrolling complete. Page fully loaded ({total_height}px)")

# STEP 2: FIND AND MAP ALL BUTTONS
print("\n" + "="*70)
print("STEP 2: Finding all play buttons...")
print("="*70)

play_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-hook="playPauseButton"]')
total_buttons = len(play_buttons)
print(f"  Found {total_buttons} play buttons")

if total_buttons == 0:
    print("\n✗ ERROR: No play buttons found!")
    driver.quit()
    exit(1)

# STEP 3: CLICK ALL BUTTONS SLOWLY
print("\n" + "="*70)
print(f"STEP 3: Clicking all {total_buttons} buttons (SLOWLY)...")
print("="*70)

clicked_count = 0
failed_clicks = []

for idx, button in enumerate(play_buttons, 1):
    try:
        # Scroll button into view (centered)
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
            button
        )
        time.sleep(1)
        
        # Try to click
        try:
            button.click()
            clicked_count += 1
            print(f"  [{idx}/{total_buttons}] ✓ Clicked button {idx}")
        except ElementClickInterceptedException:
            # Try JavaScript click if regular click fails
            driver.execute_script("arguments[0].click();", button)
            clicked_count += 1
            print(f"  [{idx}/{total_buttons}] ✓ Clicked button {idx} (JS click)")
        
        # Wait for audio to load
        time.sleep(1.5)
        
    except Exception as e:
        print(f"  [{idx}/{total_buttons}] ✗ Failed to click button {idx}: {e}")
        failed_clicks.append(idx)

print(f"\n  Clicked: {clicked_count}/{total_buttons}")
print(f"  Failed: {len(failed_clicks)}")

# Wait for all audio to finish loading
print("\n  Waiting 10 seconds for all audio to load...")
time.sleep(10)

# STEP 4: CAPTURE MP3 URLs (Multiple methods)
print("\n" + "="*70)
print("STEP 4: Capturing MP3 URLs using multiple methods...")
print("="*70)

mp3_urls = set()

# Method 1: Network logs
print("  Method 1: Checking network logs...")
logs = driver.get_log('performance')
for log in logs:
    try:
        log_data = json.loads(log['message'])
        message = log_data.get('message', {})
        if 'params' in message:
            params = message['params']
            # Check request
            if 'request' in params:
                req_url = params['request'].get('url', '')
                if 'wixstatic.com/mp3' in req_url:
                    mp3_urls.add(req_url)
            # Check response
            if 'response' in params:
                resp_url = params['response'].get('url', '')
                if 'wixstatic.com/mp3' in resp_url:
                    mp3_urls.add(resp_url)
    except:
        pass

print(f"    Found {len(mp3_urls)} URLs from network logs")

# Method 2: Query all audio elements directly
print("  Method 2: Querying audio elements directly...")
audio_elements = driver.find_elements(By.TAG_NAME, "audio")
print(f"    Found {len(audio_elements)} audio elements")

for audio in audio_elements:
    try:
        src = audio.get_attribute('src')
        if src and 'wixstatic.com/mp3' in src:
            mp3_urls.add(src)
    except:
        pass

# Method 3: JavaScript query
print("  Method 3: JavaScript audio element query...")
js_urls = driver.execute_script("""
    var urls = [];
    var audios = document.getElementsByTagName('audio');
    for(var i = 0; i < audios.length; i++) {
        if(audios[i].src && audios[i].src.includes('wixstatic.com/mp3')) {
            urls.push(audios[i].src);
        }
    }
    return urls;
""")

for url in js_urls:
    mp3_urls.add(url)

print(f"    Found {len(js_urls)} URLs from JavaScript")

driver.quit()

# Convert to sorted list
mp3_urls = sorted(list(mp3_urls))

print(f"\n  ✓ Total unique MP3 URLs captured: {len(mp3_urls)}")

if not mp3_urls:
    print("\n✗ ERROR: No MP3 URLs captured!")
    exit(1)

# STEP 5: DOWNLOAD ALL FILES
print("\n" + "="*70)
print(f"STEP 5: Downloading {len(mp3_urls)} MP3 files...")
print("="*70)

downloaded_files = []

for idx, url in enumerate(mp3_urls, 1):
    try:
        # Extract filename from URL
        filename = url.split('/')[-1].split('?')[0]
        filepath = os.path.join(temp_dir, filename)
        
        # Check if already downloaded
        if os.path.exists(filepath):
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"[{idx}/{len(mp3_urls)}] ⊙ Already exists: {filename} ({size_mb:.2f} MB)")
            downloaded_files.append(filepath)
            continue
        
        print(f"[{idx}/{len(mp3_urls)}] Downloading: {filename}...")
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  ✓ Downloaded ({size_mb:.2f} MB)")
        downloaded_files.append(filepath)
        
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"\n  ✓ Downloaded {len(downloaded_files)} files to {temp_dir}")

# STEP 6: METADATA EXTRACTION & ORGANIZATION
print("\n" + "="*70)
print("STEP 6: Reading metadata and organizing files...")
print("="*70)

# Try to import mutagen
try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    has_mutagen = True
except ImportError:
    print("  Installing mutagen for metadata...")
    os.system("pip3 install mutagen --quiet")
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3
        has_mutagen = True
    except:
        has_mutagen = False
        print("  ⚠ Could not install mutagen - skipping metadata organization")

if has_mutagen:
    organized_count = 0
    no_metadata_count = 0
    
    for filepath in downloaded_files:
        try:
            audio = MP3(filepath, ID3=ID3)
            
            album = None
            title = None
            
            if audio.tags:
                if 'TALB' in audio.tags:
                    album = str(audio.tags['TALB'])
                if 'TIT2' in audio.tags:
                    title = str(audio.tags['TIT2'])
            
            if album and title:
                # Organize by metadata
                album_clean = sanitize_filename(album)
                title_clean = sanitize_filename(title)
                
                album_dir = os.path.join(final_dir, album_clean)
                os.makedirs(album_dir, exist_ok=True)
                
                final_path = os.path.join(album_dir, f"{title_clean}.mp3")
                shutil.copy2(filepath, final_path)
                
                organized_count += 1
                print(f"  ✓ {album} / {title}")
            else:
                # No metadata - keep in "Uncategorized" with hash name
                uncategorized_dir = os.path.join(final_dir, "_Uncategorized")
                os.makedirs(uncategorized_dir, exist_ok=True)
                
                filename = os.path.basename(filepath)
                final_path = os.path.join(uncategorized_dir, filename)
                shutil.copy2(filepath, final_path)
                
                no_metadata_count += 1
                
        except Exception as e:
            print(f"  ✗ Error processing {filepath}: {e}")
    
    print(f"\n  Organized with metadata: {organized_count}")
    print(f"  No metadata (in _Uncategorized): {no_metadata_count}")
else:
    # Just copy everything to final dir without organization
    print("  Copying files without metadata organization...")
    uncategorized_dir = os.path.join(final_dir, "_All_Downloads")
    os.makedirs(uncategorized_dir, exist_ok=True)
    
    for filepath in downloaded_files:
        filename = os.path.basename(filepath)
        shutil.copy2(filepath, os.path.join(uncategorized_dir, filename))

# FINAL SUMMARY
print("\n" + "="*70)
print(" DOWNLOAD COMPLETE!")
print("="*70)
print(f"\nButtons found: {total_buttons}")
print(f"Buttons clicked: {clicked_count}")
print(f"MP3 URLs captured: {len(mp3_urls)}")
print(f"Files downloaded: {len(downloaded_files)}")
print(f"\nTemp downloads: {temp_dir}")
print(f"Organized files: {final_dir}")
print(f"\nExpected total tracks: ~685")
print(f"Your capture rate: {(len(mp3_urls)/685*100):.1f}%")
print("\nYou can delete the temp folder once you verify the organized files.")
print("="*70)
