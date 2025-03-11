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
    "music_folder": "assets/music",
    "output_folder": "output/ugc",
    "tts_files_folder": "output/ugc/tts_files",
    "font": "assets/fonts/BeVietnamPro-Bold.ttf",
    "font_size": 70,
    "text_color": "white",
    "background_color": "black",
    "num_videos": 1,
    "max_cta_videos": 3,
    "max_cta_duration": 60,
    "generate_all_combinations": False,
    "used_hooks_file": "content/used_hooks.txt",
    "video_list_file": "output/ugc/video_list.txt",
    "log_file": "output/ugc/video_creation.log",
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
    "font": "assets/fonts/BeVietnamPro-Medium.ttf",
    "heading_font_size": 80,
    "body_font_size": 60,
    "text_color": "white",
    "overlay_color": "black",
    "overlay_opacity": 0.6,
    "log_file": "output/stories/story_creation.log",
    "words_per_minute": 220,  # Average reading speed is 180
    "min_segment_duration": 3.0,  # Minimum seconds per segment
    "max_segment_duration": 8.0,  # Maximum seconds per segment
    "title_duration": 3.0,  # Duration for title display
    "title_position_y": None,  # Set to None to use automatic positioning in safe top area
    "segment_position_y": None,  # Set to None to use automatic vertical centering
    "max_chars_per_segment": 500,  # Maximum characters per segment
    "fade_duration": 0.2,  # Duration of fade in/out for segments
    "show_title_by_default": False,  # Whether to show title cards by default
    "one_sentence_per_segment": False,  # If True, keep each sentence on its own segment (up to char limit)
    "use_paragraphs_as_segments": True,  # Whether to use \n as segment breaks
    "minimum_segment_length": 130,  # Minimum characters for a segment (shorter ones get combined with next/prev)
    # TikTok safe margin settings (in pixels)
    "tiktok_margins": {
        "enabled": True,  # Whether to use TikTok-specific safe margins
        "top": 252,      # Top margin (scaled from 126px in 540x960)
        "bottom": 640,   # Bottom margin (scaled from 320px in 540x960)
        "left": 120,      # Left margin (scaled from 60px in 540x960)
        "right": 240,     # Right margin (scaled from 60px in 540x960)
        "horizontal_text_margin": 240,  # Total horizontal margin (left + right)
        "show_debug_visualization": False,  # Whether to show debug visualization of safe zones
    },
}

# API credentials from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Aria")
FAL_KEY = os.getenv("FAL_KEY", "") 