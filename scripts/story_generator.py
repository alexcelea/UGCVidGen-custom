#!/usr/bin/env python3
"""
Story Generator - Creates text-based story videos with captions over background videos
"""

import os
import sys
import logging
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip, concatenate_videoclips
import argparse
import csv
import re
import numpy as np
from functools import partial

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import STORY_CONFIG, TARGET_RESOLUTION
from scripts.utils import setup_directories, load_csv, resize_video, get_random_file, position_text_in_tiktok_safe_area, visualize_safe_area, hex_to_rgb

# Project name for filenames
PROJECT_NAME = "StoryGen"

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
    
    # Apply zoom effect to background if enabled
    background_effects = STORY_CONFIG.get("background_effects", {})
    zoom_settings = background_effects.get("zoom", {})
    
    if zoom_settings.get("enabled", False):
        zoom_factor = zoom_settings.get("factor", 1.05)
        zoom_direction = zoom_settings.get("direction", "in")
        logging.info(f"Applying {zoom_direction} zoom effect with factor {zoom_factor}")
        background = add_zoom_effect(background, zoom_factor, zoom_direction)
    
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
    
    # Get text effect settings
    text_effects = STORY_CONFIG.get("text_effects", {})
    text_effects_enabled = text_effects.get("enabled", True)
    
    if show_title and story_data.get("title", "").strip():
        # Get title duration from config
        title_duration = STORY_CONFIG.get("title_duration", 3.0)
        
        logging.info(f"Title width will be: {TARGET_RESOLUTION[0] - horizontal_margin}px (with {horizontal_margin}px margin)")
        
        # Get title-specific styling
        title_color = STORY_CONFIG.get("title_color", STORY_CONFIG.get("text_color", "white"))
        title_font = STORY_CONFIG.get("title_font", STORY_CONFIG.get("font"))
        title_fontsize = STORY_CONFIG.get("heading_font_size", 80)
        title_stroke_width = text_effects.get("title_stroke_width", 2)
        
        # Create title with or without shadow effects
        if text_effects_enabled and text_effects.get("title_shadow", True):
            shadow_color = text_effects.get("title_shadow_color", "#000000")
            shadow_offset = text_effects.get("title_shadow_offset", 3)
            
            # Create title clip with shadow
            raw_title_clip = create_text_with_shadow(
                text=story_data["title"],
                fontsize=title_fontsize,
                color=title_color,
                font=title_font,
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                shadow_color=shadow_color,
                shadow_offset=shadow_offset,
                stroke_width=title_stroke_width
            ).set_duration(title_duration)
        else:
            # Create title clip without shadow effect
            raw_title_clip = TextClip(
                txt=story_data["title"],
                fontsize=title_fontsize,
                color=title_color,
                font=title_font,
                method='caption',
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                align='center',
                stroke_color="black",
                stroke_width=title_stroke_width
            ).set_duration(title_duration)
        
        # Set title position from config with TikTok-safe margins if enabled
        if use_tiktok_margins:
            # Position title near the top of the safe area (approximately 20% into safe area)
            title_clip = position_text_in_tiktok_safe_area(
                raw_title_clip, 
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
            title_clip = raw_title_clip.set_position(("center", title_position_y))
        
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
        # Calculate how many loops we need
        loops_needed = int(total_video_duration / background.duration) + 1
        background_loops = [background] * loops_needed
        looped_background = concatenate_videoclips(background_loops)
        # Trim to exact duration needed
        background = looped_background.subclip(0, total_video_duration)
    else:
        # If background is already long enough, just trim it to what we need
        background = background.subclip(0, total_video_duration)
    
    # Create overlay based on settings (solid color, gradient, or animated)
    overlay_effects = STORY_CONFIG.get("overlay_effects", {})
    gradient_settings = overlay_effects.get("gradient", {})
    
    # Create base overlay
    if gradient_settings.get("enabled", False):
        # Use gradient overlay
        start_color = gradient_settings.get("start_color", "#3a1c71")
        end_color = gradient_settings.get("end_color", STORY_CONFIG.get("overlay_color", "#ff2956"))
        
        if gradient_settings.get("animation_enabled", False):
            # Animated gradient
            animation_speed = gradient_settings.get("animation_speed", 0.5)
            overlay = create_animated_gradient_overlay(
                duration=background.duration,
                resolution=TARGET_RESOLUTION,
                start_color=start_color,
                end_color=end_color,
                animation_speed=animation_speed,
                opacity=STORY_CONFIG.get("overlay_opacity", 0.6)
            )
            logging.info(f"Created animated gradient overlay from {start_color} to {end_color}")
        else:
            # Static gradient (use ColorClip with first color for simplicity)
            overlay_color = hex_to_rgb(start_color)
            overlay = ColorClip(TARGET_RESOLUTION, col=overlay_color)
            overlay = overlay.set_opacity(STORY_CONFIG.get("overlay_opacity", 0.6))
            overlay = overlay.set_duration(background.duration)
            logging.info(f"Created static color overlay with color {start_color}")
    else:
        # Use regular solid color overlay
        overlay_color = STORY_CONFIG.get("overlay_color", "#000000")
        # Convert hex to RGB if it's a hex color
        overlay_color = hex_to_rgb(overlay_color)
        
        overlay = ColorClip(TARGET_RESOLUTION, col=overlay_color)
        overlay = overlay.set_opacity(STORY_CONFIG.get("overlay_opacity", 0.6))
        overlay = overlay.set_duration(background.duration)
        logging.info(f"Created solid color overlay with color {overlay_color}")
    
    # Combine background with overlay
    base_clips = [background, overlay]
    
    # Add noise effect if enabled
    noise_settings = overlay_effects.get("noise", {})
    if noise_settings.get("enabled", False):
        noise_opacity = noise_settings.get("opacity", 0.03)
        noise_clip = create_noise_overlay(
            resolution=TARGET_RESOLUTION,
            duration=background.duration,
            opacity=noise_opacity
        )
        base_clips.append(noise_clip)
        logging.info(f"Added noise effect with opacity {noise_opacity}")
    
    # Combine background with overlay(s)
    base = CompositeVideoClip(base_clips)
    
    # Create clip for each segment
    segment_clips = []
    current_time = title_duration  # Start after title (or at 0 if no title)
    
    # Get body text styling
    body_color = STORY_CONFIG.get("body_color", STORY_CONFIG.get("text_color", "white"))
    body_font = STORY_CONFIG.get("body_font", STORY_CONFIG.get("font"))
    body_fontsize = STORY_CONFIG.get("body_font_size", 50)
    body_stroke_width = text_effects.get("body_stroke_width", 1)
    
    # Process segments with proper positioning
    fade_duration = STORY_CONFIG.get("fade_duration", 0.5)
    
    for i, segment in enumerate(story_segments):
        segment_duration = segment_durations[i]
        
        # Create body text with or without shadow effects
        if text_effects_enabled and text_effects.get("body_shadow", True):
            shadow_color = text_effects.get("body_shadow_color", "#000000")
            shadow_offset = text_effects.get("body_shadow_offset", 2)
            
            # Create segment clip with shadow
            raw_segment_clip = create_text_with_shadow(
                text=segment,
                fontsize=body_fontsize,
                color=body_color,
                font=body_font,
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                shadow_color=shadow_color,
                shadow_offset=shadow_offset,
                stroke_width=body_stroke_width
            ).set_duration(segment_duration)
        else:
            # Create segment clip without shadow effect
            raw_segment_clip = TextClip(
                txt=segment,
                fontsize=body_fontsize,
                color=body_color,
                font=body_font,
                method='caption',
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                align='center',
                stroke_color="black",
                stroke_width=body_stroke_width
            ).set_duration(segment_duration)
        
        # Position segment with TikTok-safe margins if enabled
        if use_tiktok_margins:
            segment_clip = position_text_in_tiktok_safe_area(
                raw_segment_clip, 
                tiktok_margins, 
                TARGET_RESOLUTION,
                position_factor=0.33  # Position text 1/3 into the safe area
            )
            logging.info(f"Positioned segment {i+1} with TikTok safe margins at position factor: 0.33")
        else:
            segment_position_y = STORY_CONFIG.get("segment_position_y", 800)
            if segment_position_y is None:
                segment_position_y = 800
            segment_clip = raw_segment_clip.set_position(("center", segment_position_y))
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

def create_descriptive_filename(story_data, background_path, music_path):
    """Create a descriptive filename that includes elements from the story, background, and music."""
    # Get story details
    story_id = story_data.get('id', '0')
    title = story_data.get('title', '')
    background_theme = story_data.get('background_theme', '').lower()
    music_mood = story_data.get('music_mood', '').lower()
    
    # Get base names without extensions
    background_name = os.path.splitext(os.path.basename(background_path))[0]
    music_name = os.path.splitext(os.path.basename(music_path))[0]
    
    # Process title: keep first few words, convert to camelCase (if title exists)
    if title:
        # Clean up special characters
        cleaned_title = re.sub(r'[^\w\s-]', '', title)
        
        # Split into words and limit to first few
        words = cleaned_title.split()
        selected_words = words[:5] if len(words) > 5 else words
        
        # Convert to camelCase
        if selected_words:
            # First word lowercase
            selected_words[0] = selected_words[0].lower()
            # Rest with first letter capitalized
            for i in range(1, len(selected_words)):
                selected_words[i] = selected_words[i].capitalize() if selected_words[i] else ''
            
            # Join without spaces
            title_summary = ''.join(selected_words)
        else:
            title_summary = 'untitled'
    else:
        title_summary = 'untitled'
    
    # Clean up names
    background_name = re.sub(r'\s+', '_', background_name)[:20]  # Limit length
    music_name = re.sub(r'\s+', '_', music_name)[:20]  # Limit length
    
    # Add date in format YYYYMMDD_HHMMSS
    today = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Combine components - format: YYYYMMDD_HHMMSS_sID_titlesummary_theme_mood_bgname_musicname.mp4
    filename = f"{today}_s{story_id}_{title_summary}_{background_theme}_{music_mood}_{background_name}_{music_name}.mp4"
    
    # Ensure the filename isn't too long
    if len(filename) > 100:
        # If we need to truncate, keep just the essential parts
        filename = f"{today}_s{story_id}_{title_summary}_{background_theme}_{music_mood}.mp4"
    
    return filename

def create_text_with_shadow(text, fontsize, color, font, size, alignment='center', 
                           shadow_color="#000000", shadow_offset=2, stroke_width=1):
    """Create text with shadow effect for better visibility"""
    # Create the shadow text clip
    shadow = TextClip(
        txt=text,
        fontsize=fontsize,
        color=shadow_color,
        font=font,
        method='caption',
        size=size,
        align=alignment,
        stroke_color="black",
        stroke_width=stroke_width
    )
    
    # Position the shadow slightly offset
    shadow = shadow.set_position((shadow_offset, shadow_offset))
    
    # Create the main text clip
    txt_clip = TextClip(
        txt=text,
        fontsize=fontsize,
        color=color,
        font=font,
        method='caption',
        size=size,
        align=alignment,
        stroke_color="black",
        stroke_width=stroke_width
    )
    
    # Combine shadow and text
    final_text = CompositeVideoClip([shadow, txt_clip], size=size)
    return final_text

def create_animated_gradient_overlay(duration, resolution, start_color, end_color, animation_speed=0.5, opacity=0.6):
    """Create an animated gradient overlay between two colors"""
    # Convert hex colors to RGB if needed
    start_color = hex_to_rgb(start_color)
    end_color = hex_to_rgb(end_color)
    
    # Create a function that returns the gradient color at time t
    def make_gradient_frame(t):
        # Use sine wave to oscillate between colors for smooth looping
        oscillation = (np.sin(t * animation_speed * np.pi) + 1) / 2
        
        # Interpolate between colors
        r = int(start_color[0] * (1-oscillation) + end_color[0] * oscillation)
        g = int(start_color[1] * (1-oscillation) + end_color[1] * oscillation)
        b = int(start_color[2] * (1-oscillation) + end_color[2] * oscillation)
        
        # Create solid color frame
        frame = np.ones((resolution[1], resolution[0], 3), dtype=np.uint8)
        frame[:,:,0] = r
        frame[:,:,1] = g
        frame[:,:,2] = b
        return frame
    
    # Create a clip with the gradient animation
    from moviepy.editor import VideoClip
    gradient_clip = VideoClip(make_frame=make_gradient_frame, duration=duration)
    gradient_clip = gradient_clip.set_opacity(opacity)
    
    return gradient_clip

def create_noise_overlay(resolution, duration, opacity=0.05):
    """Create a subtle noise texture overlay for film grain effect"""
    # Create a function that returns random noise for each frame
    def make_noise_frame(t):
        noise = np.random.randint(0, 256, (resolution[1], resolution[0], 3), dtype=np.uint8)
        return noise
    
    # Create a clip with the noise animation
    from moviepy.editor import VideoClip
    noise_clip = VideoClip(make_frame=make_noise_frame, duration=duration)
    noise_clip = noise_clip.set_opacity(opacity)
    
    return noise_clip

def add_zoom_effect(clip, zoom_factor=1.05, direction="in"):
    """Add subtle zoom in/out effect to a video clip"""
    def scale_func(t):
        progress = t / clip.duration
        
        if direction == "in":
            # Start at 1.0 and increase to zoom_factor
            scale = 1 + (zoom_factor - 1) * progress
        else:  # zoom out
            # Start at zoom_factor and decrease to 1.0
            scale = zoom_factor - (zoom_factor - 1) * progress
            
        return scale
    
    return clip.resize(lambda t: scale_func(t))

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
        
        # Make theme directory-friendly by replacing spaces with underscores and removing special chars
        theme_dir_name = re.sub(r'[^\w\s-]', '', theme).replace(' ', '_')
        
        # Original theme directory (for backward compatibility)
        original_theme_dir = os.path.join(STORY_CONFIG["background_videos_folder"], theme)
        
        # Directory-friendly theme directory
        folder_friendly_theme_dir = os.path.join(STORY_CONFIG["background_videos_folder"], theme_dir_name)
        
        logging.info(f"Looking for background theme: '{theme}' in folders:")
        logging.info(f"  - {original_theme_dir}")
        logging.info(f"  - {folder_friendly_theme_dir}")
        
        # Get a background video based on theme if possible
        # First try the directory-friendly name
        if os.path.exists(folder_friendly_theme_dir) and os.path.isdir(folder_friendly_theme_dir):
            background_path = get_random_file(folder_friendly_theme_dir, ['.mp4', '.mov'])
            if background_path:
                logging.info(f"Found background video in directory-friendly theme folder: {folder_friendly_theme_dir}")
            else:
                # Try the original theme name for backward compatibility
                if os.path.exists(original_theme_dir) and os.path.isdir(original_theme_dir):
                    background_path = get_random_file(original_theme_dir, ['.mp4', '.mov'])
                    if background_path:
                        logging.info(f"Found background video in original theme folder: {original_theme_dir}")
                    else:
                        # Fallback to main backgrounds directory
                        background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                        if background_path:
                            logging.info(f"Fallback: Found background video in main backgrounds folder")
                else:
                    # Fallback to main backgrounds directory
                    background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                    if background_path:
                        logging.info(f"Fallback: Found background video in main backgrounds folder")
        else:
            # Try the original theme name
            if os.path.exists(original_theme_dir) and os.path.isdir(original_theme_dir):
                background_path = get_random_file(original_theme_dir, ['.mp4', '.mov'])
                if background_path:
                    logging.info(f"Found background video in original theme folder: {original_theme_dir}")
                else:
                    # Fallback to main backgrounds directory
                    background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                    if background_path:
                        logging.info(f"Fallback: Found background video in main backgrounds folder")
            else:
                # Fallback to main backgrounds directory
                background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                if background_path:
                    logging.info(f"Fallback: Found background video in main backgrounds folder")
        
        if not background_path:
            logging.error("No background videos found. Please add videos to the backgrounds directory.")
            continue
        
        # Check if music mood folder exists
        mood = story.get("music_mood", "").lower()
        
        # Make mood directory-friendly by replacing spaces with underscores and removing special chars
        mood_dir_name = re.sub(r'[^\w\s-]', '', mood).replace(' ', '_')
        
        # Original mood directory (for backward compatibility)
        original_mood_dir = os.path.join(STORY_CONFIG["music_folder"], mood)
        
        # Directory-friendly mood directory
        folder_friendly_mood_dir = os.path.join(STORY_CONFIG["music_folder"], mood_dir_name)
        
        logging.info(f"Looking for music mood: '{mood}' in folders:")
        logging.info(f"  - {original_mood_dir}")
        logging.info(f"  - {folder_friendly_mood_dir}")
        
        # Get music based on mood if possible
        # First try the directory-friendly name
        if os.path.exists(folder_friendly_mood_dir) and os.path.isdir(folder_friendly_mood_dir):
            music_path = get_random_file(folder_friendly_mood_dir, ['.mp3', '.wav', '.m4a'])
            if music_path:
                logging.info(f"Found music in directory-friendly mood folder: {folder_friendly_mood_dir}")
            else:
                # Try the original mood name for backward compatibility
                if os.path.exists(original_mood_dir) and os.path.isdir(original_mood_dir):
                    music_path = get_random_file(original_mood_dir, ['.mp3', '.wav', '.m4a'])
                    if music_path:
                        logging.info(f"Found music in original mood folder: {original_mood_dir}")
                    else:
                        # Fallback to main music directory
                        music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                        if music_path:
                            logging.info(f"Fallback: Found music in main music folder")
                else:
                    # Fallback to main music directory
                    music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                    if music_path:
                        logging.info(f"Fallback: Found music in main music folder")
        else:
            # Try the original mood name
            if os.path.exists(original_mood_dir) and os.path.isdir(original_mood_dir):
                music_path = get_random_file(original_mood_dir, ['.mp3', '.wav', '.m4a'])
                if music_path:
                    logging.info(f"Found music in original mood folder: {original_mood_dir}")
                else:
                    # Fallback to main music directory
                    music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                    if music_path:
                        logging.info(f"Fallback: Found music in main music folder")
            else:
                # Fallback to main music directory
                music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                if music_path:
                    logging.info(f"Fallback: Found music in main music folder")
        
        if not music_path:
            logging.error("No music files found. Please add music to the music directory.")
            continue
        
        # Generate descriptive output filename
        output_path = os.path.join(
            STORY_CONFIG["output_folder"],
            create_descriptive_filename(story, background_path, music_path)
        )
        
        # Create the story video
        create_story_video(story, background_path, music_path, output_path)
        
        print(f"✅ Story video created: {output_path}")

if __name__ == "__main__":
    main() 