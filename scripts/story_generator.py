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
from moviepy.video.fx import all as vfx
import argparse
import csv
import re
import numpy as np
from functools import partial

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import STORY_CONFIG, TARGET_RESOLUTION
from scripts.utils import setup_directories, load_csv, resize_video, get_random_file, get_sequential_file, position_text_in_tiktok_safe_area, visualize_safe_area, hex_to_rgb

# Project name for filenames
PROJECT_NAME = "StoryGen"

def has_story_been_generated(story_id, tracking_file):
    """Check if a story with given ID has already been generated"""
    if not os.path.exists(tracking_file) or os.path.getsize(tracking_file) == 0:
        return False
    
    try:
        with open(tracking_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('story_id') == str(story_id):
                    return True
    except Exception as e:
        logging.warning(f"Error checking tracking file: {e}")
    
    return False

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
    
    # Apply background effects from config
    background_effects = STORY_CONFIG.get("background_effects", {})
    
    # Apply flip effect to background if enabled
    flip_settings = background_effects.get("flip", {})
    if flip_settings.get("enabled", False):
        if flip_settings.get("horizontal", True):
            logging.info(f"Applying horizontal flip (mirror) effect to background")
            background = vfx.mirror_x(background)
    
    # Apply zoom effect to background if enabled
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
    
    # Check if title should be on its own segment
    title_own_segment = STORY_CONFIG.get("title_own_segment", False)
    
    # If show_title is True but title_own_segment is False, we'll still show the title
    # but combined with the first segment instead of on its own card
    show_title_as_segment = show_title and title_own_segment
    
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
    
    if show_title_as_segment and story_data.get("title", "").strip():
        # Get title duration from config
        title_duration = STORY_CONFIG.get("title_duration", 3.0)
        
        logging.info(f"Title width will be: {TARGET_RESOLUTION[0] - horizontal_margin}px (with {horizontal_margin}px margin)")
        
        # Get title-specific styling
        title_color = STORY_CONFIG.get("title_color", STORY_CONFIG.get("text_color", "white"))
        title_font = STORY_CONFIG.get("title_font", STORY_CONFIG.get("font"))
        title_fontsize = STORY_CONFIG.get("heading_font_size", 72)
        title_stroke_width = text_effects.get("title_stroke_width", 2)
        title_stroke_color = text_effects.get("title_stroke_color", "#000000")
        
        # Create title with or without shadow effects
        if text_effects_enabled and text_effects.get("title_shadow", True):
            shadow_color = text_effects.get("title_shadow_color", "#000000")
            shadow_offset = text_effects.get("title_shadow_offset", 3)
            
            # Add better line spacing for title text (only needed for multi-line titles)
            if '\n' in story_data["title"]:
                logging.info(f"Title contains multiple lines, adding increased line spacing")
                # We can't directly control line height in TextClip, but we can add extra newlines
                # and recombine with proper spacing
                title_lines = story_data["title"].split('\n')
                # Add extra spacing by padding each line
                story_data["title"] = '\n\n'.join(title_lines)
            
            # Create title clip with shadow
            raw_title_clip = create_text_with_shadow(
                text=story_data["title"],
                fontsize=title_fontsize,
                color=title_color,
                font=title_font,
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                shadow_color=shadow_color,
                shadow_offset=shadow_offset,
                stroke_width=title_stroke_width,
                stroke_color=title_stroke_color
            ).set_duration(title_duration)
        else:
            # Add better line spacing for title text (only needed for multi-line titles)
            if '\n' in story_data["title"]:
                logging.info(f"Title contains multiple lines, adding increased line spacing")
                # We can't directly control line height in TextClip, but we can add extra newlines
                # and recombine with proper spacing
                title_lines = story_data["title"].split('\n')
                # Add extra spacing by padding each line
                story_data["title"] = '\n\n'.join(title_lines)
            
            # Create title clip without shadow effect
            raw_title_clip = TextClip(
                txt=story_data["title"],
                fontsize=title_fontsize,
                color=title_color,
                font=title_font,
                method='caption',
                size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                align='center',
                stroke_color=title_stroke_color,
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
    
    # Add title to the first segment if title exists and we're not using a separate title card
    has_title = story_data.get("title", "").strip() != ""
    if has_title and not title_own_segment and story_segments:
        # We'll handle this title as part of the first segment, not as a separate title card
        show_title_as_segment = False  # Disable separate title card
        logging.info(f"Will display title with first segment (combined card)")
    
    # Calculate duration for each segment based on content
    segment_durations = []
    
    # Process each segment (including title if combined)
    for i, segment in enumerate(story_segments):
        # If this is the first segment and we need to add the title
        if i == 0 and has_title and not title_own_segment:
            # Combine the title with the first segment
            title_text = story_data["title"]
            # We're handling the title and content separately for styling purposes
            # but they'll be displayed on the same card
            segment_durations.append(calculate_segment_duration(title_text + " " + segment))
            logging.info(f"Calculated combined duration for title+first segment: {segment_durations[-1]} seconds")
        else:
            segment_durations.append(calculate_segment_duration(segment))
    
    total_needed_duration = sum(segment_durations)
    
    # Calculate the total video duration required
    # If using separate title card, include title_duration
    if show_title_as_segment:
        total_video_duration = title_duration + total_needed_duration
    else:
        total_video_duration = total_needed_duration
    
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
    
    # Get global opacity setting
    global_opacity = overlay_effects.get("global_opacity", 0.6)
    
    # Create base overlay
    if gradient_settings.get("enabled", False):
        # Use gradient overlay
        start_color = gradient_settings.get("start_color", "#3a1c71")
        end_color = gradient_settings.get("end_color", "#ff2956")  # Default end color if not specified
        
        if gradient_settings.get("animation_enabled", False):
            # Animated gradient
            animation_speed = gradient_settings.get("animation_speed", 0.5)
            overlay = create_animated_gradient_overlay(
                duration=background.duration,
                resolution=TARGET_RESOLUTION,
                start_color=start_color,
                end_color=end_color,
                animation_speed=animation_speed,
                opacity=global_opacity
            )
            logging.info(f"Created animated gradient overlay from {start_color} to {end_color}")
        else:
            # Static gradient (use ColorClip with first color for simplicity)
            overlay_color = hex_to_rgb(start_color)
            overlay = ColorClip(TARGET_RESOLUTION, col=overlay_color)
            overlay = overlay.set_opacity(global_opacity)
            overlay = overlay.set_duration(total_video_duration)
            logging.info(f"Created static color overlay with color {start_color}")
    else:
        # Use regular solid color overlay
        overlay_color = overlay_effects.get("solid_color", "#000000")  # Use solid_color from config
        # Convert hex to RGB if it's a hex color
        overlay_color = hex_to_rgb(overlay_color)
        
        overlay = ColorClip(TARGET_RESOLUTION, col=overlay_color)
        overlay = overlay.set_opacity(global_opacity)
        overlay = overlay.set_duration(total_video_duration)
        logging.info(f"Created solid color overlay with color {overlay_color}")
    
    # Combine background with overlay
    base_clips = [background, overlay]
    
    # Add noise effect if enabled
    noise_settings = overlay_effects.get("noise", {})
    if noise_settings.get("enabled", False):
        noise_opacity = noise_settings.get("opacity", 0.03) * global_opacity  # Scale noise opacity by global opacity
        noise_clip = create_noise_overlay(
            resolution=TARGET_RESOLUTION,
            duration=total_video_duration,
            opacity=noise_opacity
        )
        base_clips.append(noise_clip)
        logging.info(f"Added noise effect with opacity {noise_opacity}")
    
    # Combine background with overlay(s)
    base = CompositeVideoClip(base_clips)
    
    # Create clip for each segment
    segment_clips = []
    current_time = 0
    
    # If we have a separate title card, set current_time to title_duration
    if show_title_as_segment:
        current_time = title_duration
    
    # Get body text styling
    body_color = STORY_CONFIG.get("body_color", STORY_CONFIG.get("text_color", "white"))
    body_font = STORY_CONFIG.get("body_font", STORY_CONFIG.get("font"))
    body_fontsize = STORY_CONFIG.get("body_font_size", 58)  # Use the value from config
    body_stroke_width = text_effects.get("body_stroke_width", 1)
    body_stroke_color = text_effects.get("body_stroke_color", "#000000")
    
    # Make sure title_fontsize is defined before using it
    title_fontsize = STORY_CONFIG.get("heading_font_size", 72)  # Default title font size
    
    logging.info(f"Using title font size: {title_fontsize}pt, body font size: {body_fontsize}pt")
    
    # Process segments with proper positioning
    fade_duration = STORY_CONFIG.get("fade_duration", 0.5)
    
    for i, segment in enumerate(story_segments):
        segment_duration = segment_durations[i]
        
        # Check if this is the first segment and we need to combine with title
        is_combined_title_segment = (i == 0 and has_title and not title_own_segment)
        
        # For the first segment that should include title, we need special handling
        if is_combined_title_segment:
            title_text = story_data["title"]
            content_text = segment
            
            # Debug logs
            logging.info(f"Creating combined title+content segment")
            logging.info(f"Title: '{title_text}' [{len(title_text)} chars]")
            logging.info(f"Content: '{content_text[:100]}...' [{len(content_text)} chars]")
            
            # Create title with title styling
            title_color = STORY_CONFIG.get("title_color", STORY_CONFIG.get("text_color", "white"))
            title_font = STORY_CONFIG.get("title_font", STORY_CONFIG.get("font"))
            title_fontsize = STORY_CONFIG.get("heading_font_size", 72)
            title_stroke_width = text_effects.get("title_stroke_width", 2)
            title_stroke_color = text_effects.get("title_stroke_color", "#000000")
            
            # Create title text with shadow if enabled
            if text_effects_enabled and text_effects.get("title_shadow", True):
                shadow_color = text_effects.get("title_shadow_color", "#000000")
                shadow_offset = text_effects.get("title_shadow_offset", 3)
                
                # Add better line spacing for title text (only needed for multi-line titles)
                if '\n' in title_text:
                    logging.info(f"Title contains multiple lines, adding increased line spacing")
                    # We can't directly control line height in TextClip, but we can add extra newlines
                    # and recombine with proper spacing
                    title_lines = title_text.split('\n')
                    # Add extra spacing by padding each line
                    title_text = '\n\n'.join(title_lines)
                
                title_text_clip = create_text_with_shadow(
                    text=title_text,
                    fontsize=title_fontsize,
                    color=title_color,
                    font=title_font,
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    shadow_color=shadow_color,
                    shadow_offset=shadow_offset,
                    stroke_width=title_stroke_width,
                    stroke_color=title_stroke_color
                )
            else:
                # Add better line spacing for title text (only needed for multi-line titles)
                if '\n' in title_text:
                    logging.info(f"Title contains multiple lines, adding increased line spacing")
                    # We can't directly control line height in TextClip, but we can add extra newlines
                    # and recombine with proper spacing
                    title_lines = title_text.split('\n')
                    # Add extra spacing by padding each line
                    title_text = '\n\n'.join(title_lines)
                
                title_text_clip = TextClip(
                    txt=title_text,
                    fontsize=title_fontsize,
                    color=title_color,
                    font=title_font,
                    method='caption',
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    align='center',
                    stroke_color=title_stroke_color,
                    stroke_width=title_stroke_width
                )
                
            # Create body text with body styling
            body_color = STORY_CONFIG.get("body_color", STORY_CONFIG.get("text_color", "white"))
            body_font = STORY_CONFIG.get("body_font", STORY_CONFIG.get("font"))
            body_fontsize = STORY_CONFIG.get("body_font_size", 58)  # Use the value from config
            body_stroke_width = text_effects.get("body_stroke_width", 1)
            
            # Create content text with shadow if enabled
            if text_effects_enabled and text_effects.get("body_shadow", True):
                shadow_color = text_effects.get("body_shadow_color", "#000000")
                shadow_offset = text_effects.get("body_shadow_offset", 2)
                
                content_text_clip = create_text_with_shadow(
                    text=content_text,
                    fontsize=body_fontsize,
                    color=body_color,
                    font=body_font,
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    shadow_color=shadow_color,
                    shadow_offset=shadow_offset,
                    stroke_width=body_stroke_width,
                    stroke_color=body_stroke_color
                )
            else:
                content_text_clip = TextClip(
                    txt=content_text,
                    fontsize=body_fontsize,
                    color=body_color,
                    font=body_font,
                    method='caption',
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    align='center',
                    stroke_color=body_stroke_color,
                    stroke_width=body_stroke_width
                )
            
            # Get title and content clip dimensions for positioning
            title_height = title_text_clip.h
            content_height = content_text_clip.h
            
            # Position title and content independently in the safe area
            # This prevents positioning issues caused by dynamic heights
            
            if use_tiktok_margins:
                safe_top = tiktok_margins.get("top", 252)
                safe_bottom = TARGET_RESOLUTION[1] - tiktok_margins.get("bottom", 640)
                safe_height = safe_bottom - safe_top
                
                # Title positioned in the top x% of safe area
                title_pos_factor = 0.05  # from the top of safe area  
                
                # Content positioned closer to middle (x% from top of safe area)
                # This creates a fixed, reliable space between them regardless of content
                content_pos_factor = 0.4  # Fixed content position
                
                logging.info(f"Using independent positioning: title at {title_pos_factor*100}%, content at {content_pos_factor*100}% of safe area")
                
                # We still calculate the total height for font size adjustments
                shadow_offset = text_effects.get("title_shadow_offset", 3)
                content_spacing = max(100, int(title_fontsize * 1.2))  # For height calculation only
                total_height = title_height + content_spacing + content_height + shadow_offset
                
                # If text is too tall to fit in safe zone, reduce content font size
                max_allowed_height = safe_height * 1.0  # Allow 100% of safe height (was 0.95)
                
                if total_height > max_allowed_height:
                    # Content text is too tall, needs font size reduction
                    original_fontsize = body_fontsize
                    
                    # Calculate a gentler reduction - use square root to make reduction less severe
                    reduction_factor = max(0.8, 1.0 - (0.5 * (total_height - max_allowed_height) / max_allowed_height))
                    
                    # Apply reduction with a higher minimum
                    adjusted_fontsize = max(int(body_fontsize * reduction_factor), 45)  # Minimum 45pt now (was 24)
                    
                    logging.info(f"Content too tall ({total_height}px vs {max_allowed_height}px allowed), reducing font size from {body_fontsize} to {adjusted_fontsize} (reduction factor: {reduction_factor:.2f})")
                    
                    # Recreate content text with reduced font size
                    if text_effects_enabled and text_effects.get("body_shadow", True):
                        shadow_color = text_effects.get("body_shadow_color", "#000000")
                        shadow_offset = text_effects.get("body_shadow_offset", 2)
                        
                        content_text_clip = create_text_with_shadow(
                            text=content_text,
                            fontsize=adjusted_fontsize,  # Reduced font size
                            color=body_color,
                            font=body_font,
                            size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                            shadow_color=shadow_color,
                            shadow_offset=shadow_offset,
                            stroke_width=body_stroke_width,
                            stroke_color=body_stroke_color
                        )
                    else:
                        content_text_clip = TextClip(
                            txt=content_text,
                            fontsize=adjusted_fontsize,  # Reduced font size
                            color=body_color,
                            font=body_font,
                            method='caption',
                            size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                            align='center',
                            stroke_color=body_stroke_color,
                            stroke_width=body_stroke_width
                        )
                    
                    # Update content height
                    content_height = content_text_clip.h
                    total_height = title_height + content_spacing + content_height + shadow_offset
                    logging.info(f"After font reduction, content height: {content_height}px, total height: {total_height}px")
                
                # Use the proper TikTok safe area positioning function instead of manual positioning
                # This ensures both vertical and horizontal margins are respected
                positioned_title_clip = position_text_in_tiktok_safe_area(
                    title_text_clip, 
                    tiktok_margins, 
                    TARGET_RESOLUTION, 
                    position_factor=title_pos_factor
                )
                
                # For content, we'll use our fixed position factor
                positioned_content_clip = position_text_in_tiktok_safe_area(
                    content_text_clip, 
                    tiktok_margins, 
                    TARGET_RESOLUTION, 
                    position_factor=content_pos_factor
                )
                
                logging.info(f"Applied TikTok margin positioning with title factor: {title_pos_factor}, content factor: {content_pos_factor}")
            else:
                # Position with fixed values if not using TikTok margins
                title_y = 350
                content_y = 600  # Fixed position with good separation from title
                
                # Create clips with proper positions
                positioned_title_clip = title_text_clip.set_position(("center", title_y))
                positioned_content_clip = content_text_clip.set_position(("center", content_y))
                
                logging.info(f"Using fixed positioning: title Y at {title_y}px, content Y at {content_y}px")
            
            # Combine the clips and set duration
            combined_clip = CompositeVideoClip([
                positioned_title_clip,
                positioned_content_clip
            ], size=TARGET_RESOLUTION).set_duration(segment_duration)
            
            # Debug the composite clip
            logging.info(f"Created composite clip with title and content, duration: {segment_duration}s")
            
            # Add fade effects
            segment_clip = combined_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
        else:
            # Standard segment - create body text with or without shadow effects
            if text_effects_enabled and text_effects.get("body_shadow", True):
                shadow_color = text_effects.get("body_shadow_color", "#000000")
                shadow_offset = text_effects.get("body_shadow_offset", 2)
                
                # Use the original font size from config without reduction
                segment_fontsize = STORY_CONFIG.get("body_font_size", 58)
                body_stroke_color = text_effects.get("body_stroke_color", "#000000")
                
                # Create segment clip with shadow
                raw_segment_clip = create_text_with_shadow(
                    text=segment,
                    fontsize=segment_fontsize,
                    color=body_color,
                    font=body_font,
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    shadow_color=shadow_color,
                    shadow_offset=shadow_offset,
                    stroke_width=body_stroke_width,
                    stroke_color=body_stroke_color
                ).set_duration(segment_duration)
            else:
                # Use the original font size from config without reduction
                segment_fontsize = STORY_CONFIG.get("body_font_size", 58)
                body_stroke_color = text_effects.get("body_stroke_color", "#000000")
                
                # Create segment clip without shadow effect
                raw_segment_clip = TextClip(
                    txt=segment,
                    fontsize=segment_fontsize,
                    color=body_color,
                    font=body_font,
                    method='caption',
                    size=(TARGET_RESOLUTION[0] - horizontal_margin, None),
                    align='center',
                    stroke_color=body_stroke_color,
                    stroke_width=body_stroke_width
                ).set_duration(segment_duration)
            
            # Position segment with TikTok-safe margins if enabled
            if use_tiktok_margins:
                # Use a position factor that's different from the combined title+content segment
                # to ensure consistent positioning between all segments
                segment_pos_factor = 0.33  # Position text 1/3 into the safe area
                segment_clip = position_text_in_tiktok_safe_area(
                    raw_segment_clip, 
                    tiktok_margins, 
                    TARGET_RESOLUTION,
                    position_factor=segment_pos_factor
                )
                logging.info(f"Positioned segment {i+1} with TikTok safe margins at position factor: {segment_pos_factor}")
            else:
                segment_position_y = STORY_CONFIG.get("segment_position_y", 800)
                if segment_position_y is None:
                    segment_position_y = 800
                segment_clip = raw_segment_clip.set_position(("center", segment_position_y))
                logging.info(f"Using standard segment position y: {segment_position_y}px")
            
            # Add fade in/out effects
            segment_clip = segment_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
        
        segment_clip = segment_clip.set_start(current_time)
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
    
    # After music is added, ensure final video duration is exactly total_video_duration
    if final_video.duration > total_video_duration:
        logging.info(f"Trimming final video from {final_video.duration}s to exact duration of {total_video_duration}s")
        final_video = final_video.subclip(0, total_video_duration)
    
    # Check if iPhone style is enabled in config
    iphone_style_config = STORY_CONFIG.get("iphone_style", {})
    iphone_style_enabled = iphone_style_config.get("enabled", False)
    
    # Check if we need to change the output path extension
    if iphone_style_enabled and iphone_style_config.get("use_mov_container", True):
        if output_path.lower().endswith('.mp4'):
            output_path = output_path[:-4] + '.mov'
            logging.info(f"Changed output extension to .mov for iPhone compatibility")
    
    # Write the final video with appropriate encoding based on configuration
    if iphone_style_enabled:
        logging.info("Writing video with iPhone-style encoding")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec=iphone_style_config.get("codec", "libx265"),  # HEVC codec like iPhone
            preset='medium',
            bitrate=iphone_style_config.get("bitrate", "16000k"),
            ffmpeg_params=[
                '-tag:v', 'hvc1',         # Add HVC1 tag for Apple compatibility
                '-pix_fmt', 'yuv420p',    # Standard pixel format
                '-movflags', '+faststart', # Optimize for web streaming
                '-color_primaries', 'bt709', # Standard color space
                '-color_trc', 'bt709',     # Standard color transfer
                '-colorspace', 'bt709',    # Standard colorspace
            ],
            audio_codec='aac',
            audio_bitrate='192k',
            threads=4
        )
        
        # Apply iPhone metadata
        from utils import apply_iphone_metadata
        output_path = apply_iphone_metadata(output_path)
        logging.info(f"Applied iPhone metadata to: {output_path}")
    else:
        # Standard encoding (original behavior)
        logging.info("Writing video with standard encoding")
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
    
    # Check if iPhone style is enabled and should use .mov extension
    iphone_style_config = STORY_CONFIG.get("iphone_style", {})
    use_mov_container = (iphone_style_config.get("enabled", False) and 
                        iphone_style_config.get("use_mov_container", True))
    
    # Set the extension based on configuration
    extension = '.mov' if use_mov_container else '.mp4'
    
    # Combine components - format: YYYYMMDD_HHMMSS_sID_titlesummary_theme_mood_bgname_musicname.mp4
    filename = f"{today}_s{story_id}_{title_summary}_{background_theme}_{music_mood}_{background_name}_{music_name}{extension}"
    
    # Ensure the filename isn't too long
    if len(filename) > 100:
        # If we need to truncate, keep just the essential parts
        filename = f"{today}_s{story_id}_{title_summary}_{background_theme}_{music_mood}{extension}"
    
    return filename

def create_text_with_shadow(text, fontsize, color, font, size, alignment='center', 
                           shadow_color="#000000", shadow_offset=2, stroke_width=1, stroke_color="black"):
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
        stroke_color=stroke_color,
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
        stroke_color=stroke_color,
        stroke_width=stroke_width
    )
    
    # Combine shadow and text - don't specify size (let it be determined automatically)
    final_text = CompositeVideoClip([shadow, txt_clip])
    return final_text

def create_animated_gradient_overlay(duration, resolution, start_color, end_color, animation_speed=0.5, opacity=0.6):
    """Create an animated gradient overlay with a linear gradient that moves across the screen"""
    # Convert hex colors to RGB if needed
    start_color = hex_to_rgb(start_color)
    end_color = hex_to_rgb(end_color)
    
    # Create a function that returns the gradient frame at time t
    def make_gradient_frame(t):
        # Create frame canvas
        frame = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)
        
        # Animate gradient direction using sine wave for smooth looping
        angle = 2 * np.pi * (t * animation_speed % 1.0)
        
        # Calculate direction vector for gradient
        dx = np.cos(angle)
        dy = np.sin(angle)
        
        # Create coordinate grids
        y, x = np.mgrid[0:resolution[1], 0:resolution[0]]
        
        # Normalize coordinates to [-1, 1] range
        x_norm = 2 * x / resolution[0] - 1
        y_norm = 2 * y / resolution[1] - 1
        
        # Calculate gradient value for each pixel (dot product with direction)
        gradient = (x_norm * dx + y_norm * dy + 1) / 2  # Normalize to [0, 1]
        gradient = np.clip(gradient, 0, 1)
        
        # Apply gradient to each color channel
        for c in range(3):
            frame[:, :, c] = (start_color[c] * (1 - gradient) + end_color[c] * gradient).astype(np.uint8)
        
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
    parser.add_argument('--all', action='store_true', help='Generate videos for all stories in the CSV file')
    parser.add_argument('--force', action='store_true', help='Force regeneration even if story exists')
    parser.add_argument('--start-id', type=str, help='Start processing from this ID (when using "all" mode)')
    parser.add_argument('--mode', choices=['random', 'sequential'], help='Override the file selection mode in config')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Ensure directories exist
    setup_directories([STORY_CONFIG["output_folder"]])
    
    # Get file selection mode from config (with command line override)
    file_selection_mode = args.mode if args.mode else STORY_CONFIG.get("file_selection_mode", "random")
    sequential_tracking_file = STORY_CONFIG.get("sequential_tracking_file")
    
    # If using sequential mode, ensure tracking file directory exists
    if file_selection_mode == "sequential" and sequential_tracking_file:
        tracking_dir = os.path.dirname(sequential_tracking_file)
        setup_directories([tracking_dir])
        logging.info(f"Using {file_selection_mode} file selection mode with tracking file: {sequential_tracking_file}")
    else:
        logging.info(f"Using {file_selection_mode} file selection mode")
    
    # Load stories data
    stories = load_csv(STORY_CONFIG["stories_file"])
    
    if not stories:
        logging.error(f"No stories found in {STORY_CONFIG['stories_file']}")
        return
    
    # Tracking file path
    tracking_file = os.path.join(STORY_CONFIG["output_folder"], "story_tracking.csv")
    
    # Get duplicate handling setting
    duplicate_handling = STORY_CONFIG.get("duplicate_handling", "always_new")
    
    # Override duplicate handling if --force is used
    if args.force:
        duplicate_handling = "always_new"
        logging.info("Force flag used - will regenerate all stories regardless of existing files")
    
    # Priority for story selection:
    # 1. Command line --id parameter (explicit selection)
    # 2. Command line --all parameter (generate all)
    # 3. Config setting (all or random)
    
    # Filter stories by ID if specified
    stories_to_generate = []
    if args.id:
        # Explicit ID selection via command line has highest priority
        requested_ids = [id.strip() for id in args.id.split(',')]
        for story in stories:
            if story.get('id') in requested_ids:
                # Check if story has already been generated
                if duplicate_handling == "skip" and has_story_been_generated(story.get('id'), tracking_file):
                    logging.info(f"Skipping story ID {story.get('id')} - already generated")
                    continue
                stories_to_generate.append(story)
        if not stories_to_generate:
            logging.error(f"No stories found with requested IDs: {args.id}")
            return
    elif args.all or args.start_id or STORY_CONFIG.get("story_selection", "random").lower() == "all":
        # Generate all stories (from command line flag or config)
        
        # Sort stories by ID for consistent ordering
        stories = sorted(stories, key=lambda x: int(x.get('id', '0')))
        
        # Set starting ID (default to first story or use command line parameter)
        start_id = args.start_id if args.start_id else None
        start_found = (start_id is None)  # If no start_id specified, we start from beginning
        
        # If a specific start ID is given
        if start_id:
            logging.info(f"Starting from ID: {start_id}")
        
        # Process stories
        for story in stories:
            # If we have a start_id and haven't found it yet, check if this is it
            if not start_found and story.get('id') == start_id:
                start_found = True
            
            # Skip stories before start_id
            if not start_found:
                continue
                
            # Check if story has already been generated (if in skip mode)
            if duplicate_handling == "skip" and has_story_been_generated(story.get('id'), tracking_file):
                logging.info(f"Skipping story ID {story.get('id')} - already generated")
                continue
                
            stories_to_generate.append(story)
        
        # Log info about what we're generating
        if args.all:
            logging.info(f"Generating videos for all {len(stories_to_generate)} stories from command line flag")
        elif args.start_id:
            logging.info(f"Generating videos for {len(stories_to_generate)} stories starting from ID {start_id}")
        else:
            logging.info(f"Generating videos for all {len(stories_to_generate)} stories based on config setting")
            
        # Check if we have any stories to generate
        if not stories_to_generate:
            if start_id and not start_found:
                logging.error(f"Starting ID {start_id} not found in stories file.")
            else:
                logging.error("No stories to generate. All may have been processed already.")
            return
    else:
        # Default to random selection (one story)
        if duplicate_handling == "skip":
            # Only select from stories that haven't been generated yet
            available_stories = [s for s in stories if not has_story_been_generated(s.get('id'), tracking_file)]
            if not available_stories:
                logging.error("All stories have already been generated. Use --force to regenerate.")
                return
            stories_to_generate = [random.choice(available_stories)]
        else:
            stories_to_generate = [random.choice(stories)]
        logging.info(f"Selected random story ID: {stories_to_generate[0].get('id')}")
    
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
        
        # Get a background video based on file selection mode
        background_path = None
        
        # First try the directory-friendly name
        if os.path.exists(folder_friendly_theme_dir) and os.path.isdir(folder_friendly_theme_dir):
            if file_selection_mode == "sequential":
                background_path = get_sequential_file(
                    folder_friendly_theme_dir, 
                    ['.mp4', '.mov'], 
                    sequential_tracking_file, 
                    f"background:{theme_dir_name}"
                )
            else:  # Default to random
                background_path = get_random_file(folder_friendly_theme_dir, ['.mp4', '.mov'])
                
            if background_path:
                logging.info(f"Found background video in directory-friendly theme folder: {folder_friendly_theme_dir}")
            else:
                # Try the original theme name for backward compatibility
                if os.path.exists(original_theme_dir) and os.path.isdir(original_theme_dir):
                    if file_selection_mode == "sequential":
                        background_path = get_sequential_file(
                            original_theme_dir, 
                            ['.mp4', '.mov'], 
                            sequential_tracking_file, 
                            f"background:{theme}"
                        )
                    else:  # Default to random
                        background_path = get_random_file(original_theme_dir, ['.mp4', '.mov'])
                        
                    if background_path:
                        logging.info(f"Found background video in original theme folder: {original_theme_dir}")
                    else:
                        # Fallback to main backgrounds directory
                        if file_selection_mode == "sequential":
                            background_path = get_sequential_file(
                                STORY_CONFIG["background_videos_folder"], 
                                ['.mp4', '.mov'], 
                                sequential_tracking_file, 
                                "background:main"
                            )
                        else:  # Default to random
                            background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                            
                        if background_path:
                            logging.info(f"Fallback: Found background video in main backgrounds folder")
                else:
                    # Fallback to main backgrounds directory
                    if file_selection_mode == "sequential":
                        background_path = get_sequential_file(
                            STORY_CONFIG["background_videos_folder"], 
                            ['.mp4', '.mov'], 
                            sequential_tracking_file, 
                            "background:main"
                        )
                    else:  # Default to random
                        background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                        
                    if background_path:
                        logging.info(f"Fallback: Found background video in main backgrounds folder")
        else:
            # Try the original theme name
            if os.path.exists(original_theme_dir) and os.path.isdir(original_theme_dir):
                if file_selection_mode == "sequential":
                    background_path = get_sequential_file(
                        original_theme_dir, 
                        ['.mp4', '.mov'], 
                        sequential_tracking_file, 
                        f"background:{theme}"
                    )
                else:  # Default to random
                    background_path = get_random_file(original_theme_dir, ['.mp4', '.mov'])
                    
                if background_path:
                    logging.info(f"Found background video in original theme folder: {original_theme_dir}")
                else:
                    # Fallback to main backgrounds directory
                    if file_selection_mode == "sequential":
                        background_path = get_sequential_file(
                            STORY_CONFIG["background_videos_folder"], 
                            ['.mp4', '.mov'], 
                            sequential_tracking_file, 
                            "background:main"
                        )
                    else:  # Default to random
                        background_path = get_random_file(STORY_CONFIG["background_videos_folder"], ['.mp4', '.mov'])
                        
                    if background_path:
                        logging.info(f"Fallback: Found background video in main backgrounds folder")
            else:
                # Fallback to main backgrounds directory
                if file_selection_mode == "sequential":
                    background_path = get_sequential_file(
                        STORY_CONFIG["background_videos_folder"], 
                        ['.mp4', '.mov'], 
                        sequential_tracking_file, 
                        "background:main"
                    )
                else:  # Default to random
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
        
        # Get music based on mood and file selection mode
        music_path = None
        
        # First try the directory-friendly name
        if os.path.exists(folder_friendly_mood_dir) and os.path.isdir(folder_friendly_mood_dir):
            if file_selection_mode == "sequential":
                music_path = get_sequential_file(
                    folder_friendly_mood_dir, 
                    ['.mp3', '.wav', '.m4a'], 
                    sequential_tracking_file, 
                    f"music:{mood_dir_name}"
                )
            else:  # Default to random
                music_path = get_random_file(folder_friendly_mood_dir, ['.mp3', '.wav', '.m4a'])
                
            if music_path:
                logging.info(f"Found music in directory-friendly mood folder: {folder_friendly_mood_dir}")
            else:
                # Try the original mood name for backward compatibility
                if os.path.exists(original_mood_dir) and os.path.isdir(original_mood_dir):
                    if file_selection_mode == "sequential":
                        music_path = get_sequential_file(
                            original_mood_dir, 
                            ['.mp3', '.wav', '.m4a'], 
                            sequential_tracking_file, 
                            f"music:{mood}"
                        )
                    else:  # Default to random
                        music_path = get_random_file(original_mood_dir, ['.mp3', '.wav', '.m4a'])
                        
                    if music_path:
                        logging.info(f"Found music in original mood folder: {original_mood_dir}")
                    else:
                        # Fallback to main music directory
                        if file_selection_mode == "sequential":
                            music_path = get_sequential_file(
                                STORY_CONFIG["music_folder"], 
                                ['.mp3', '.wav', '.m4a'], 
                                sequential_tracking_file, 
                                "music:main"
                            )
                        else:  # Default to random
                            music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                            
                        if music_path:
                            logging.info(f"Fallback: Found music in main music folder")
                else:
                    # Fallback to main music directory
                    if file_selection_mode == "sequential":
                        music_path = get_sequential_file(
                            STORY_CONFIG["music_folder"], 
                            ['.mp3', '.wav', '.m4a'], 
                            sequential_tracking_file, 
                            "music:main"
                        )
                    else:  # Default to random
                        music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                        
                    if music_path:
                        logging.info(f"Fallback: Found music in main music folder")
        else:
            # Try the original mood name
            if os.path.exists(original_mood_dir) and os.path.isdir(original_mood_dir):
                if file_selection_mode == "sequential":
                    music_path = get_sequential_file(
                        original_mood_dir, 
                        ['.mp3', '.wav', '.m4a'], 
                        sequential_tracking_file, 
                        f"music:{mood}"
                    )
                else:  # Default to random
                    music_path = get_random_file(original_mood_dir, ['.mp3', '.wav', '.m4a'])
                    
                if music_path:
                    logging.info(f"Found music in original mood folder: {original_mood_dir}")
                else:
                    # Fallback to main music directory
                    if file_selection_mode == "sequential":
                        music_path = get_sequential_file(
                            STORY_CONFIG["music_folder"], 
                            ['.mp3', '.wav', '.m4a'], 
                            sequential_tracking_file, 
                            "music:main"
                        )
                    else:  # Default to random
                        music_path = get_random_file(STORY_CONFIG["music_folder"], ['.mp3', '.wav', '.m4a'])
                        
                    if music_path:
                        logging.info(f"Fallback: Found music in main music folder")
            else:
                # Fallback to main music directory
                if file_selection_mode == "sequential":
                    music_path = get_sequential_file(
                        STORY_CONFIG["music_folder"], 
                        ['.mp3', '.wav', '.m4a'], 
                        sequential_tracking_file, 
                        "music:main"
                    )
                else:  # Default to random
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