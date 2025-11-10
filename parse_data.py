# parse_data.py
import json

# This is the big file we just added
WLASL_JSON_FILE = 'WLASL_info.json' 
OUTPUT_MAP_FILE = 'sign_video_map.json'

print(f"Loading data from {WLASL_JSON_FILE}...")

try:
    with open(WLASL_JSON_FILE, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"ERROR: Could not find {WLASL_JSON_FILE}.")
    print("Please make sure you moved and renamed the file correctly.")
    exit()

video_map = {}

# The WLASL JSON is a list of entries
for entry in data:
    word = entry['gloss']

    # An entry can have many video instances
    if not entry['instances']:
        continue

    # Let's just grab the FIRST video instance for simplicity
    first_instance = entry['instances'][0]

    # Get the video ID (which matches the .mp4 file name)
    video_id = first_instance.get('video_id')

    if word and video_id:
        # Save the word in lowercase for easy lookup
        if word.lower() not in video_map:
             video_map[word.lower()] = video_id

# Now, save our new, simple map
with open(OUTPUT_MAP_FILE, 'w') as f:
    json.dump(video_map, f, indent=2)

print(f"Success! Created {OUTPUT_MAP_FILE} with {len(video_map)} sign-to-video links.")