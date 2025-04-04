#!/usr/bin/env python3
"""Shared utilities for content generators"""

import os
import logging
import csv
import json
import random
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import numpy as np

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    if isinstance(hex_color, str) and hex_color.startswith('#'):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return (r, g, b)
    return hex_color  # Return unchanged if not a hex color

def setup_directories(directories):
    """Create multiple directories if they don't exist"""
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Directory ensured: {directory}")

def load_csv(csv_path):
    """Load data from a CSV file"""
    if not os.path.exists(csv_path):
        logging.error(f"CSV file not found: {csv_path}")
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Get the raw content to check for newlines
        raw_content = f.read()
        f.seek(0)  # Reset the file pointer
        literal_n_count = raw_content.count('\\n')
        logging.info("Debug - Raw CSV contains %d occurrences of literal \\n", literal_n_count)
        
        # Print a sample of the raw content
        logging.info("Debug - Raw CSV sample: '%s'...", raw_content[:200])
        
        reader = csv.DictReader(f)
        for row in reader:
            # Add row ID for easier tracking in logs
            row_id = row.get('id', 'unknown')
            logging.info("Processing row ID: %s", row_id)
            
            # Process any needed field conversions
            if 'story_text' in row and row['story_text']:
                # Check for literal "\n" strings in the text
                text_length = len(row['story_text'])
                logging.info("Story text length: %d characters", text_length)
                literal_n_count = row['story_text'].count('\\n')
                logging.info("Literal \\n count in story_text: %d", literal_n_count)
                
                # Show more of the actual story text for debugging
                logging.info("Story text sample (first 200 chars): '%s'...", row['story_text'][:200])
                logging.info("Story text end (last 200 chars): '...%s'", row['story_text'][-200:])
                
                # Check if text appears truncated
                if "relationship?" not in row['story_text'] and len(row['story_text']) > 200:
                    logging.warning("Story text appears to be truncated! Missing expected ending.")
                
                # Do the replacement if found
                if literal_n_count > 0:
                    row['story_text'] = row['story_text'].replace('\\n', '\n')
                    actual_n_count = row['story_text'].count('\n')
                    logging.info("After replacement - actual newline count: %d", actual_n_count)
                
                # Also check for other newline formats
                if '\\r\\n' in row['story_text']:
                    logging.info("Found Windows-style newlines (\\r\\n)")
                    row['story_text'] = row['story_text'].replace('\\r\\n', '\n')
                
                # Also clean up the title if needed
                if 'title' in row and row['title']:
                    if '\\n' in row['title']:
                        logging.info("Found \\n in title, replacing")
                        row['title'] = row['title'].replace('\\n', '\n')
                    
            data.append(row)
    
    logging.info(f"Loaded {len(data)} rows from {csv_path}")
    return data

def save_to_csv(data, filepath, fieldnames=None):
    """Save data to a CSV file"""
    if not fieldnames and data:
        fieldnames = data[0].keys()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    logging.info(f"Saved {len(data)} rows to {filepath}")

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

def add_text_overlay(clip, text, font_path, font_size, position, color="white", 
                      stroke_color="black", stroke_width=2, config=None):
    """Add text overlay to video clip"""
    # Check if we have a config with TikTok margins
    if config and "tiktok_margins" in config:
        tiktok_margins = config.get("tiktok_margins", {})
        use_tiktok_margins = tiktok_margins.get("enabled", False)
        
        if use_tiktok_margins:
            horizontal_margin = tiktok_margins.get("horizontal_text_margin", 240)
        else:
            horizontal_margin = 120  # Default margin
    else:
        horizontal_margin = 120  # Default margin if no config provided
    
    text_width = clip.w - horizontal_margin
    
    # If position is a tuple with y-coordinate and we have TikTok margins,
    # ensure the position respects the safe area
    if config and "tiktok_margins" in config and isinstance(position, tuple) and len(position) == 2:
        tiktok_margins = config.get("tiktok_margins", {})
        use_tiktok_margins = tiktok_margins.get("enabled", False)
        
        if use_tiktok_margins:
            pos_x, pos_y = position
            
            # Ensure y position is within safe zone
            top_margin = tiktok_margins.get("top", 252)
            bottom_margin = tiktok_margins.get("bottom", 640)
            
            # Add some buffer from the edges
            buffer = 50
            
            # Adjust if too close to top or bottom
            if isinstance(pos_y, (int, float)):
                screen_height = clip.h
                min_y = top_margin + buffer
                max_y = screen_height - bottom_margin - buffer
                
                # Keep y position within safe area
                pos_y = max(min_y, min(pos_y, max_y))
                position = (pos_x, pos_y)
                
                logging.info(f"Adjusted text position to {position} to respect TikTok safe area")
    
    text_clip = TextClip(
        txt=text,
        fontsize=font_size,
        color=color,
        font=font_path,
        method='caption',
        size=(text_width, None),
        align='center',
        stroke_color=stroke_color,
        stroke_width=stroke_width
    ).set_duration(clip.duration).set_position(position)
    
    return CompositeVideoClip([clip, text_clip])

def get_random_file(directory, extensions=None):
    """Get a random file from a directory with specified extensions"""
    if extensions is None:
        extensions = ['.mp4', '.mov', '.mp3', '.wav', '.m4a']
    
    files = [f for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) and 
             any(f.lower().endswith(ext) for ext in extensions)]
    
    if not files:
        logging.warning(f"No files with extensions {extensions} found in {directory}")
        return None
    
    return os.path.join(directory, random.choice(files))

def get_sequential_file(directory, extensions=None, tracking_file=None, category="default"):
    """
    Get a file sequentially from a directory with specified extensions.
    Uses a tracking file to remember the last used index for each category.
    
    Args:
        directory (str): Directory containing files
        extensions (list): List of file extensions to include
        tracking_file (str): Path to a JSON file that tracks usage
        category (str): Category identifier (e.g., "background", "music") to track separately
        
    Returns:
        str: Path to the selected file
    """
    if extensions is None:
        extensions = ['.mp4', '.mov', '.mp3', '.wav', '.m4a']
    
    # Get list of eligible files
    files = [f for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) and 
             any(f.lower().endswith(ext) for ext in extensions)]
    
    if not files:
        logging.warning(f"No files with extensions {extensions} found in {directory}")
        return None
    
    # Sort files to ensure consistent ordering
    files.sort()
    
    # Initialize or load the tracking data
    tracking_data = {}
    if tracking_file and os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logging.warning(f"Could not load tracking file {tracking_file}, creating new")
            tracking_data = {}
    
    # Get the current index for this category and directory
    category_key = f"{category}:{directory}"
    current_index = tracking_data.get(category_key, -1)
    
    # Get the next file index (cycle back to 0 if we've used all files)
    next_index = (current_index + 1) % len(files)
    selected_file = files[next_index]
    
    # Update and save tracking data
    tracking_data[category_key] = next_index
    
    if tracking_file:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
        with open(tracking_file, 'w') as f:
            json.dump(tracking_data, f)
    
    logging.info(f"Sequential selection: {category} file {next_index+1}/{len(files)}: {selected_file}")
    return os.path.join(directory, selected_file)

def load_used_items(file_path):
    """Load used items from a file"""
    used_items = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            used_items = [line.strip() for line in f.readlines()]
    return used_items

def save_used_item(file_path, item):
    """Save an item to the used items file"""
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"{item}\n")

def position_text_in_tiktok_safe_area(text_clip, tiktok_margins, target_resolution, position_factor=0.33):
    """
    Position text within TikTok's safe area with precise control.
    
    Args:
        text_clip (TextClip): The text clip to position
        tiktok_margins (dict): Dictionary with top, bottom, left, right margins
        target_resolution (tuple): (width, height) of the video
        position_factor (float): Position factor within safe area (0.0=top, 1.0=bottom)
                                Default is 0.33 (1/3 from the top)
    
    Returns:
        TextClip: The text clip with position set
    """
    width, height = target_resolution
    
    # Calculate safe area boundaries
    safe_top = tiktok_margins.get("top", 252)
    safe_bottom = height - tiktok_margins.get("bottom", 640)
    safe_left = tiktok_margins.get("left", 120)
    safe_right = width - tiktok_margins.get("right", 240)
    
    # Calculate safe area height and width
    safe_height = safe_bottom - safe_top
    safe_width = safe_right - safe_left
    
    # Get the height and width of the text clip
    text_height = text_clip.h
    text_width = text_clip.w
    
    # Calculate the y position based on the position factor
    # This places the TOP of the text at the specified position factor
    y_position = int(safe_top + (safe_height * position_factor))
    
    # Make sure text stays within safe area (including its full height)
    max_y = safe_bottom - text_height
    y_position = min(max_y, max(safe_top, y_position))
    
    # Calculate the x position to center the text within the safe area
    # This accounts for asymmetric margins by using the safe area boundaries
    x_position = safe_left + (safe_width - text_width) / 2
    
    logging.info(f"Positioning text in safe area at ({x_position}, {y_position})")
    
    # Set position with exact coordinates
    return text_clip.set_position((x_position, y_position))

def visualize_safe_area(clip, tiktok_margins, target_resolution, duration=None):
    """
    Add visualization of TikTok safe area to a clip for debugging purposes.
    
    Args:
        clip (VideoClip): The base video clip
        tiktok_margins (dict): Dictionary with top, bottom, left, right margins
        target_resolution (tuple): (width, height) of the video
        duration (float, optional): Duration override for the visualization
    
    Returns:
        CompositeVideoClip: Clip with safe area visualization overlaid
    """
    from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, ImageClip
    
    width, height = target_resolution
    
    # Calculate safe area boundaries
    safe_top = tiktok_margins.get("top", 252)
    safe_bottom = height - tiktok_margins.get("bottom", 640)
    safe_left = tiktok_margins.get("left", 120)
    safe_right = width - tiktok_margins.get("right", 240)
    
    # Create a transparent image for the safe area boundaries
    safe_img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Draw safe area boundaries as red lines
    # Top boundary
    safe_img[safe_top, safe_left:safe_right, 0] = 255  # Red
    safe_img[safe_top, safe_left:safe_right, 3] = 255  # Opaque
    
    # Bottom boundary
    safe_img[safe_bottom, safe_left:safe_right, 0] = 255
    safe_img[safe_bottom, safe_left:safe_right, 3] = 255
    
    # Left boundary
    safe_img[safe_top:safe_bottom, safe_left, 0] = 255
    safe_img[safe_top:safe_bottom, safe_left, 3] = 255
    
    # Right boundary
    safe_img[safe_top:safe_bottom, safe_right, 0] = 255
    safe_img[safe_top:safe_bottom, safe_right, 3] = 255
    
    # Create visualization clip
    duration = duration or clip.duration
    safe_clip = ImageClip(safe_img).set_duration(duration)
    
    # Add labels for safe areas
    top_label = TextClip(
        f"Safe Top: {safe_top}px", 
        fontsize=20, 
        color="red",
        font="Arial"
    ).set_duration(duration).set_position((safe_left + 10, safe_top - 30))
    
    bottom_label = TextClip(
        f"Safe Bottom: {safe_bottom}px", 
        fontsize=20, 
        color="red",
        font="Arial"
    ).set_duration(duration).set_position((safe_left + 10, safe_bottom + 5))
    
    # Combine clips
    return CompositeVideoClip([clip, safe_clip, top_label, bottom_label])

def apply_iphone_metadata(video_path, temp_path=None):
    """
    Apply iPhone-style metadata to a video file using exiftool.
    
    This function adds metadata to make videos appear as if they were recorded
    on an iPhone, including device information and encoding details.
    Geolocation data is intentionally omitted.
    
    Args:
        video_path (str): Path to the video file
        temp_path (str, optional): Temporary file path for processing
                                  If None, a temp path will be created
    
    Returns:
        str: Path to the processed video file with iPhone metadata
    """
    import subprocess
    import os
    from datetime import datetime
    
    # Generate a temp path if not provided
    if temp_path is None:
        base, ext = os.path.splitext(video_path)
        temp_path = f"{base}_temp{ext}"
    
    # Rename original file to temp path if needed
    if os.path.exists(video_path) and not os.path.exists(temp_path):
        os.rename(video_path, temp_path)
    
    # Current date in proper format for exiftool
    current_date = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
    
    # Define exiftool command with iPhone metadata
    exiftool_cmd = [
        "exiftool",
        # Device info
        "-Make=Apple",
        "-Model=iPhone 14 Pro",
        "-Software=18.3.1",
        "-LensModel=iPhone 14 Pro back camera 6.86mm f/1.78",
        "-FocalLengthIn35mmFormat=24",
        
        # Video properties
        "-VideoFrameRate=24",
        "-Rotation=0",  # We're directly creating vertical video
        
        # Date information
        "-CreateDate=" + current_date,
        "-ModifyDate=" + current_date,
        "-TrackCreateDate=" + current_date,
        "-TrackModifyDate=" + current_date,
        "-MediaCreateDate=" + current_date,
        "-MediaModifyDate=" + current_date,
        
        # Audio properties
        "-AudioChannels=2",
        "-AudioSampleRate=44100",
        
        # QuickTime specific tags
        "-QuickTime:Make=Apple",
        "-QuickTime:Model=iPhone 14 Pro",
        "-QuickTime:Software=18.3.1",
        "-CompressorName=HEVC",
        "-CompressorID=hvc1",
        
        # Output settings
        "-o", video_path,
        temp_path
    ]
    
    try:
        logging.info("Applying iPhone metadata with exiftool")
        result = subprocess.run(exiftool_cmd, check=True, capture_output=True, text=True)
        
        if result.stderr:
            logging.warning(f"Exiftool warnings: {result.stderr}")
        
        logging.info("Successfully applied iPhone metadata")
        
        # Clean up temp file if successful
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return video_path
        
    except Exception as e:
        logging.error(f"Failed to apply iPhone metadata: {e}")
        
        # Restore original file if metadata application failed
        if os.path.exists(temp_path):
            if os.path.exists(video_path):
                os.remove(video_path)
            os.rename(temp_path, video_path)
            
        return video_path 