#!/usr/bin/env python3
"""
KLF Track Renamer - Post-Download Name Fixer
Matches downloaded MP3 files to correct track names from the website list
"""
import os
import shutil
from pathlib import Path

# PASTE YOUR TRACK LIST HERE (one track per line)
TRACK_LIST = """
The Queen & I (Do Not Attempt To Beat Mix) - Mario S. David (Rhythm Stick)
Britney Joins The Jams - Dj Nite
Burn The Beat - N/A
Downtown (Swemix)
Down Town (Neon Signs Are Pretty) - M.Ward
It's Always Grim Up North (Anatolian Weapons Edit)
""".strip().split('\n')

# YOUR DOWNLOAD DIRECTORIES
DOWNLOAD_DIR = Path.home() / "Desktop" / "klf-remixes-v4"  # or v5
TEMP_DIR = DOWNLOAD_DIR / "_downloads"
RENAMED_DIR = DOWNLOAD_DIR / "_renamed"

def sanitize_filename(name):
    """Clean filename for filesystem"""
    import re
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]

def main():
    print("="*80)
    print(" KLF TRACK RENAMER - Fix Names After Download")
    print("="*80)

    # Check if directory exists
    if not TEMP_DIR.exists():
        print(f"\n❌ Directory not found: {TEMP_DIR}")
        print("\nPlease edit the script and set DOWNLOAD_DIR to your download location")
        return

    # Get all MP3 files
    mp3_files = sorted(list(TEMP_DIR.glob("*.mp3")))

    if not mp3_files:
        print(f"\n❌ No MP3 files found in {TEMP_DIR}")
        return

    print(f"\n📁 Found {len(mp3_files)} MP3 files")
    print(f"📝 Have {len(TRACK_LIST)} track names from website")

    # Create renamed directory
    RENAMED_DIR.mkdir(exist_ok=True)

    print(f"\n🔄 Renaming files...\n")

    # Simple approach: match files in order to track list
    for idx, mp3_file in enumerate(mp3_files):
        if idx < len(TRACK_LIST):
            # Get the track name
            track_name = TRACK_LIST[idx].strip()

            if not track_name:
                continue

            # Create new filename
            new_name = sanitize_filename(track_name)
            new_path = RENAMED_DIR / f"{idx+1:03d}_{new_name}.mp3"

            # Copy file
            shutil.copy2(mp3_file, new_path)

            print(f"[{idx+1:03d}] {track_name}")

        else:
            # More files than track names - keep original
            shutil.copy2(mp3_file, RENAMED_DIR / mp3_file.name)
            print(f"[{idx+1:03d}] {mp3_file.name} (no track name)")

    print(f"\n✅ Done! Renamed files saved to:")
    print(f"   {RENAMED_DIR}")
    print("="*80)

if __name__ == "__main__":
    main()
