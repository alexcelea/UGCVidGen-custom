import os
import random
import logging
import pandas as pd
import sys
from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip, 
    concatenate_videoclips, AudioFileClip, concatenate_audioclips,
    CompositeAudioClip, ColorClip
)
import time
from tqdm import tqdm
import numpy as np
import tempfile
import subprocess
from elevenlabs import generate, save, set_api_key
from dotenv import load_dotenv
from datetime import datetime
import requests
import json

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the configuration
from config import UGC_CONFIG, TARGET_RESOLUTION, ELEVENLABS_API_KEY, ELEVENLABS_VOICE
from scripts.utils import setup_directories, resize_video, get_random_file, position_text_in_tiktok_safe_area, visualize_safe_area

# Verify ffmpeg installation
try:
    subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
    print("✅ ffmpeg is installed and working correctly")
except (subprocess.CalledProcessError, FileNotFoundError):
    print("⚠️ WARNING: ffmpeg may not be installed or is not in PATH. This might cause audio issues.")

# Load environment variables from .env file
load_dotenv()

# ---- CONFIGURATION ----
PROJECT_NAME = UGC_CONFIG.get("project_name", "ugcReelGen")
HOOKS_CSV = UGC_CONFIG.get("hooks_file", "content/hooks.csv")
HOOK_VIDEOS_FOLDER = UGC_CONFIG.get("hooks_videos_folder", "assets/videos/hooks")
CTA_VIDEOS_FOLDER = UGC_CONFIG.get("cta_videos_folder", "assets/videos/ctas")
OUTPUT_FOLDER = UGC_CONFIG.get("output_folder", "output/ugc")
USED_HOOKS_FILE = UGC_CONFIG.get("used_hooks_file", "content/used_hooks.txt")
NUM_VIDEOS = UGC_CONFIG.get("num_videos", 1)
FONT = UGC_CONFIG.get("font", "assets/fonts/BeVietnamPro-Bold.ttf")
FONT_SIZE = UGC_CONFIG.get("font_size", 70)
TEXT_COLOR = UGC_CONFIG.get("text_color", "white")
BACKGROUND_COLOR = UGC_CONFIG.get("background_color", "black")
LOG_FILE = UGC_CONFIG.get("log_file", "output/ugc/video_creation.log")
VIDEO_LIST_FILE = UGC_CONFIG.get("video_list_file", "output/ugc/video_list.txt")
MUSIC_FOLDER = UGC_CONFIG.get("music_folder", "assets/music")
GENERATE_ALL_COMBINATIONS = UGC_CONFIG.get("generate_all_combinations", False)
MAX_CTA_VIDEOS = UGC_CONFIG.get("max_cta_videos", 3)
MAX_CTA_DURATION = UGC_CONFIG.get("max_cta_duration", 60)

# ElevenLabs configuration
USE_ELEVENLABS = True  # Set to False to disable ElevenLabs TTS
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")  # API key from .env file
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Adam")  # Voice name or ID from .env file
ELEVENLABS_MODEL = "eleven_monolingual_v1"  # Default TTS model
SAVE_TTS_FILES = True  # Set to True to save raw TTS files for debugging
TTS_FILES_FOLDER = UGC_CONFIG.get("tts_files_folder", "output/ugc/tts_files")

# ---- SETUP LOGGING ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ---- FUNCTION DEFINITIONS ----

def setup_output_folder(folder_path):
    """Ensure the output folder exists."""
    setup_directories([folder_path])

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

def get_hook_video(folder_path):
    """
    Pick a hook video from the folder using the configured selection mode.
    Uses either random selection or sequential selection based on UGC_CONFIG.
    """
    selection_mode = UGC_CONFIG.get("file_selection_mode", "random")
    
    if selection_mode == "sequential":
        # Use sequential selection
        tracking_file = UGC_CONFIG.get("sequential_tracking_file")
        from scripts.utils import get_sequential_file
        
        video_path = get_sequential_file(
            folder_path, 
            extensions=['.mp4', '.mov'],
            tracking_file=tracking_file,
            category="ugc_hook_video"
        )
        
        if video_path:
            logging.info(f"Selected hook video sequentially: {os.path.basename(video_path)}")
            return video_path
        else:
            # Fallback to random if sequential fails
            logging.warning("Sequential hook video selection failed, falling back to random")
            return get_random_video(folder_path)
    else:
        # Use random selection
        return get_random_video(folder_path)

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
    selection_mode = UGC_CONFIG.get("file_selection_mode", "random")
    
    if selection_mode == "sequential":
        return get_sequential_cta_videos(folder_path, max_count, max_duration)
    else:
        # Default to random selection
        return get_random_cta_videos(folder_path, max_count, max_duration)

def get_random_cta_videos(folder_path, max_count=MAX_CTA_VIDEOS, max_duration=MAX_CTA_DURATION):
    """Get multiple CTA videos randomly respecting max count and duration limits."""
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

def get_sequential_cta_videos(folder_path, max_count=MAX_CTA_VIDEOS, max_duration=MAX_CTA_DURATION):
    """Get multiple CTA videos sequentially respecting max count and duration limits."""
    tracking_file = UGC_CONFIG.get("sequential_tracking_file")
    from scripts.utils import get_sequential_file
    
    selected_videos = []
    total_duration = 0
    
    # Get all videos first to know how many we have
    all_videos = get_all_videos(folder_path)
    
    # Sort videos to ensure consistent ordering
    all_videos.sort()
    
    # Calculate how many videos we need to check (might need to loop around)
    num_videos = len(all_videos)
    
    # Load tracking data to find last used index
    tracking_data = {}
    if tracking_file and os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logging.warning(f"Could not load tracking file {tracking_file}, creating new")
            tracking_data = {}
    
    # Get the current index for this category
    category_key = f"ugc_cta_video:{folder_path}"
    current_index = tracking_data.get(category_key, -1)
    
    # Try to select videos, starting from the next index
    videos_checked = 0
    while len(selected_videos) < max_count and videos_checked < num_videos * 2:  # Limit to avoid infinite loop
        next_index = (current_index + 1) % num_videos
        video_path = all_videos[next_index]
        
        # Check duration
        try:
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
                
                # If it fits within our limits, add it
                if total_duration + duration <= max_duration:
                    selected_videos.append(video_path)
                    total_duration += duration
                    logging.info(f"Selected sequential CTA video {next_index+1}/{num_videos}: {os.path.basename(video_path)}")
                else:
                    logging.info(f"Skipping CTA video due to duration limit: {os.path.basename(video_path)}")
        except Exception as e:
            logging.error(f"Error checking duration for {video_path}: {e}")
        
        # Update tracking
        current_index = next_index
        videos_checked += 1
        
        # Stop if we've reached the limit
        if len(selected_videos) >= max_count:
            break
    
    # Save the last index
    tracking_data[category_key] = current_index
    
    if tracking_file:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
        with open(tracking_file, 'w') as f:
            json.dump(tracking_data, f)
    
    logging.info(f"Selected {len(selected_videos)} sequential CTA videos with total duration {total_duration:.2f}s")
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

def get_music(folder_path):
    """
    Pick a music file from the folder using the configured selection mode.
    Uses either random selection or sequential selection based on UGC_CONFIG.
    """
    selection_mode = UGC_CONFIG.get("music_selection_mode", UGC_CONFIG.get("file_selection_mode", "random"))
    
    if selection_mode == "sequential":
        # Use sequential selection with the existing music tracking file
        return get_sequential_music(folder_path)
    else:
        # Use random selection
        return get_random_music(folder_path)

def get_sequential_music(folder_path):
    """
    Get music files sequentially using the existing music_tracking.json file.
    This follows the format already being used in the project.
    """
    tracking_file = UGC_CONFIG.get("music_tracking_file")
    if not tracking_file:
        logging.warning("No music tracking file specified, falling back to random selection")
        return get_random_music(folder_path)
    
    # Ensure the music folder exists
    if not os.path.exists(folder_path):
        logging.error(f"Music folder not found: {folder_path}")
        raise FileNotFoundError(f"Music folder not found: {folder_path}")
    
    # Get all music files
    music_files = [f for f in os.listdir(folder_path) if f.endswith((".mp3", ".wav", ".m4a"))]
    if not music_files:
        logging.error(f"No music files found in {folder_path}")
        raise FileNotFoundError(f"No music files found in {folder_path}")
    
    # Sort files to ensure consistent ordering
    music_files.sort()
    
    # Get or create the tracking data
    tracking_data = {}
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.warning(f"Error reading music tracking file: {e}, creating new")
            tracking_data = {}
    
    # Get the folder key or create it if it doesn't exist
    folder_key = folder_path
    if folder_key not in tracking_data:
        tracking_data[folder_key] = []
    
    used_music = tracking_data[folder_key]
    
    # Find the next unused music file, or cycle back if all used
    for music_file in music_files:
        if music_file not in used_music:
            # Found an unused file, add it to the tracking
            used_music.append(music_file)
            tracking_data[folder_key] = used_music
            
            # Save the updated tracking data
            try:
                os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
                with open(tracking_file, 'w') as f:
                    json.dump(tracking_data, f, indent=2)
                logging.info(f"Updated music tracking file: {tracking_file}")
            except Exception as e:
                logging.error(f"Error updating music tracking file: {e}")
            
            selected_music = os.path.join(folder_path, music_file)
            logging.info(f"Selected sequential music: {music_file}")
            return selected_music
    
    # If all files have been used, clear the list and start over
    logging.info("All music files have been used, starting fresh cycle")
    if music_files:
        selected_music = music_files[0]
        tracking_data[folder_key] = [selected_music]
        
        # Save the updated tracking data
        try:
            with open(tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=2)
            logging.info(f"Reset music tracking and selected first file: {selected_music}")
        except Exception as e:
            logging.error(f"Error updating music tracking file: {e}")
            
        return os.path.join(folder_path, selected_music)
    else:
        # Fallback if something went wrong
        return get_random_music(folder_path)

def verify_audio_file(file_path):
    """Verify that an audio file contains valid audio data."""
    try:
        cmd = ['ffprobe', '-i', file_path, '-show_streams', '-select_streams', 'a', '-v', 'error']
        output = subprocess.check_output(cmd).decode('utf-8')
        if 'codec_type=audio' in output:
            size = os.path.getsize(file_path)
            logging.info(f"Audio file verified: {file_path} (size: {size} bytes)")
            return True
        else:
            logging.error(f"No audio stream found in file: {file_path}")
            return False
    except Exception as e:
        logging.error(f"Error verifying audio file {file_path}: {e}")
        return False

def check_video_has_audio(video_path):
    """Check if a video file has an audio stream using ffprobe."""
    try:
        cmd = ['ffprobe', '-i', video_path, '-show_streams', '-select_streams', 'a', '-v', 'error']
        output = subprocess.check_output(cmd).decode('utf-8')
        has_audio = 'codec_type=audio' in output
        logging.info(f"Video {video_path} has audio: {has_audio}")
        return has_audio
    except Exception as e:
        logging.error(f"Error checking audio in video {video_path}: {e}")
        return False

def generate_elevenlabs_tts(text, output_path):
    """Generate TTS audio from text using ElevenLabs and save to file."""
    try:
        # Set the API key
        set_api_key(ELEVENLABS_API_KEY)
        
        # First, try using the voice name/ID directly from config
        try:
            # Generate audio using ElevenLabs
            logging.info(f"Generating TTS with voice '{ELEVENLABS_VOICE}' and model '{ELEVENLABS_MODEL}'")
            audio = generate(
                text=text,
                voice=ELEVENLABS_VOICE,
                model=ELEVENLABS_MODEL
            )
            
            # Save the audio to file
            save(audio, output_path)
            
            # Check file size and duration
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logging.info(f"Generated TTS audio file at {output_path} (size: {file_size} bytes)")
                
                # Verify the audio file with ffmpeg
                verify_audio_file(output_path)
                
                # Check audio duration if file exists and has content
                if file_size > 0:
                    try:
                        with AudioFileClip(output_path) as audio_clip:
                            logging.info(f"TTS audio duration: {audio_clip.duration:.2f} seconds")
                    except Exception as e:
                        logging.error(f"Error checking TTS audio duration: {e}")
                else:
                    logging.error(f"Generated TTS file has zero size: {output_path}")
                    return False
            else:
                logging.error(f"TTS file was not created at {output_path}")
                return False
                
            # Save a copy of the TTS file if enabled
            if SAVE_TTS_FILES:
                setup_output_folder(TTS_FILES_FOLDER)
                import shutil
                tts_filename = f"tts_{text[:20].replace(' ', '_')}_{int(time.time())}.mp3"
                tts_file_path = os.path.join(TTS_FILES_FOLDER, tts_filename)
                shutil.copy(output_path, tts_file_path)
                logging.info(f"Saved copy of TTS file to {tts_file_path}")
            
            logging.info(f"Generated ElevenLabs TTS audio for: {text}")
            return True
            
        except Exception as voice_error:
            logging.warning(f"Could not use configured voice '{ELEVENLABS_VOICE}': {voice_error}")
            logging.info("Attempting to fetch available voices...")
            
            # If that fails, try to get the first available voice from the account
            from elevenlabs.api import Voices
            
            available_voices = Voices.from_api()
            if not available_voices:
                raise Exception("No voices found in your ElevenLabs account")
            
            # Use the first available voice
            first_voice = available_voices[0]
            logging.info(f"Using alternative voice: {first_voice.name}")
            
            # Generate with the available voice
            audio = generate(
                text=text,
                voice=first_voice.voice_id,
                model=ELEVENLABS_MODEL
            )
            
            # Save the audio to file
            save(audio, output_path)
            
            # Check file size and duration
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logging.info(f"Generated TTS audio file at {output_path} (size: {file_size} bytes)")
                
                # Verify the audio file with ffmpeg
                verify_audio_file(output_path)
                
                # Check audio duration if file exists and has content
                if file_size > 0:
                    try:
                        with AudioFileClip(output_path) as audio_clip:
                            logging.info(f"TTS audio duration: {audio_clip.duration:.2f} seconds")
                    except Exception as e:
                        logging.error(f"Error checking TTS audio duration: {e}")
                else:
                    logging.error(f"Generated TTS file has zero size: {output_path}")
                    return False
            else:
                logging.error(f"TTS file was not created at {output_path}")
                return False
                
            # Save a copy of the TTS file if enabled
            if SAVE_TTS_FILES:
                setup_output_folder(TTS_FILES_FOLDER)
                import shutil
                tts_filename = f"tts_{text[:20].replace(' ', '_')}_{int(time.time())}.mp3"
                tts_file_path = os.path.join(TTS_FILES_FOLDER, tts_filename)
                shutil.copy(output_path, tts_file_path)
                logging.info(f"Saved copy of TTS file to {tts_file_path}")
            
            logging.info(f"Generated ElevenLabs TTS audio with voice '{first_voice.name}' for: {text}")
            return True
            
    except Exception as e:
        logging.error(f"Error generating ElevenLabs TTS: {e}")
        # If ElevenLabs fails, we return False
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
        tts_file = None
        if USE_ELEVENLABS:
            print("Generating TTS with ElevenLabs...")
            tts_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            logging.info(f"Temporary TTS file path: {tts_file}")
            
            # Get the tts value from the hooks dataframe if available
            tts_text = hook_text
            try:
                # Find the hook in the hooks dataframe by text
                hooks_df = load_hooks(HOOKS_CSV)
                hook_row = hooks_df[hooks_df['text'] == hook_text]
                
                if not hook_row.empty and 'tts' in hook_row.columns and hook_row['tts'].iloc[0]:
                    tts_text = hook_row['tts'].iloc[0]
                    logging.info(f"Using TTS-specific text: {tts_text}")
                else:
                    logging.info(f"No TTS-specific text found, using original hook text")
            except Exception as e:
                logging.warning(f"Error finding TTS text: {e}. Using original hook text.")
            
            if generate_elevenlabs_tts(tts_text, tts_file):
                try:
                    # Verify audio file before loading
                    if verify_audio_file(tts_file):
                        tts_audio = AudioFileClip(tts_file)
                        logging.info(f"Loaded TTS audio with duration: {tts_audio.duration:.2f} seconds")
                    else:
                        logging.error("Failed to verify TTS audio file, skipping TTS")
                        tts_audio = None
                except Exception as e:
                    logging.error(f"Error loading TTS audio file: {e}")
                    tts_audio = None
        
        print("Loading hook video...")
        hook_clip = VideoFileClip(hook_video_path)
        hook_clip = resize_video(hook_clip, TARGET_RESOLUTION)
        logging.info(f"Hook video duration: {hook_clip.duration:.2f} seconds")
        
        # If TTS is enabled and successfully generated, make sure hook clip is long enough
        if tts_audio and tts_audio.duration > hook_clip.duration:
            # Loop the clip to match the TTS duration
            logging.info(f"Extending hook video from {hook_clip.duration:.2f}s to {tts_audio.duration:.2f}s to match TTS")
            hook_clip = hook_clip.loop(duration=tts_audio.duration)

        print("Adding text overlay...")
        # Get TikTok margin settings if enabled
        tiktok_margins = UGC_CONFIG.get("tiktok_margins", {})
        use_tiktok_margins = tiktok_margins.get("enabled", False)
        
        # Calculate text width with appropriate margins
        if use_tiktok_margins:
            horizontal_margin = tiktok_margins.get("horizontal_text_margin", 240)
        else:
            horizontal_margin = 120  # Default margin
            
        # Calculate text width with margins
        text_width = hook_clip.w - horizontal_margin
        logging.info(f"Text width will be {text_width}px (with {horizontal_margin}px margin)")
        
        # Set up text clip parameters
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
        
        # Get appropriate Y position for text with TikTok safe areas
        if use_tiktok_margins:
            # Use our custom text positioning utility for consistent text placement
            # Set position to 33% of safe area for primary hook text
            main_text = position_text_in_tiktok_safe_area(
                TextClip(**text_clip_args),
                tiktok_margins,
                TARGET_RESOLUTION,
                position_factor=0.33  # Position text 1/3 into the safe area
            ).set_duration(hook_clip.duration)
            
            # Apply the same positioning to glow effects for consistency
            glow_clips = []
            for i in range(glow_layers):
                glow_args = {**text_clip_args, 
                           "color": "black",
                           "stroke_width": 2 + i,
                           "stroke_color": "black"}
                
                glow = position_text_in_tiktok_safe_area(
                    TextClip(**glow_args),
                    tiktok_margins,
                    TARGET_RESOLUTION,
                    position_factor=0.33  # Match main text position
                ).set_duration(hook_clip.duration).set_opacity(0.2)
                
                glow_clips.append(glow)
            
            logging.info(f"Positioned hook text with TikTok safe margins at position factor: 0.33")
        else:
            # Default positioning when not using TikTok margins
            text_y_position = 350  # Default position
            logging.info(f"Using standard text position: {text_y_position}px")
            
            # Create glow layers
            glow_clips = []
            for i in range(glow_layers):
                glow = (TextClip(**{**text_clip_args, 
                                "color": "black",
                                "stroke_width": 2 + i,
                                "stroke_color": "black"})
                       .set_duration(hook_clip.duration)
                       .set_position(("center", text_y_position))
                       .set_opacity(0.2))
                glow_clips.append(glow)
                
            # Main text on top
            main_text = (TextClip(**text_clip_args)
                        .set_duration(hook_clip.duration)
                        .set_position(("center", text_y_position)))

        # Combine hook video with text overlay
        print("Combining hook and text...")
        combined_hook = CompositeVideoClip([hook_clip] + glow_clips + [main_text])
        
        # Handle audio separately to ensure TTS is preserved
        hook_with_tts = None
        hook_has_audio = hook_clip.audio is not None
        
        # Check if hook video has audio with ffprobe and MoviePy
        has_hook_audio = check_video_has_audio(hook_video_path)
        if has_hook_audio:
            if not hook_has_audio:
                logging.warning(f"Hook video has audio according to ffprobe but not MoviePy: {hook_video_path}")
            else:
                logging.info(f"Hook video has audio with duration: {hook_clip.audio.duration:.2f}s")
        else:
            logging.info(f"Hook video has no audio track: {hook_video_path}")
            
        if tts_audio:
            logging.info("Adding TTS audio to hook")
            # If hook has audio, mix it with TTS at lower volume
            if hook_has_audio:
                # Use a slightly higher volume (0.3 instead of 0.1) for better audibility
                hook_audio = hook_clip.audio.volumex(0.3) 
                combined_audio = CompositeAudioClip([hook_audio, tts_audio.volumex(1.0)])
                logging.info("Mixed hook audio with TTS")
            else:
                combined_audio = tts_audio
                logging.info("Using TTS audio alone (hook has no audio)")
            
            # Store the combined audio but don't set it to the clip yet
            hook_with_tts = combined_audio
        elif hook_has_audio:
            # If no TTS but hook has audio, preserve the hook audio
            logging.info("No TTS audio, preserving hook audio")
            hook_with_tts = hook_clip.audio.volumex(1.0)  # Full volume for hook audio
        else:
            logging.info("No TTS audio and hook has no audio")
            hook_with_tts = None

        # Load CTA videos
        print("Loading CTA videos...")
        cta_clips = []
        for cta_path in cta_video_paths:
            # First check if the video has audio using ffprobe
            has_audio = check_video_has_audio(cta_path)
            if not has_audio:
                logging.warning(f"CTA video has no audio track: {cta_path}")
            
            cta_clip = VideoFileClip(cta_path)
            cta_clip = resize_video(cta_clip, TARGET_RESOLUTION)
            
            # Double check the audio with MoviePy
            if cta_clip.audio is None:
                logging.warning(f"CTA clip has no audio according to MoviePy: {cta_path}")
            else:
                logging.info(f"CTA clip has audio with duration: {cta_clip.audio.duration:.2f}s")
            
            cta_clips.append(cta_clip)
        
        # Combine all videos (without audio for now)
        print("Creating final video...")
        final_video = concatenate_videoclips([combined_hook] + cta_clips)
        
        # Add debug visualization if enabled
        if use_tiktok_margins and tiktok_margins.get("show_debug_visualization", False):
            final_video = visualize_safe_area(final_video, tiktok_margins, TARGET_RESOLUTION)
            logging.info("Added debug visualization of TikTok safe zones")
            
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
        
        # Create final audio track by compositing all audio sources
        if hook_with_tts:
            logging.info("Creating final audio with TTS and background music")
            try:
                # Create temp clips for the CTA audio portions
                cta_audio_clips = []
                hook_duration = combined_hook.duration
                total_duration = final_video.duration
                
                # First add hook with TTS, but limit it to its duration
                hook_with_tts = hook_with_tts.subclip(0, min(hook_with_tts.duration, hook_duration))
                
                # Create a CompositeAudioClip with the hook TTS and background music
                # We need to position the TTS at the start and the music throughout
                final_audio_clips = [
                    background_music.volumex(0.4)  # Reduced background music volume for better voice clarity
                ]
                
                # Add TTS with the correct start time (0) and higher volume
                hook_with_tts = hook_with_tts.volumex(1.5)  # Boost TTS volume significantly
                hook_with_tts = hook_with_tts.set_start(0)
                final_audio_clips.append(hook_with_tts)
                
                # If there are CTA clips with audio, add them with appropriate start times
                current_time = hook_duration
                for i, cta_clip in enumerate(cta_clips):
                    if cta_clip.audio:
                        cta_audio = cta_clip.audio.volumex(0.9)  # Slightly increase CTA audio volume
                        cta_audio = cta_audio.set_start(current_time)
                        final_audio_clips.append(cta_audio)
                    current_time += cta_clip.duration
                
                # Create the composite audio
                final_audio = CompositeAudioClip(final_audio_clips)
                final_audio = final_audio.subclip(0, total_duration)
                
                # Set the final audio to the video
                final_video = final_video.set_audio(final_audio)
                logging.info(f"Successfully created final audio with TTS and background music")
                
            except Exception as e:
                logging.error(f"Error creating audio: {e}")
                # Fallback to just using the background music with higher volume
                logging.info("Fallback: Using only background music due to error")
                background_music = background_music.volumex(1.5)  # Increase background music volume significantly
                final_video = final_video.set_audio(background_music)
        else:
            # No TTS, but still include CTA audio with background music
            logging.info("No TTS audio, using background music with CTA audio")
            try:
                hook_duration = combined_hook.duration
                total_duration = final_video.duration
                
                # Start with background music
                final_audio_clips = [
                    background_music.volumex(0.6)  # Reduced background music volume to make room for hook audio
                ]
                
                # Add hook audio if available
                if hook_has_audio and hook_with_tts is not None:
                    hook_with_tts = hook_with_tts.subclip(0, min(hook_with_tts.duration, hook_duration))
                    hook_with_tts = hook_with_tts.set_start(0) 
                    final_audio_clips.append(hook_with_tts)
                    logging.info("Added hook audio to final composition")
                
                # Add CTA clips audio with appropriate start times
                current_time = hook_duration
                has_cta_audio = False
                for i, cta_clip in enumerate(cta_clips):
                    if cta_clip.audio:
                        cta_audio = cta_clip.audio.volumex(1.0)  # Full volume for CTA audio
                        cta_audio = cta_audio.set_start(current_time)
                        final_audio_clips.append(cta_audio)
                        has_cta_audio = True
                    current_time += cta_clip.duration
                
                # Create the composite audio
                final_audio = CompositeAudioClip(final_audio_clips)
                final_audio = final_audio.subclip(0, total_duration)
                
                # Set the final audio to the video
                final_video = final_video.set_audio(final_audio)
                
                if has_cta_audio:
                    logging.info("Successfully included CTA audio with background music")
                else:
                    logging.info("No CTA audio found, using only background music and hook audio")
                
            except Exception as e:
                logging.error(f"Error creating audio without TTS: {e}")
                # Fallback to just using the background music
                logging.info("Fallback: Using only background music due to error")
                background_music = background_music.volumex(1.5)  # Increase background music volume
                final_video = final_video.set_audio(background_music)

        # Verify background music file
        if not verify_audio_file(music_path):
            logging.error(f"Background music file failed verification: {music_path}")
            # Try alternative fallback method
            try:
                cmd = ['ffmpeg', '-i', music_path, '-c:a', 'copy', '-f', 'mp3', '-y', 'temp_music.mp3']
                subprocess.check_call(cmd)
                if os.path.exists('temp_music.mp3') and os.path.getsize('temp_music.mp3') > 0:
                    music_path = 'temp_music.mp3'
                    logging.info(f"Using converted music file: {music_path}")
            except Exception as e:
                logging.error(f"Error converting music file: {e}")

        print(f"Writing final video to {output_path}...")
        
        # Specify audio codec and bitrate explicitly to ensure audio is properly encoded
        try:
            final_video.write_videofile(
                output_path, 
                fps=24, 
                codec="libx264",
                audio_codec="aac",  # Specify a more compatible audio codec
                audio_bitrate="192k",  # Higher audio bitrate for better quality
                preset='medium',
                verbose=False,
                logger=None
            )
            logging.info(f"Successfully wrote video file with audio: {output_path}")
            
            # Verify the final video has audio
            if not verify_audio_file(output_path):
                logging.error(f"Final video does not contain audio: {output_path}")
                # Try to fix the video with ffmpeg directly
                try:
                    temp_output = f"temp_{os.path.basename(output_path)}"
                    if hook_with_tts:
                        logging.info(f"Attempting to fix audio with ffmpeg directly...")
                        # Create a version with audio using ffmpeg directly
                        cmd = [
                            'ffmpeg', '-i', output_path, '-i', tts_file, '-i', music_path,
                            '-filter_complex', '[1:a]volume=1.5[a1];[2:a]volume=0.5[a2];[a1][a2]amix=inputs=2:duration=longest[a]',
                            '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                            '-y', temp_output
                        ]
                        subprocess.check_call(cmd)
                        if os.path.exists(temp_output) and verify_audio_file(temp_output):
                            # Replace the original with the fixed version
                            os.remove(output_path)
                            os.rename(temp_output, output_path)
                            logging.info(f"Successfully fixed audio using ffmpeg directly: {output_path}")
                    else:
                        # For no-TTS case, we might need to extract and preserve CTA audio
                        logging.info(f"Attempting to fix audio (preserving CTA audio) with ffmpeg directly...")
                        
                        # Check if there are CTA videos with audio that we need to consider
                        has_cta_audio = any(verify_audio_file(cta_path) for cta_path in cta_video_paths)
                        
                        if has_cta_audio:
                            # This is more complex as we'd need to extract CTA audio and position it correctly
                            # Since this requires knowledge of the CTA start times and durations, 
                            # we'll just log that manual ffmpeg work would be needed
                            logging.info("CTA audio detected but direct ffmpeg fix is limited. Apply the moviepy fix instead.")
                            # Just add background music as fallback
                            cmd = [
                                'ffmpeg', '-i', output_path, '-i', music_path,
                                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                                '-y', temp_output
                            ]
                            subprocess.check_call(cmd)
                            if os.path.exists(temp_output) and verify_audio_file(temp_output):
                                # Replace the original with the fixed version
                                os.remove(output_path)
                                os.rename(temp_output, output_path)
                                logging.info(f"Added background music as fallback: {output_path}")
                        else:
                            # Just add background music
                            cmd = [
                                'ffmpeg', '-i', output_path, '-i', music_path,
                                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                                '-y', temp_output
                            ]
                            subprocess.check_call(cmd)
                            if os.path.exists(temp_output) and verify_audio_file(temp_output):
                                # Replace the original with the fixed version
                                os.remove(output_path)
                                os.rename(temp_output, output_path)
                                logging.info(f"Successfully fixed audio using ffmpeg directly: {output_path}")
                except Exception as e:
                    logging.error(f"Error fixing audio with ffmpeg: {e}")
        except Exception as e:
            logging.error(f"Error writing video file: {e}")
            # Try to fall back to writing with default settings
            try:
                logging.info("Falling back to default write_videofile settings")
                final_video.write_videofile(output_path, verbose=False, logger=None)
            except Exception as e2:
                logging.error(f"Fallback write also failed: {e2}")
                raise
        
        # Clean up
        hook_clip.close()
        for clip in cta_clips:
            clip.close()
        background_music.close()
        final_video.close()
        
        # Clean up temp TTS file if it exists
        if tts_audio:
            tts_audio.close()
            if tts_file and os.path.exists(tts_file) and not SAVE_TTS_FILES:
                os.unlink(tts_file)
                logging.info(f"Cleaned up temporary TTS file: {tts_file}")
            elif SAVE_TTS_FILES:
                logging.info(f"Kept temporary TTS file for debugging: {tts_file}")
        
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
                    
                    # Try to match new format first (YYYYMMDD_PROJECT_NAME_NUM_...)
                    import re
                    # This pattern matches a 3-digit number after a date and project name
                    # It works for both camelCase and snake_case hooks
                    match = re.search(r'_(\d{3})_h\d+_', final_video)
                    if match:
                        num = int(match.group(1))
                        numbers.append(num)
                        continue
                        
                    # Try old format (final_video_N.mp4)
                    if "final_video_" in final_video:
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

def create_descriptive_filename(hook_id, hook_text, hook_video_path, cta_video_paths, video_number):
    """Create a descriptive filename that includes elements from the hook text and videos used."""
    # Get base names without extensions
    hook_video_name = os.path.splitext(os.path.basename(hook_video_path))[0]
    
    # Process hook text: keep first few words, convert to camelCase
    import re
    from datetime import datetime
    
    # Clean up special characters first
    cleaned_text = re.sub(r'[^\w\s-]', '', hook_text)
    
    # Split into words and limit to first few
    words = cleaned_text.split()
    selected_words = words[:3] if len(words) > 3 else words
    
    # Convert to camelCase
    if selected_words:
        # First word lowercase
        selected_words[0] = selected_words[0].lower()
        # Rest with first letter capitalized
        for i in range(1, len(selected_words)):
            selected_words[i] = selected_words[i].capitalize() if selected_words[i] else ''
        
        # Join without spaces
        hook_summary = ''.join(selected_words)
    else:
        hook_summary = 'emptyHook'
    
    # Clean up hook video name
    hook_video_name = re.sub(r'\s+', '_', hook_video_name)  # Replace spaces with underscores
    
    # Add CTA reference
    cta_count = len(cta_video_paths)
    
    # Add date in format YYYYMMDD
    today = datetime.now().strftime("%Y%m%d")
    
    # Combine components - format: YYYYMMDD_PROJECT_NAME_NUM_hID_hooksummary_hookvideo_NUMcta.mp4
    filename = f"{today}_{PROJECT_NAME}_{video_number:03d}_h{hook_id}_{hook_summary}_{hook_video_name}_{cta_count}cta.mp4"
    
    # Ensure the filename isn't too long
    if len(filename) > 100:
        # If we need to truncate, keep the camelCase format 
        # but truncate to 30 characters
        hook_summary = hook_summary[:30]
        filename = f"{today}_{PROJECT_NAME}_{video_number:03d}_h{hook_id}_{hook_summary}_{hook_video_name}_{cta_count}cta.mp4"
    
    return filename

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
    """
    Main script to automate video creation.
    
    File selection modes:
    - Random: Selects hook videos, CTA videos, and music randomly (default)
    - Sequential: Selects assets in sequential order, cycling through all available files
      
    To enable sequential selection for all assets, set "file_selection_mode": "sequential" in UGC_CONFIG in config.py.
    
    Music selection can be controlled separately:
    - Set "music_selection_mode": "sequential" to use music sequentially even with random videos
    - Set "music_selection_mode": "random" to use random music even with sequential videos
    
    Sequential selection for videos uses the tracking file at "sequential_tracking_file" (default: output/ugc/sequential_tracking.json).
    Sequential selection for music uses the existing tracking file at "music_tracking_file" (default: output/music_tracking.json).
    """
    start_time = time.time()
    
    print("\n🎬 Starting UGC Reel Generator...")
    logging.info("Starting video generation process")
    
    try:
        # Ensure all required directories exist
        setup_directories([
            OUTPUT_FOLDER,
            TTS_FILES_FOLDER,
            os.path.dirname(LOG_FILE),
            os.path.dirname(VIDEO_LIST_FILE)
        ])
        
        # Get last video number
        last_number = get_last_video_number()
        print(f"📝 Last video number: {last_number}")
        
        # Load hooks
        hooks = load_hooks(HOOKS_CSV)
        print(f"📝 Loaded {len(hooks)} hooks from {HOOKS_CSV}")

        # Check if hook videos directory exists
        if not os.path.exists(HOOK_VIDEOS_FOLDER):
            error_msg = f"Folder not found: {HOOK_VIDEOS_FOLDER}"
            print(f"\n❌ Process stopped due to error: {error_msg}")
            logging.error(f"Process stopped due to error: {error_msg}")
            return
            
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
                hook_id = hook_data.id
                hook_tts = hook_data.tts if hasattr(hook_data, 'tts') else hook_text  # Get TTS text if available
                for hook_video in hook_videos:
                    combinations.append((hook_video, hook_id, hook_text))
            
            if NUM_VIDEOS > 0 and len(combinations) > NUM_VIDEOS:
                # Limit to NUM_VIDEOS if specified
                combinations = combinations[:NUM_VIDEOS]
                
            print(f"\n🎥 Generating {len(combinations)} videos (all combinations)...")
            
            for i, (hook_video, hook_id, hook_text) in enumerate(tqdm(combinations, desc="Generating videos")):
                try:
                    # Get multiple CTA videos respecting limits
                    cta_videos = get_multiple_cta_videos(CTA_VIDEOS_FOLDER, MAX_CTA_VIDEOS, MAX_CTA_DURATION)
                    music_file = get_music(MUSIC_FOLDER)

                    video_number = last_number + i + 1
                    
                    # Create descriptive filename
                    filename = create_descriptive_filename(hook_id, hook_text, hook_video, cta_videos, video_number)
                    output_path = os.path.join(OUTPUT_FOLDER, filename)

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
                    hook_video = get_hook_video(HOOK_VIDEOS_FOLDER)
                    # Get unused hook with ID
                    unused_hooks = hooks[~hooks["text"].isin(used_hooks)]
                    if unused_hooks.empty:
                        raise ValueError("No unused hooks available.")
                    selected_hook = unused_hooks.sample(1).iloc[0]
                    hook_text = selected_hook["text"]
                    hook_id = selected_hook["id"]
                    
                    cta_videos = get_multiple_cta_videos(CTA_VIDEOS_FOLDER, MAX_CTA_VIDEOS, MAX_CTA_DURATION)
                    music_file = get_music(MUSIC_FOLDER)

                    video_number = last_number + i + 1
                    
                    # Create descriptive filename
                    filename = create_descriptive_filename(hook_id, hook_text, hook_video, cta_videos, video_number)
                    output_path = os.path.join(OUTPUT_FOLDER, filename)

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