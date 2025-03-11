#!/usr/bin/env python3
"""
Story Generator - Creates text-based story videos with captions over background videos
"""

import os
import sys
import logging
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip
import argparse

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import STORY_CONFIG, TARGET_RESOLUTION
from scripts.utils import setup_directories, load_csv, resize_video, get_random_file

def setup_logging():
    """Set up logging configuration"""
    os.makedirs(os.path.dirname(STORY_CONFIG["log_file"]), exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(STORY_CONFIG["log_file"]),
            logging.StreamHandler()
        ]
    )

def segment_story(story_text, max_chars=None):
    """
    Break a story into segments based on configuration settings.
    
    If one_sentence_per_segment is True, each sentence will be its own segment (up to max_chars).
    If False, sentences will be combined to approach max_chars limit.
    """
    if max_chars is None:
        max_chars = STORY_CONFIG.get("max_chars_per_segment", 200)
    
    # Get segmentation style from config
    one_sentence_per_segment = STORY_CONFIG.get("one_sentence_per_segment", False)
    
    # First split by sentences
    import re
    sentences = re.split(r'(?<=[.!?])\s+', story_text)
    
    segments = []
    
    if one_sentence_per_segment:
        # Style 1: One sentence per segment (original behavior)
        for sentence in sentences:
            # If sentence is short enough, add it as a segment
            if len(sentence) <= max_chars:
                segments.append(sentence)
            else:
                # Otherwise split the sentence by words
                words = sentence.split()
                current_segment = ""
                
                for word in words:
                    test_word_addition = current_segment + (" " if current_segment else "") + word
                    
                    if len(test_word_addition) <= max_chars:
                        current_segment = test_word_addition
                    else:
                        segments.append(current_segment)
                        current_segment = word
                
                # Add the last segment if not empty
                if current_segment:
                    segments.append(current_segment)
    else:
        # Style 2: Combine sentences up to max_chars (new behavior)
        current_segment = ""
        
        for sentence in sentences:
            # Test if adding this sentence would exceed the limit
            test_segment = current_segment + (" " if current_segment else "") + sentence
            
            if len(test_segment) <= max_chars:
                # Add to current segment
                current_segment = test_segment
            else:
                # Current segment is full, add it to segments
                if current_segment:
                    segments.append(current_segment)
                
                # Is this sentence itself too long?
                if len(sentence) <= max_chars:
                    current_segment = sentence
                else:
                    # Need to split the long sentence by words
                    words = sentence.split()
                    current_segment = ""
                    
                    for word in words:
                        test_word_addition = current_segment + (" " if current_segment else "") + word
                        
                        if len(test_word_addition) <= max_chars:
                            current_segment = test_word_addition
                        else:
                            segments.append(current_segment)
                            current_segment = word
        
        # Don't forget the last segment
        if current_segment:
            segments.append(current_segment)
    
    return segments

def calculate_segment_duration(segment, wpm=None):
    """Calculate appropriate duration based on word count and reading speed"""
    if wpm is None:
        wpm = STORY_CONFIG.get("words_per_minute", 180)
    
    word_count = len(segment.split())
    duration = (word_count / wpm) * 60  # Convert to seconds
    
    # Apply min/max constraints
    min_duration = STORY_CONFIG.get("min_segment_duration", 3)
    max_duration = STORY_CONFIG.get("max_segment_duration", 8)
    
    return max(min_duration, min(duration, max_duration))

def create_story_video(story_data, background_path, music_path, output_path):
    """Create a video with storytelling text overlaid on background"""
    logging.info(f"Creating story video: {story_data.get('title', 'Untitled')}")
    
    # Load background video and resize
    background = VideoFileClip(background_path)
    background = resize_video(background, TARGET_RESOLUTION)
    
    # Determine if we should show the title
    # Priority: 1. show_title flag if present, 2. check if title exists and isn't empty
    if "show_title" in story_data:
        # Explicit flag exists, use it
        show_title = story_data.get("show_title", "").lower() in ["true", "yes", "1"]
    else:
        # Otherwise, check if title exists and global setting
        global_title_setting = STORY_CONFIG.get("show_title_by_default", True)
        has_title = bool(story_data.get("title", "").strip())
        show_title = has_title and global_title_setting
    
    title_clip = None
    title_duration = 0
    
    if show_title and story_data.get("title", "").strip():
        # Get title duration from config
        title_duration = STORY_CONFIG.get("title_duration", 3.0)
        
        # Create title clip
        title_clip = TextClip(
            txt=story_data["title"],
            fontsize=STORY_CONFIG["heading_font_size"],
            color=STORY_CONFIG["text_color"],
            font=STORY_CONFIG["font"],
            method='caption',
            size=(TARGET_RESOLUTION[0] - 120, None),
            align='center',
            stroke_color="black",
            stroke_width=2
        ).set_duration(title_duration)
        
        # Set title position from config
        title_position_y = STORY_CONFIG.get("title_position_y", 200)
        title_clip = title_clip.set_position(("center", title_position_y))
        
        # Add fade in/out effects to title
        fade_duration = STORY_CONFIG.get("fade_duration", 0.5)
        title_clip = title_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
    
    # Break story into segments
    story_segments = segment_story(story_data["story_text"])
    
    # Calculate duration for each segment based on content
    segment_durations = [calculate_segment_duration(segment) for segment in story_segments]
    total_needed_duration = sum(segment_durations)
    
    # Calculate the total video duration required
    total_video_duration = title_duration + total_needed_duration
    
    # Create a looped background video if needed
    if total_video_duration > background.duration:
        from moviepy.editor import concatenate_videoclips
        # Calculate how many loops we need
        loops_needed = int(total_video_duration / background.duration) + 1
        background_loops = [background] * loops_needed
        looped_background = concatenate_videoclips(background_loops)
        # Trim to exact duration needed
        background = looped_background.subclip(0, total_video_duration)
    else:
        # If background is already long enough, just trim it to what we need
        background = background.subclip(0, total_video_duration)
    
    # Create a dark overlay for better text contrast
    overlay = ColorClip(TARGET_RESOLUTION, col=(0, 0, 0))
    overlay = overlay.set_opacity(STORY_CONFIG["overlay_opacity"])
    overlay = overlay.set_duration(background.duration)
    
    # Combine background with overlay
    base = CompositeVideoClip([background, overlay])
    
    # Create clip for each segment
    segment_clips = []
    current_time = title_duration  # Start after title (or at 0 if no title)
    
    segment_position_y = STORY_CONFIG.get("segment_position_y", 500)
    fade_duration = STORY_CONFIG.get("fade_duration", 0.5)
    
    for i, segment in enumerate(story_segments):
        segment_duration = segment_durations[i]
        
        segment_clip = TextClip(
            txt=segment,
            fontsize=STORY_CONFIG["body_font_size"],
            color=STORY_CONFIG["text_color"],
            font=STORY_CONFIG["font"],
            method='caption',
            size=(TARGET_RESOLUTION[0] - 120, None),
            align='center',
            stroke_color="black",
            stroke_width=1
        ).set_duration(segment_duration)
        
        segment_clip = segment_clip.set_position(("center", segment_position_y))
        segment_clip = segment_clip.set_start(current_time)
        
        # Add fade in/out effects
        segment_clip = segment_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
        
        segment_clips.append(segment_clip)
        current_time += segment_duration
    
    # Combine everything
    all_clips = [base]
    if title_clip:
        all_clips.append(title_clip)
    all_clips.extend(segment_clips)
    
    final_video = CompositeVideoClip(all_clips)
    
    # Add music
    music = AudioFileClip(music_path)
    if music.duration < final_video.duration:
        # Loop music to match video duration
        from moviepy.editor import concatenate_audioclips
        loops_needed = int(final_video.duration / music.duration) + 1
        music_list = [music] * loops_needed
        music = concatenate_audioclips(music_list)
    
    # Trim music to match video duration and set volume
    music = music.subclip(0, final_video.duration).volumex(0.3)
    
    # Add music to video
    final_video = final_video.set_audio(music)
    
    # Write the final video
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        threads=4
    )
    
    logging.info(f"Story video created: {output_path}")

def main():
    """Main entry point for story video generator"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate story videos')
    parser.add_argument('--id', type=str, help='Specific story ID to generate. Can provide multiple IDs separated by commas.')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Ensure directories exist
    setup_directories([STORY_CONFIG["output_folder"]])
    
    # Load stories data
    stories = load_csv(STORY_CONFIG["stories_file"])
    
    if not stories:
        logging.error(f"No stories found in {STORY_CONFIG['stories_file']}")
        return
    
    # Filter stories by ID if specified
    stories_to_generate = []
    if args.id:
        requested_ids = [id.strip() for id in args.id.split(',')]
        for story in stories:
            if story.get('id') in requested_ids:
                stories_to_generate.append(story)
        if not stories_to_generate:
            logging.error(f"No stories found with requested IDs: {args.id}")
            return
    else:
        # Get a random story if no ID specified
        stories_to_generate = [random.choice(stories)]
    
    # Generate each requested story
    for story in stories_to_generate:
        logging.info(f"Generating story ID: {story.get('id')}")
        
        # Check if background theme folder exists
        theme = story.get("background_theme", "").lower()
        theme_dir = os.path.join(STORY_CONFIG["background_videos_folder"], theme)
        
        # Get a background video based on theme if possible
        if os.path.exists(theme_dir) and os.path.isdir(theme_dir):
            background_path = get_random_file(theme_dir, ['.mp4', '.mov'])
            if not background_path:
                # Fallback to main backgrounds directory
                background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
        else:
            # Use main backgrounds directory
            background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
        
        if not background_path:
            logging.error("No background videos found. Please add videos to the backgrounds directory.")
            continue
        
        # Check if music mood folder exists
        mood = story.get("music_mood", "").lower()
        mood_dir = os.path.join(STORY_CONFIG["music_folder"], mood)
        
        # Get music based on mood if possible
        if os.path.exists(mood_dir) and os.path.isdir(mood_dir):
            music_path = get_random_file(mood_dir, ['.mp3', '.wav', '.m4a'])
            if not music_path:
                # Fallback to main music directory
                music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
        else:
            # Use main music directory
            music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
        
        if not music_path:
            logging.error("No music files found. Please add music to the music directory.")
            continue
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = story.get('title', f"Story_{story['id']}").replace(' ', '_').replace('"', '').replace("'", "")[:20]
        output_path = os.path.join(
            STORY_CONFIG["output_folder"],
            f"{timestamp}_story_{story['id']}_{safe_title}.mp4"
        )
        
        # Create the story video
        create_story_video(story, background_path, music_path, output_path)
        
        print(f"✅ Story video created: {output_path}")

if __name__ == "__main__":
    main() 