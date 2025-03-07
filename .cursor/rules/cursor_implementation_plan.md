# Implementation Plan

Let's implement all your requested features:

```python:UGCReelGen.py
import os
import random
import logging
import pandas as pd
from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip, 
    concatenate_videoclips, AudioFileClip, concatenate_audioclips
)
import time
from tqdm import tqdm
import numpy as np
import tempfile
from elevenlabs import generate, save, set_api_key
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---- CONFIGURATION ----
HOOKS_CSV = "hooks.csv"  # Path to your hooks CSV file (columns: id, text)
HOOK_VIDEOS_FOLDER = "hook_videos"  # Folder containing all hook videos
CTA_VIDEOS_FOLDER = "cta_videos"  # Folder containing all CTA videos
OUTPUT_FOLDER = "final_videos"  # Folder to save the final videos
USED_HOOKS_FILE = "used_hooks.txt"  # File to track used hooks
NUM_VIDEOS = 10  # Number of final videos to create
FONT = "./fonts/BeVietnamPro-Bold.ttf"  # Path to custom font file
FONT_SIZE = 70  # Font size for overlay text
TEXT_COLOR = "white"  # Color of the overlay text
BACKGROUND_COLOR = "black"  # Background color for overlay text
LOG_FILE = "video_creation.log"  # Log file will be created in current directory
TARGET_RESOLUTION = (1080, 1920)  # Vertical video format (9:16 aspect ratio)
VIDEO_LIST_FILE = "video_list.txt"  # File to track video details
MUSIC_FOLDER = "music"  # Folder containing background music

# ---- NEW CONFIGURATION OPTIONS ----
# Set to True to generate every hook with every video, False for random combinations
GENERATE_ALL_COMBINATIONS = False

# ElevenLabs configuration
USE_ELEVENLABS = True  # Set to False to disable ElevenLabs TTS
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")  # API key from .env file
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Adam")  # Voice ID from .env file

# CTA videos configuration
MAX_CTA_VIDEOS = 3  # Maximum number of CTA videos to use per final video
MAX_CTA_DURATION = 30  # Maximum duration in seconds for all CTA videos combined

# ---- SETUP LOGGING ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # This ensures logs are also printed to console
    ]
)

# ---- FUNCTION DEFINITIONS ----

def setup_output_folder(folder_path):
    """Ensure the output folder exists."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logging.info(f"Created output folder: {folder_path}")
    else:
        logging.info(f"Output folder already exists: {folder_path}")

def load_hooks(csv_path):
    """Load hooks from a CSV file."""
    if not os.path.exists(csv_path):
        logging.error(f"Hooks CSV file not found: {csv_path}")
        raise FileNotFoundError(f"Hooks CSV file not found: {csv_path}")
    hooks = pd.read_csv(csv_path)
    logging.info(f"Loaded {len(hooks)} hooks from {csv_path}")
    return hooks

def load_used_hooks(file_path):
    """Load the list of already used hooks from a file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            used_hooks = set(f.read().splitlines())
            logging.info(f"Loaded {len(used_hooks)} used hooks.")
            return used_hooks
    else:
        logging.info("No used hooks file found. Starting fresh.")
        return set()

def save_used_hook(file_path, hook_text):
    """Save a used hook to the tracking file."""
    with open(file_path, "a") as f:
        f.write(hook_text + "\n")
    logging.info(f"Saved used hook: {hook_text}")

def get_unused_hook(hooks, used_hooks):
    """Get a random unused hook from the hooks list."""
    unused_hooks = hooks[~hooks["text"].isin(used_hooks)]
    if unused_hooks.empty:
        logging.error("No unused hooks available! All hooks have been used.")
        raise ValueError("No unused hooks available.")
    selected_hook = unused_hooks.sample(1).iloc[0]["text"]
    return selected_hook

def get_random_video(folder_path):
    """Pick a random video file from a folder."""
    if not os.path.exists(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    video_files = [f for f in os.listdir(folder_path) if f.endswith((".mp4", ".mov"))]
    if not video_files:
        logging.error(f"No video files found in {folder_path}")
        raise FileNotFoundError(f"No video files found in {folder_path}")
    selected_video = random.choice(video_files)
    logging.info(f"Selected video: {selected_video}")
    return os.path.join(folder_path, selected_video)

def get_all_videos(folder_path):
    """Get all video files from a folder."""
    if not os.path.exists(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    video_files = [f for f in os.listdir(folder_path) if f.endswith((".mp4", ".mov"))]
    if not video_files:
        logging.error(f"No video files found in {folder_path}")
        raise FileNotFoundError(f"No video files found in {folder_path}")
    return [os.path.join(folder_path, video) for video in video_files]

def get_multiple_cta_videos(folder_path, max_count=MAX_CTA_VIDEOS, max_duration=MAX_CTA_DURATION):
    """Get multiple CTA videos respecting max count and duration limits."""
    all_cta_videos = get_all_videos(folder_path)
    random.shuffle(all_cta_videos)
    
    selected_videos = []
    total_duration = 0
    
    # First, calculate durations for each video
    video_durations = {}
    for video_path in all_cta_videos:
        try:
            with VideoFileClip(video_path) as clip:
                video_durations[video_path] = clip.duration
        except Exception as e:
            logging.error(f"Error getting duration for {video_path}: {e}")
            video_durations[video_path] = 0
    
    # Then select videos respecting both count and duration limits
    for video_path in all_cta_videos:
        if len(selected_videos) >= max_count:
            break
            
        duration = video_durations[video_path]
        if total_duration + duration <= max_duration:
            selected_videos.append(video_path)
            total_duration += duration
    
    logging.info(f"Selected {len(selected_videos)} CTA videos with total duration {total_duration:.2f}s")
    return selected_videos

def get_random_music(folder_path):
    """Pick a random music file from the folder."""
    if not os.path.exists(folder_path):
        logging.error(f"Music folder not found: {folder_path}")
        raise FileNotFoundError(f"Music folder not found: {folder_path}")
    
    music_files = [f for f in os.listdir(folder_path) if f.endswith((".mp3", ".wav", ".m4a"))]
    if not music_files:
        logging.error(f"No music files found in {folder_path}")
        raise FileNotFoundError(f"No music files found in {folder_path}")
    
    selected_music = random.choice(music_files)
    logging.info(f"Selected music: {selected_music}")
    return os.path.join(folder_path, selected_music)

def generate_elevenlabs_tts(text, output_path):
    """Generate TTS audio from text using ElevenLabs and save to file."""
    try:
        # Set the API key
        set_api_key(ELEVENLABS_API_KEY)
        
        # Generate audio using ElevenLabs
        audio = generate(
            text=text,
            voice=ELEVENLABS_VOICE,
            model="eleven_monolingual_v1"
        )
        
        # Save the audio to file
        save(audio, output_path)
        
        logging.info(f"Generated ElevenLabs TTS audio for: {text}")
        return True
    except Exception as e:
        logging.error(f"Error generating ElevenLabs TTS: {e}")
        # If ElevenLabs fails, we should implement a fallback
        return False

def resize_video(clip, target_resolution):
    """Resize video to fill target resolution (may crop to fill)"""
    target_w, target_h = target_resolution
    clip_w, clip_h = clip.size
    
    # Scale to fill
    scale = max(target_w/clip_w, target_h/clip_h)
    new_w = int(clip_w * scale)
    new_h = int(clip_h * scale)
    
    # First scale up
    clip = clip.resize(width=new_w, height=new_h)
    
    # Then crop to target size
    x_center = new_w/2
    y_center = new_h/2
    x1 = int(x_center - target_w/2)
    y1 = int(y_center - target_h/2)
    return clip.crop(x1=x1, y1=y1, width=target_w, height=target_h)

def create_video(hook_video_path, hook_text, cta_video_paths, music_path, output_path):
    """Create a single video by combining hook video, text, CTA videos, and music."""
    try:
        print(f"\nProcessing video with hook: {hook_text}")
        
        # Generate TTS if enabled
        tts_audio = None
        if USE_ELEVENLABS:
            print("Generating TTS with ElevenLabs...")
            tts_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            if generate_elevenlabs_tts(hook_text, tts_file):
                tts_audio = AudioFileClip(tts_file)
        
        print("Loading hook video...")
        hook_clip = VideoFileClip(hook_video_path)
        hook_clip = resize_video(hook_clip, TARGET_RESOLUTION)
        
        # If TTS is enabled and successfully generated, make sure hook clip is long enough
        if tts_audio and tts_audio.duration > hook_clip.duration:
            # Loop the clip to match the TTS duration
            hook_clip = hook_clip.loop(duration=tts_audio.duration)

        print("Adding text overlay...")
        # Calculate text width with margins
        text_width = hook_clip.w - 120  # 80px margin on each side
        
        # Create main text clip with improved smoothness
        text_clip_args = {
            "txt": hook_text,
            "fontsize": FONT_SIZE,
            "color": TEXT_COLOR,
            "font": FONT,
            "method": 'caption',
            "size": (text_width, None),
            "align": 'center',
            "stroke_color": 'black',
            "stroke_width": 2,  # Keep this for main text
            "kerning": -1,
            "interline": -1,
        }
        
        # Reduced glow effect
        glow_layers = 1  # Reduced from 2 to 1 layers
        glow_clips = []
        
        # Create fewer glow layers with lower opacity
        for i in range(glow_layers):
            glow = (TextClip(**{**text_clip_args, 
                              "color": "black",
                              "stroke_width": 2 + i,  # Reduced from 4+i to 2+i
                              "stroke_color": "black"})
                   .set_duration(hook_clip.duration)
                   .set_position(("center", 200))
                   .set_opacity(0.2))  # Reduced opacity from 0.3 to 0.2
            glow_clips.append(glow)

        # Main text on top
        main_text = (TextClip(**text_clip_args)
                    .set_duration(hook_clip.duration)
                    .set_position(("center", 200)))

        # Combine hook video with text and TTS audio if enabled
        print("Combining hook, text, and audio...")
        if tts_audio:
            # If hook has audio, combine it with TTS at lower volume
            if hook_clip.audio:
                hook_audio = hook_clip.audio.volumex(0.1)
                combined_audio = CompositeAudioClip([hook_audio, tts_audio.volumex(1.0)])
            else:
                combined_audio = tts_audio
                
            # Create combined hook with text and audio
            combined_hook = CompositeVideoClip([hook_clip] + glow_clips + [main_text])
            combined_hook = combined_hook.set_audio(combined_audio)
        else:
            # No TTS, just combine hook with text overlay
            combined_hook = CompositeVideoClip([hook_clip] + glow_clips + [main_text])

        # Load CTA videos
        print("Loading CTA videos...")
        cta_clips = []
        for cta_path in cta_video_paths:
            cta_clip = VideoFileClip(cta_path)
            cta_clip = resize_video(cta_clip, TARGET_RESOLUTION)
            cta_clips.append(cta_clip)
        
        # Combine all videos
        print("Creating final video...")
        final_video = concatenate_videoclips([combined_hook] + cta_clips)
        
        # Add background music
        print("Adding background music...")
        background_music = AudioFileClip(music_path)
        
        # Loop or trim music to match video duration
        if background_music.duration < final_video.duration:
            # Loop music if it's shorter than video
            n_loops = int(np.ceil(final_video.duration / background_music.duration))
            background_music = concatenate_audioclips([background_music] * n_loops)
        
        # Trim music to video duration and set volume
        background_music = background_music.subclip(0, final_video.duration).volumex(0.3)
        
        # If we have TTS, don't override its audio - mix the music at lower volume
        if tts_audio:
            final_audio = CompositeAudioClip([final_video.audio, background_music.volumex(0.2)])
            final_video = final_video.set_audio(final_audio)
        else:
            # No TTS, just use the background music
            final_video = final_video.set_audio(background_music)

        print(f"Writing final video to {output_path}...")
        final_video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264",
            preset='medium',
            verbose=False,
            logger=None
        )
        
        # Clean up
        hook_clip.close()
        for clip in cta_clips:
            clip.close()
        background_music.close()
        final_video.close()
        
        # Clean up temp TTS file if it exists
        if tts_audio:
            tts_audio.close()
            if os.path.exists(tts_file):
                os.unlink(tts_file)
        
        logging.info(f"Created video: {output_path} at resolution {TARGET_RESOLUTION}")
        print(f"✅ Video created successfully: {output_path}")
        
    except Exception as e:
        logging.error(f"Error creating video: {e}")
        print(f"❌ Error creating video: {e}")
        raise

def get_last_video_number():
    """Get the last video number from video_list.txt"""
    if not os.path.exists(VIDEO_LIST_FILE):
        return 0
        
    try:
        with open(VIDEO_LIST_FILE, 'r') as f:
            # Skip header
            next(f, None)
            # Read all lines
            lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                return 0
            
            numbers = []
            for line in lines:
                try:
                    # Get the last column (final_video name)
                    final_video = line.split(',')[-1].strip('"')
                    # Extract number between 'final_video_' and '.mp4'
                    num = int(final_video.replace('final_video_', '').replace('.mp4', ''))
                    numbers.append(num)
                except (IndexError, ValueError) as e:
                    logging.error(f"Error parsing line '{line}': {e}")
                    continue
            
            last_num = max(numbers) if numbers else 0
            logging.info(f"Found last video number: {last_num}")
            return last_num
            
    except Exception as e:
        logging.error(f"Error reading video list file: {e}")
        return 0

def save_video_details(hook_video, hook_text, cta_videos, music_file, final_video):
    """Save video details to tracking file"""
    try:
        # Create file with header if it doesn't exist
        if not os.path.exists(VIDEO_LIST_FILE):
            with open(VIDEO_LIST_FILE, 'w') as f:
                f.write("hook_video,hook_text,cta_videos,music_file,final_video\n")
        
        # Format CTA videos as a semicolon-separated list
        cta_videos_str = ';'.join([os.path.basename(v) for v in cta_videos])
        
        # Append video details
        with open(VIDEO_LIST_FILE, 'a') as f:
            # Escape any commas in hook_text and cta_videos_str 
            safe_hook_text = f'"{hook_text}"' if ',' in hook_text else hook_text
            safe_cta_videos = f'"{cta_videos_str}"' if ',' in cta_videos_str else cta_videos_str
            
            line = f"{os.path.basename(hook_video)},{safe_hook_text},{safe_cta_videos},{os.path.basename(music_file)},{final_video}\n"
            f.write(line)
            logging.info(f"Saved video details: {line.strip()}")
            
    except Exception as e:
        logging.error(f"Error saving video details: {e}")

def main():
    """Main script to automate video creation."""
    start_time = time.time()
    
    print("\n🎬 Starting UGC Reel Generator...")
    logging.info("Starting video generation process")
    
    try:
        # Get last video number
        last_number = get_last_video_number()
        print(f"📝 Last video number: {last_number}")
        
        # Ensure the output folder exists
        setup_output_folder(OUTPUT_FOLDER)

        # Load hooks
        hooks = load_hooks(HOOKS_CSV)
        print(f"📝 Loaded {len(hooks)} hooks from {HOOKS_CSV}")

        # Load hook videos
        hook_videos = get_all_videos(HOOK_VIDEOS_FOLDER)
        print(f"📝 Found {len(hook_videos)} hook videos")
        
        # Track used hooks if not generating all combinations
        if not GENERATE_ALL_COMBINATIONS:
            used_hooks = load_used_hooks(USED_HOOKS_FILE)
            print(f"🔄 Found {len(used_hooks)} previously used hooks")

            # Check if we have enough unused hooks
            if len(used_hooks) >= len(hooks):
                print("\n⚠️  No more fresh hooks available! All hooks have been used.")
                logging.info("Process stopped: All hooks have been used")
                return

        # Generate videos
        if GENERATE_ALL_COMBINATIONS:
            # Create all possible combinations
            combinations = []
            for hook_data in hooks.itertuples():
                hook_text = hook_data.text
                for hook_video in hook_videos:
                    combinations.append((hook_video, hook_text))
            
            if NUM_VIDEOS > 0 and len(combinations) > NUM_VIDEOS:
                # Limit to NUM_VIDEOS if specified
                combinations = combinations[:NUM_VIDEOS]
                
            print(f"\n🎥 Generating {len(combinations)} videos (all combinations)...")
            
            for i, (hook_video, hook_text) in enumerate(tqdm(combinations, desc="Generating videos")):
                try:
                    # Get multiple CTA videos respecting limits
                    cta_videos = get_multiple_cta_videos(CTA_VIDEOS_FOLDER, MAX_CTA_VIDEOS, MAX_CTA_DURATION)
                    music_file = get_random_music(MUSIC_FOLDER)

                    video_number = last_number + i + 1
                    output_path = os.path.join(OUTPUT_FOLDER, f"final_video_{video_number}.mp4")

                    create_video(hook_video, hook_text, cta_videos, music_file, output_path)

                    # Save video details
                    save_video_details(
                        hook_video,
                        hook_text,
                        cta_videos,
                        music_file,
                        os.path.basename(output_path)
                    )
                    
                except Exception as e:
                    logging.error(f"Error during video creation for video {i+1}: {e}")
                    print(f"\n❌ Error creating video {i+1}: {e}")
                    continue
                    
        else:
            # Generate random combinations
            print(f"\n🎥 Generating {NUM_VIDEOS} videos...")
            for i in tqdm(range(NUM_VIDEOS), desc="Generating videos"):
                try:
                    hook_video = get_random_video(HOOK_VIDEOS_FOLDER)
                    hook_text = get_unused_hook(hooks, used_hooks)
                    cta_videos = get_multiple_cta_videos(CTA_VIDEOS_FOLDER, MAX_CTA_VIDEOS, MAX_CTA_DURATION)
                    music_file = get_random_music(MUSIC_FOLDER)

                    video_number = last_number + i + 1
                    output_path = os.path.join(OUTPUT_FOLDER, f"final_video_{video_number}.mp4")

                    create_video(hook_video, hook_text, cta_videos, music_file, output_path)

                    # Save video details
                    save_video_details(
                        hook_video,
                        hook_text,
                        cta_videos,
                        music_file,
                        os.path.basename(output_path)
                    )

                    save_used_hook(USED_HOOKS_FILE, hook_text)
                    used_hooks.add(hook_text)
                    
                except ValueError as e:
                    if "No unused hooks available" in str(e):
                        print("\n⚠️  Stopping: No more fresh hooks available!")
                        logging.info("Process stopped: All hooks have been used")
                        return
                    raise
                except Exception as e:
                    logging.error(f"Error during video creation for video {video_number}: {e}")
                    print(f"\n❌ Error creating video {video_number}: {e}")
                    continue

        end_time = time.time()
        duration = end_time - start_time
        print(f"\n✨ Process completed in {duration:.2f} seconds!")
        logging.info(f"All videos created successfully in {duration:.2f} seconds!")
        
    except Exception as e:
        print(f"\n❌ Process stopped due to error: {e}")
        logging.error(f"Process stopped due to error: {e}")

# ---- RUN SCRIPT ----
if __name__ == "__main__":
    main()
```

# Sample .env File

Let's also create a sample .env file:

```
# ElevenLabs API credentials
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE=Adam

# Alternatively, you can use a specific voice ID
# ELEVENLABS_VOICE=21m00Tcm4TlvDq8ikWAM
```

# Key Modifications Summary

1. **Generate All Combinations Toggle**:
   - Added `GENERATE_ALL_COMBINATIONS` flag at the top
   - When enabled, creates every hook text with every hook video
   - When disabled, reverts to random selection behavior

2. **ElevenLabs Integration**:
   - Added proper ElevenLabs API configuration with env variable support
   - Implemented TTS generation with `generate_elevenlabs_tts` function
   - Added toggle to enable/disable TTS with `USE_ELEVENLABS`

3. **Multiple CTA Videos**:
   - Added control variables: `MAX_CTA_VIDEOS` and `MAX_CTA_DURATION`
   - Implemented smart video selection in `get_multiple_cta_videos`
   - Added time-based limiting to stay within duration budget

4. **Additional Improvements**:
   - Enhanced audio handling to properly mix TTS, video audio, and background music
   - Improved video details tracking to handle multiple CTA videos
   - Added better error handling and recovery throughout

These changes give you flexible controls over the video generation process while maintaining the core functionality of the original script.
