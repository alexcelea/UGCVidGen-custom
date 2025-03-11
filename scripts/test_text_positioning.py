#!/usr/bin/env python3
"""
Test script to visualize text positioning and safe zones for TikTok videos.
This helps debug where text is actually being positioned.
"""

import os
import sys
import numpy as np
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, ImageClip

# Add the parent directory to the path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TARGET_RESOLUTION
from scripts.utils import visualize_safe_area

# Use absolute path for output to ensure consistent location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DEFAULT_OUTPUT_PATH = os.path.join(PROJECT_DIR, "output", "text_position_test.mp4")

def create_test_video(output_path=DEFAULT_OUTPUT_PATH):
    """Create a test video showing safe zones and text positioning"""
    # TikTok safe margins as specified
    margins = {
        "top": 252,
        "bottom": 640,
        "left": 120, 
        "right": 240,
        "enabled": True,
        "show_debug_visualization": True
    }
    
    # Create base clip with visualization grid
    width, height = TARGET_RESOLUTION
    duration = 5.0
    
    # Base clip with dark background
    base = ColorClip(size=(width, height), color=(20, 20, 20), duration=duration)
    
    # Create grid for visualization
    grid_img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Draw horizontal lines every 100px
    for y in range(0, height, 100):
        grid_img[y, :, 0:3] = 255  # White line
        grid_img[y, :, 3] = 50     # Semi-transparent
        
        # Create y-coordinate labels
        label = TextClip(str(y), fontsize=24, color="white", font="Arial")
        label = label.set_duration(duration).set_position((10, y))
        base = CompositeVideoClip([base, label.set_start(0)])
    
    # Add the grid
    grid_clip = ImageClip(grid_img).set_duration(duration)
    base = CompositeVideoClip([base, grid_clip])
    
    # Apply safe area visualization using our utility function
    base = visualize_safe_area(base, margins, TARGET_RESOLUTION)
    
    # Calculate safe zone boundaries
    safe_top = margins["top"]
    safe_bottom = height - margins["bottom"]
    safe_left = margins["left"]
    safe_right = width - margins["right"]
    
    # Calculate safe area height and width
    safe_height = safe_bottom - safe_top
    safe_width = safe_right - safe_left
    
    # Calculate the horizontal center of the safe area
    safe_center_x = safe_left + (safe_width / 2)
    
    # Draw vertical line at the safe area center
    center_line_img = np.zeros((height, width, 4), dtype=np.uint8)
    center_line_img[:, int(safe_center_x), 1] = 255  # Green line
    center_line_img[:, int(safe_center_x), 3] = 128  # Semi-transparent
    center_line_clip = ImageClip(center_line_img).set_duration(duration)
    
    # Add a label for the safe area center
    center_label = TextClip(f"Safe Area Center: {int(safe_center_x)}px", 
                          fontsize=24, color="green", font="Arial")
    center_label = center_label.set_duration(duration).set_position((int(safe_center_x) + 10, 50))
    
    base = CompositeVideoClip([base, center_line_clip, center_label])
    
    # Also show the screen center for comparison
    screen_center_x = width / 2
    screen_center_img = np.zeros((height, width, 4), dtype=np.uint8)
    screen_center_img[:, int(screen_center_x), 2] = 255  # Blue line
    screen_center_img[:, int(screen_center_x), 3] = 128  # Semi-transparent
    screen_center_clip = ImageClip(screen_center_img).set_duration(duration)
    
    screen_center_label = TextClip(f"Screen Center: {int(screen_center_x)}px", 
                                 fontsize=24, color="blue", font="Arial")
    screen_center_label = screen_center_label.set_duration(duration).set_position((int(screen_center_x) + 10, 80))
    
    base = CompositeVideoClip([base, screen_center_clip, screen_center_label])
    
    # Test different text positions within safe zone
    positions = [0.25, 0.33, 0.4, 0.5]
    text_clips = []
    
    for i, rel_pos in enumerate(positions):
        # Calculate absolute Y position (from top of screen)
        y_pos = int(safe_top + (safe_height * rel_pos))
        
        # Create text clip
        text = TextClip(
            f"Text at {rel_pos*100:.0f}% of safe area (Y={y_pos}px)", 
            fontsize=60, 
            color="white",
            font="Arial-Bold",
            method='caption',
            size=(safe_width, None),
            align='center'
        ).set_duration(duration)
        
        # Get the text height and width for positioning
        text_height = text.h
        text_width = text.w
        
        # Create a background for the text to better visualize its bounds
        bg_color = [50, 50, 150, 128]  # Semi-transparent blue
        text_bg = ColorClip(
            size=(text_width, text_height),
            color=bg_color
        ).set_duration(duration)
        
        # Position the text at the safe area center
        # Calculate the x position that centers the text in the safe area
        x_pos = safe_left + (safe_width - text_width) / 2
        
        # Position the text and its background
        text = text.set_position((x_pos, y_pos))
        text_bg = text_bg.set_position((x_pos, y_pos))
        
        # Add vertical indicator line to show exact placement
        indicator = TextClip(f"▼ {y_pos}px", fontsize=24, color="yellow", font="Arial")
        indicator = indicator.set_duration(duration).set_position((width - 150, y_pos - 30))
        
        text_clips.extend([text_bg, text, indicator])
        
        # Add a line indicating where text would be positioned with half-height offset
        half_height_pos = int(y_pos + (text_height / 2))
        if half_height_pos < safe_bottom:
            half_height_indicator = ColorClip(
                size=(width, 2), 
                color=[255, 255, 0, 128]  # Semi-transparent yellow
            ).set_duration(duration).set_position((0, half_height_pos))
            
            half_height_label = TextClip(
                f"Center: {half_height_pos}px", 
                fontsize=24, 
                color="yellow",
                font="Arial"
            ).set_duration(duration).set_position((width - 150, half_height_pos + 5))
            
            text_clips.extend([half_height_indicator, half_height_label])
    
    # Create final composite with all elements
    final = CompositeVideoClip([base] + text_clips)
    
    # Make sure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the test video
    final.write_videofile(output_path, fps=24, codec="libx264", audio=False)
    print(f"Test video created at: {output_path}")

if __name__ == "__main__":
    create_test_video() 