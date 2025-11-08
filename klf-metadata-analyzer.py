#!/usr/bin/env python3
"""
KLF Smart Renamer - Uses ID3 Metadata to Match Correct Track Names
Reads metadata from downloaded files and matches them to the website track list
"""
import os
from pathlib import Path
from difflib import SequenceMatcher

# Try to import mutagen for ID3 reading
try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("⚠️  Installing mutagen for metadata reading...")
    os.system("pip3 install mutagen")
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3
        HAS_MUTAGEN = True
    except:
        print("❌ Could not install mutagen. Exiting.")
        exit(1)

# CONFIGURATION - UPDATE THESE PATHS
DOWNLOAD_DIR = Path.home() / "Desktop" / "klf-remixes-v5" / "_raw_downloads"
# Alternative common locations:
# DOWNLOAD_DIR = Path.home() / "Desktop" / "klf-remixes-v4" / "_downloads"
# DOWNLOAD_DIR = Path.home() / "Downloads" / "klf"

def read_id3_metadata(mp3_file):
    """Read ID3 metadata from an MP3 file"""
    try:
        audio = MP3(mp3_file, ID3=ID3)

        metadata = {
            'file': mp3_file.name,
            'title': None,
            'album': None,
            'artist': None,
            'has_metadata': False
        }

        if audio.tags:
            # Title
            if 'TIT2' in audio.tags:
                metadata['title'] = str(audio.tags['TIT2'])
                metadata['has_metadata'] = True

            # Album
            if 'TALB' in audio.tags:
                metadata['album'] = str(audio.tags['TALB'])
                metadata['has_metadata'] = True

            # Artist
            if 'TPE1' in audio.tags:
                metadata['artist'] = str(audio.tags['TPE1'])
                metadata['has_metadata'] = True

        return metadata
    except Exception as e:
        return {
            'file': mp3_file.name,
            'title': None,
            'album': None,
            'artist': None,
            'has_metadata': False,
            'error': str(e)
        }

def similarity(a, b):
    """Calculate similarity between two strings"""
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_match(metadata, track_list):
    """Find the best matching track name from the list"""
    if not metadata['has_metadata']:
        return None, 0

    # Try to match on title
    title = metadata.get('title', '')
    album = metadata.get('album', '')

    best_match = None
    best_score = 0

    for track in track_list:
        # Try matching title
        if title:
            score = similarity(title, track)
            if score > best_score:
                best_score = score
                best_match = track

        # Also try matching album info in the track name
        if album:
            score = similarity(album, track)
            if score > best_score:
                best_score = score
                best_match = track

    return best_match, best_score

def main():
    print("="*80)
    print(" KLF SMART RENAMER - ID3 Metadata-Based Name Matching")
    print("="*80)

    # Check if directory exists
    if not DOWNLOAD_DIR.exists():
        print(f"\n❌ Directory not found: {DOWNLOAD_DIR}")
        print("\nPlease edit this script and set DOWNLOAD_DIR to your download location.")
        print("\nCommon locations:")
        print(f"  ~/Desktop/klf-remixes-v5/_raw_downloads")
        print(f"  ~/Desktop/klf-remixes-v4/_downloads")
        print(f"  ~/Downloads/klf")
        return

    # Get all MP3 files
    mp3_files = sorted(list(DOWNLOAD_DIR.glob("*.mp3")))

    if not mp3_files:
        print(f"\n❌ No MP3 files found in {DOWNLOAD_DIR}")
        return

    print(f"\n📁 Found {len(mp3_files)} MP3 files in:")
    print(f"   {DOWNLOAD_DIR}")

    # Read metadata from all files
    print(f"\n🔍 Reading ID3 metadata from files...\n")

    files_with_metadata = []
    files_without_metadata = []

    for idx, mp3_file in enumerate(mp3_files, 1):
        metadata = read_id3_metadata(mp3_file)

        if metadata['has_metadata']:
            files_with_metadata.append((mp3_file, metadata))
        else:
            files_without_metadata.append((mp3_file, metadata))

        # Show progress every 50 files
        if idx % 50 == 0:
            print(f"  Processed {idx}/{len(mp3_files)} files...")

    print(f"\n📊 RESULTS:")
    print(f"  Files WITH metadata:    {len(files_with_metadata)}")
    print(f"  Files WITHOUT metadata: {len(files_without_metadata)}")

    # Display first 20 files with their metadata
    print(f"\n📋 FIRST 20 FILES - METADATA CHECK:")
    print("="*80)

    for idx, (mp3_file, metadata) in enumerate(files_with_metadata[:20], 1):
        print(f"\n[{idx:03d}] FILE: {mp3_file.name}")
        if metadata['title']:
            print(f"     TITLE:  {metadata['title']}")
        if metadata['album']:
            print(f"     ALBUM:  {metadata['album']}")
        if metadata['artist']:
            print(f"     ARTIST: {metadata['artist']}")
        if not metadata['has_metadata']:
            print(f"     ⚠️  NO METADATA")

    # Show files without metadata
    if files_without_metadata:
        print(f"\n\n⚠️  FILES WITHOUT METADATA (first 10):")
        print("="*80)
        for idx, (mp3_file, metadata) in enumerate(files_without_metadata[:10], 1):
            print(f"  [{idx}] {mp3_file.name}")

    # Ask user to verify
    print("\n" + "="*80)
    print("📝 VERIFICATION NEEDED:")
    print("="*80)
    print("\nPlease check the metadata above and verify:")
    print("  1. Does the TITLE match what you expect?")
    print("  2. Can you manually check file [001] to confirm it's 'The Rites of Matrix'?")
    print("  3. Can you manually check file [002] to confirm it's 'The Queen & I'?")
    print("\nOnce verified, I can create the proper renaming script.")
    print("\nTo test a specific file, you can:")
    print(f"  - Open the file in a music player")
    print(f"  - Check 'Get Info' or 'Properties' to see metadata")
    print(f"  - Or listen to it to identify the track")

    # Save report to file
    report_file = DOWNLOAD_DIR.parent / "metadata_report.txt"
    with open(report_file, 'w') as f:
        f.write("KLF METADATA REPORT\n")
        f.write("="*80 + "\n\n")

        f.write(f"Total files: {len(mp3_files)}\n")
        f.write(f"Files with metadata: {len(files_with_metadata)}\n")
        f.write(f"Files without metadata: {len(files_without_metadata)}\n\n")

        f.write("="*80 + "\n")
        f.write("ALL FILES WITH METADATA:\n")
        f.write("="*80 + "\n\n")

        for idx, (mp3_file, metadata) in enumerate(files_with_metadata, 1):
            f.write(f"[{idx:03d}] {mp3_file.name}\n")
            if metadata['title']:
                f.write(f"      Title:  {metadata['title']}\n")
            if metadata['album']:
                f.write(f"      Album:  {metadata['album']}\n")
            if metadata['artist']:
                f.write(f"      Artist: {metadata['artist']}\n")
            f.write("\n")

        if files_without_metadata:
            f.write("\n" + "="*80 + "\n")
            f.write("FILES WITHOUT METADATA:\n")
            f.write("="*80 + "\n\n")

            for idx, (mp3_file, metadata) in enumerate(files_without_metadata, 1):
                f.write(f"  [{idx}] {mp3_file.name}\n")

    print(f"\n💾 Full metadata report saved to:")
    print(f"   {report_file}")
    print("="*80)

if __name__ == "__main__":
    main()
