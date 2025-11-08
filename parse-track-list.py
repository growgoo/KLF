#!/usr/bin/env python3
"""
Parse the KLF track list from website text and create a clean numbered list
"""

# Paste the track section text here - I'll extract just the track names
raw_text = """
The Queen & I (Do Not Attempt To Beat Mix) - Mario S. David (Rhythm Stick)
Britney Joins The Jams - Dj Nite
Burn The Beat - N/A
Downtown (Swemix)
Down Town (Neon Signs Are Pretty) - M.Ward
"""

# Extract tracks - filter out section headers and images
tracks = []
for line in raw_text.strip().split('\n'):
    line = line.strip()

    # Skip empty lines
    if not line:
        continue

    # Skip image files
    if any(ext in line.lower() for ext in ['.png', '.jpg', '.gif', '.jpeg', '.webp']):
        continue

    # Skip obvious section headers (all lowercase or very short)
    if len(line) < 5:
        continue

    # Skip lines that are just symbols or separators
    if line.startswith('---') or line == '​':
        continue

    # This looks like a track
    tracks.append(line)

# Save to file
with open('klf-tracks-numbered.txt', 'w') as f:
    for idx, track in enumerate(tracks, 1):
        f.write(f"{idx:03d}|{track}\n")

print(f"✅ Extracted {len(tracks)} tracks")
print(f"📄 Saved to: klf-tracks-numbered.txt")
print(f"\nFirst 10 tracks:")
for i, track in enumerate(tracks[:10], 1):
    print(f"  {i:03d}. {track}")
