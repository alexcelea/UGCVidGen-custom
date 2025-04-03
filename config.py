#!/usr/bin/env python3
"""Centralized configuration for content generators"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Common settings
PROJECT_NAME = "content-generator"
TARGET_RESOLUTION = (1080, 1920)  # Vertical video format
LOG_LEVEL = "INFO"

# UGC Generator settings
UGC_CONFIG = {
    "hooks_file": "content/hooks.csv",
    "hooks_videos_folder": "assets/videos/hooks",
    "cta_videos_folder": "assets/videos/ctas",
    "music_folder": "assets/music/instrumental_impact",
    "output_folder": "output/ugc",
    "tts_files_folder": "output/ugc/tts_files",
    "font": "assets/fonts/Lato-Black.ttf",
    "font_size": 70,
    "text_color": "white",
    "background_color": "black",
    "num_videos": 3,
    "max_cta_videos": 1,
    "max_cta_duration": 60,
    "generate_all_combinations": False,
    "used_hooks_file": "content/used_hooks.txt",
    "video_list_file": "output/ugc/video_list.txt",
    "log_file": "output/ugc/video_creation.log",
    # Asset selection settings
    "file_selection_mode": "random",  # Options: "random" (default) or "sequential"
    "music_selection_mode": "sequential",  # Options: "random" or "sequential" - can be different from file_selection_mode
    "sequential_tracking_file": "output/ugc/sequential_tracking.json",  # Tracking file for video assets
    "music_tracking_file": "output/music_tracking.json",  # Existing tracking file for music
    # TikTok safe margin settings (in pixels)
    "tiktok_margins": {
        "enabled": True,  # Whether to use TikTok-specific safe margins
        "top": 252,      # Top margin (scaled from 126px in 540x960)
        "bottom": 640,   # Bottom margin (scaled from 320px in 540x960)
        "left": 120,      # Left margin (scaled from 60px in 540x960)
        "right": 240,     # Right margin (scaled from 60px in 540x960)
        "horizontal_text_margin": 240,  # Total horizontal margin (left + right)
        "text_y_position": None,  # Set to None to use automatic vertical centering
        "show_debug_visualization": False,  # Whether to show debug visualization of safe zones
    },
}

# AI Generator settings
AI_CONFIG = {
    "prompts_file": "content/ai_prompts.csv",
    "output_dir": "output/ai_generated",
    "batch_size": 5,
    "default_image_model": "fal-ai/flux/dev",
    "default_video_model": "fal-ai/minimax-video/image-to-video",
    "log_dir": "output/ai_generated/logs",
}

# Story Generator settings (for future implementation)
STORY_CONFIG = {
    "stories_file": "content/stories.csv",
    "background_videos_folder": "assets/videos/backgrounds",
    "music_folder": "assets/music",
    "output_folder": "output/stories",
    
    # Story selection settings
    "story_selection": "all",  # Options: "random" (default) or "all" for stories.csv
    "duplicate_handling": "always_new",  # Options: "skip" or "always_new" (default)
    
    # Asset selection settings
    "file_selection_mode": "sequential",  # Options: "random" or "sequential"
    "sequential_tracking_file": "output/stories/sequential_tracking.json",  # Tracking file for sequential selection
    
    # Font settings with separate title/body styling
    "title_font": "assets/fonts/Karla-ExtraBold.ttf",
    "body_font": "assets/fonts/Karla-Medium.ttf",
    "font": "assets/fonts/Karla-Medium.ttf",  # Kept for backwards compatibility
    "heading_font_size": 54,  # Slightly larger for more prominence
    "body_font_size": 54,  # Slightly smaller for hierarchy
    
    # Color settings
    "title_color": "white",
    "body_color": "#EAEAEA",
    "text_color": "white",  # Kept for backwards compatibility
    
    # Text effect settings
    "text_effects": {
        "enabled": True,
        "title_shadow": True,
        "title_shadow_offset": 4,
        "title_shadow_color": "#3a1c71",
        "title_stroke_width": 1,
        "title_stroke_color": "#ff2956",
        "body_shadow": True,
        "body_shadow_offset": 3,
        "body_shadow_color": "#000000",
        "body_stroke_width": 1,
        "body_stroke_color": "#000000"
    },
    
    # Overlay effect settings
    "overlay_effects": {
        "global_opacity": 0.6,  # Master opacity control for all overlay effects
        "solid_color": "#000000",  # Color to use when gradient is disabled
        "gradient": {
            "enabled": False,  # Set to True to use gradient instead of solid color
            "start_color": "#3a1c71",
            "end_color": "#ff2956",
            "animation_speed": 0.1,  # Lower = slower animation
            "animation_enabled": True  # Set to True to animate the gradient
        },
        "noise": {
            "enabled": True,
            "opacity": 0.25
        }
    },
    
    # Background effect settings
    "background_effects": {
        "zoom": {
            "enabled": True,
            "factor": 1.1,  # How much to zoom by the end
            "direction": "in"  # "in" or "out"
        },
        "flip": {
            "enabled": True,  # Set to True to flip the background video
            "horizontal": True  # Flip horizontally to mirror the background
        }
    },
    
    "log_file": "output/stories/story_creation.log",
    "words_per_minute": 180,  # Average reading speed is 180
    "min_segment_duration": 1.0,  # Minimum seconds per segment
    "max_segment_duration": 8.0,  # Maximum seconds per segment
    "max_chars_per_segment": 500,  # Maximum characters per segment
    "one_sentence_per_segment": False,  # If True, keep each sentence on its own segment (up to char limit)
    "use_paragraphs_as_segments": True,  # Whether to use \n as segment breaks
    "minimum_segment_length": 130,  # Minimum characters for a segment (shorter ones get combined with next/prev)
    "title_duration": 3.0,  # Duration for title display
    "title_position_y": None,  # Set to None to use automatic positioning in safe top area
    "segment_position_y": None,  # Set to None to use automatic vertical centering
    "fade_duration": 0,  # Duration of fade in/out for segments
    "show_title_by_default": False,  # Whether to show title cards by default
    "title_own_segment": False,  # If True, title appears on its own card; if False, title combines with first segment
    # TikTok safe margin settings (in pixels)
    "tiktok_margins": {
        "enabled": True,  # True = TikTok-specific safe margins for 1080 x 1920 videos, False = center text
        "top": 292,      # Top margin 
        "bottom": 500,   # Bottom margin (reduced from 600 for more space)
        "left": 120,      # Left margin 
        "right": 240,     # Right margin 
        "horizontal_text_margin": 240,  # Total horizontal margin (left + right)
        "show_debug_visualization": False,  # Whether to show debug visualization of safe zones
    },
    
    # iPhone-style video settings
    "iphone_style": {
        "enabled": True,           # Enable/disable iPhone-style encoding and metadata
        "model": "iPhone 14 Pro",  # iPhone model to emulate
        "codec": "libx265",        # Video codec (HEVC)
        "use_mov_container": True, # Use .mov container instead of .mp4
        "bitrate": "16000k"        # Video bitrate
    },
}

# API credentials from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")

# ElevenLabs configuration
ELEVENLABS_CONFIG = {
    "voice": {
        "name": "pNInz6obpgDQGcFmaJgB",  # Primary voice to use (Adam Legacy voice id pNInz6obpgDQGcFmaJgB)
        "fallback_voices": ["Aria", "Rachel", "Domi"],  # Fallback voices in order of preference
        "model": "eleven_multilingual_v2",  # Updated to latest quality model
        "flash_model": "eleven_flash_v2",  # For low-latency needs
        "max_chars": 800,  # Maximum characters per generation
        "language": "en"  # Default language
    },
    "audio": {
        "volume": 1.5,  # Volume multiplier for TTS audio
        "save_raw_files": True,  # Whether to save raw TTS files for debugging
        "stability": 0.5,  # Voice stability (0-1)
        "similarity_boost": 0.75,  # Voice similarity boost (0-1)
        "fit_to_video": {
            "enabled": True,  # Whether to adjust audio speed to match video
            "max_speed_up": 1.3,  # Maximum speed multiplier 
            "min_speed_down": 1.0,  # Minimum speed multiplier 
            "preserve_pitch": True  # Whether to maintain pitch while changing speed
        }
    }
} 