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
import csv

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import STORY_CONFIG, TARGET_RESOLUTION
from scripts.utils import setup_directories, load_csv, resize_video, get_random_file, position_text_in_tiktok_safe_area, visualize_safe_area

def setup_logging():
    """Set up logging configuration"""
    os.makedirs(os.path.dirname(STORY_CONFIG["log_file"]), exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Set up console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    # Set up file handler with a more minimal WARNING level
    file_handler = logging.FileHandler(STORY_CONFIG["log_file"])
    file_handler.setLevel(logging.WARNING)  # Only log warnings and errors to file
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logging.info("Logging initialized: INFO level to console, WARNING level to log file")

def segment_story(story_text, max_chars=None):
    """
    Break a story into segments based on configuration settings.
    
    Priorities:
    1. Split by paragraph breaks (\n) if use_paragraphs_as_segments is True
    2. Otherwise use one_sentence_per_segment or combined approach
    """
    if max_chars is None:
        max_chars = STORY_CONFIG.get("max_chars_per_segment", 200)
    
    # Get minimum segment length setting
    min_segment_length = STORY_CONFIG.get("minimum_segment_length", 0)
    
    # Debug: Print a sample of the story text to see if it contains newlines
    sample_text = story_text[:100]  # First 100 chars
    logging.info("Debug - Sample text: '%s'", sample_text)
    newline_count = story_text.count('\n')
    logging.info("Debug - Contains newlines: %d", newline_count)
    
    # Check if paragraph-based segmentation is enabled
    use_paragraphs = STORY_CONFIG.get("use_paragraphs_as_segments", True)
    
    segments = []
    
    # Check for actual newlines in the text
    if use_paragraphs and '\n' in story_text:
        logging.info(f"Using paragraph-based segmentation")
        # Replace any consecutive newlines with single ones and then split
        paragraphs = story_text.replace('\n\n', '\n').split('\n')
        logging.info(f"Found {len(paragraphs)} paragraphs")
        
        # Debug each paragraph
        for i, p in enumerate(paragraphs):
            logging.info(f"Raw paragraph {i+1}: '{p[:50]}...' [{len(p)} chars]")
        
        # Filter out empty paragraphs and process each one
        filtered_paragraphs = [p.strip() for p in paragraphs if p.strip()]
        logging.info(f"After filtering: {len(filtered_paragraphs)} non-empty paragraphs")
        
        # Handle minimum segment length by combining short paragraphs
        combined_paragraphs = []
        current_paragraph = ""
        
        for i, paragraph in enumerate(filtered_paragraphs):
            # If the paragraph is too short and not the last one
            if len(paragraph) < min_segment_length and i < len(filtered_paragraphs) - 1:
                logging.info(f"Paragraph {i+1} is too short ({len(paragraph)} chars), combining with next")
                # If we already have content in current_paragraph, append this to it
                if current_paragraph:
                    current_paragraph += " " + paragraph
                else:
                    current_paragraph = paragraph
            # If the paragraph is too short and it's the last one
            elif len(paragraph) < min_segment_length and i == len(filtered_paragraphs) - 1:
                logging.info(f"Last paragraph is too short ({len(paragraph)} chars), combining with previous")
                # If we have a previous combined paragraph, add this to it
                if current_paragraph:
                    current_paragraph += " " + paragraph
                    combined_paragraphs.append(current_paragraph)
                # Otherwise add it as is (even if it's short)
                else:
                    combined_paragraphs.append(paragraph)
            # If the paragraph is long enough
            else:
                # If we have collected content in current_paragraph, add it first
                if current_paragraph:
                    combined_paragraphs.append(current_paragraph)
                    current_paragraph = ""
                
                # Then add the current paragraph
                combined_paragraphs.append(paragraph)
        
        # Add any remaining content
        if current_paragraph:
            combined_paragraphs.append(current_paragraph)
        
        logging.info(f"After combining short paragraphs: {len(combined_paragraphs)} segments")
        
        # Debug each combined paragraph
        for i, p in enumerate(combined_paragraphs):
            logging.info(f"Combined paragraph {i+1}: '{p[:50]}...' [{len(p)} chars]")
        
        # Process each combined paragraph
        for i, paragraph in enumerate(combined_paragraphs):
            if len(paragraph) <= max_chars:
                segments.append(paragraph)
                logging.info(f"Paragraph {i+1} added as segment: '{paragraph[:30]}...'")
            else:
                # Paragraph is too long, need further segmentation
                # Use sentence or combined approach based on config
                one_sentence_per_segment = STORY_CONFIG.get("one_sentence_per_segment", False)
                if one_sentence_per_segment:
                    sub_segments = segment_by_sentences(paragraph, max_chars)
                else:
                    sub_segments = segment_by_chars(paragraph, max_chars)
                segments.extend(sub_segments)
                logging.info(f"Paragraph {i+1} was split into {len(sub_segments)} sub-segments")
    else:
        # No paragraphs or paragraph segmentation disabled
        if '\n' not in story_text:
            logging.info("No paragraph breaks (\\n) found in text, using regular segmentation")
        else:
            logging.info("Paragraph segmentation disabled, using regular segmentation")
            
        # Use standard segmentation approach
        one_sentence_per_segment = STORY_CONFIG.get("one_sentence_per_segment", False)
        if one_sentence_per_segment:
            segments = segment_by_sentences(story_text, max_chars)
        else:
            segments = segment_by_chars(story_text, max_chars)
    
    logging.info(f"Total segments created: {len(segments)}")
    # Debug each segment
    for i, seg in enumerate(segments):
        logging.info(f"Final segment {i+1}: '{seg[:50]}...' [{len(seg)} chars]")
    
    return segments

def segment_by_sentences(text, max_chars):
    """Split text by sentences, respecting max characters"""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    
    for sentence in sentences:
        if len(sentence) <= max_chars:
            result.append(sentence)
        else:
            # Break long sentences into smaller chunks
            word_segments = segment_by_chars(sentence, max_chars)
            result.extend(word_segments)
    
    return result

def segment_by_chars(text, max_chars):
    """Split text by character count, trying to preserve words"""
    words = text.split()
    result = []
    current = ""
    
    for word in words:
        test_word_addition = current + (" " if current else "") + word
        
        if len(test_word_addition) <= max_chars:
            current = test_word_addition
        else:
            if current:
                result.append(current)
            current = word
    
    if current:
        result.append(current)
    
    return result

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
    
    # Debug story data
    if 'story_text' in story_data:
        text_length = len(story_data['story_text'])
        logging.info("Debug - Story text length in create_story_video: %d", text_length)
        logging.info("Debug - First 50 chars: '%s'...", story_data['story_text'][:50])
        logging.info("Debug - Newline count: %d", story_data['story_text'].count('\n'))
        
        # Check if story_text needs escaping
        if '\\n' in story_data['story_text']:
            logging.info("Debug - Found literal \\n in story_text, replacing...")
            story_data['story_text'] = story_data['story_text'].replace('\\n', '\n')
    
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
    
    # Get TikTok margin settings if enabled
    tiktok_margins = STORY_CONFIG.get("tiktok_margins", {})
    use_tiktok_margins = tiktok_margins.get("enabled", False)
    
    # Calculate text width with appropriate margins
    if use_tiktok_margins:
        horizontal_margin = tiktok_margins.get("horizontal_text_margin", 240)
    else:
        horizontal_margin = 120  # Default fallback margin
    
    logging.info(f"Using horizontal margin: {horizontal_margin}px")
    
    title_clip = None
    title_duration = 0
    
    if show_title and story_data.get("title", "").strip():
        # Get title duration from config
        title_duration = STORY_CONFIG.get("title_duration", 3.0)
        
        logging.info(f"Title width will be: {TARGET_RESOLUTION[0] - horizontal_margin}px (with {horizontal_margin}px margin)")
        
        # Create title clip
        title_clip = TextClip(
            txt=story_data["title"],
            fontsize=STORY_CONFIG["heading_font_size"],
            color=STORY_CONFIG["text_color"],
            font=STORY_CONFIG["font"],
            method='caption',
            size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
            align='center',
            stroke_color="black",
            stroke_width=2
        ).set_duration(title_duration)
        
        # Set title position from config with TikTok-safe margins if enabled
        if use_tiktok_margins:
            # Position title near the top of the safe area (approximately 20% into safe area)
            title_clip = position_text_in_tiktok_safe_area(
                title_clip, 
                tiktok_margins, 
                TARGET_RESOLUTION, 
                position_factor=0.15  # Position title 15% into the safe area
            )
            logging.info(f"Positioned title with TikTok safe margins at position factor: 0.15")
        else:
            title_position_y = STORY_CONFIG.get("title_position_y", 350)
            if title_position_y is None:
                title_position_y = 350
            logging.info(f"Using standard title position y: {title_position_y}px")
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
    
    # Process segments with proper positioning
    fade_duration = STORY_CONFIG.get("fade_duration", 0.5)
    
    for i, segment in enumerate(story_segments):
        segment_duration = segment_durations[i]
        
        segment_clip = TextClip(
            txt=segment,
            fontsize=STORY_CONFIG["body_font_size"],
            color=STORY_CONFIG["text_color"],
            font=STORY_CONFIG["font"],
            method='caption',
            size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
            align='center',
            stroke_color="black",
            stroke_width=1
        ).set_duration(segment_duration)
        
        # Position segment with TikTok-safe margins if enabled
        if use_tiktok_margins:
            segment_clip = position_text_in_tiktok_safe_area(
                segment_clip, 
                tiktok_margins, 
                TARGET_RESOLUTION,
                position_factor=0.33  # Position text 1/3 into the safe area
            )
            logging.info(f"Positioned segment {i+1} with TikTok safe margins at position factor: 0.33")
        else:
            segment_position_y = STORY_CONFIG.get("segment_position_y", 800)
            if segment_position_y is None:
                segment_position_y = 800
            segment_clip = segment_clip.set_position(("center", segment_position_y))
            logging.info(f"Using standard segment position y: {segment_position_y}px")
        
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
    
    # Add debug visualization if enabled
    if use_tiktok_margins and tiktok_margins.get("show_debug_visualization", False):
        final_video = visualize_safe_area(final_video, tiktok_margins, TARGET_RESOLUTION)
        logging.info("Added debug visualization of TikTok safe zones")
    
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
    
    # After successful video creation, write tracking info to a simple CSV
    tracking_file = os.path.join(STORY_CONFIG["output_folder"], "story_tracking.csv")
    
    # Get just the filenames without full paths
    bg_filename = os.path.basename(background_path)
    music_filename = os.path.basename(music_path)
    output_filename = os.path.basename(output_path)
    
    # Write a CSV row with key information
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if header needs to be written
    write_header = not os.path.exists(tracking_file) or os.path.getsize(tracking_file) == 0
    
    with open(tracking_file, "a", newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "story_id", "story_title", "output_file", "background_file", "music_file"])
        
        writer.writerow([
            timestamp,
            story_data.get('id', 'unknown'),
            story_data.get('title', 'Untitled'),
            output_filename,
            bg_filename,
            music_filename
        ])

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