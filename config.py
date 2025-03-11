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
    "heading_font_size": 70,
    "body_font_size": 50,
    "text_color": "white",
    "overlay_color": "black",
    "overlay_opacity": 0.6,
    "log_file": "output/stories/story_creation.log",
    "words_per_minute": 180,  # Average reading speed
    "min_segment_duration": 3.0,  # Minimum seconds per segment
    "max_segment_duration": 8.0,  # Maximum seconds per segment
    "title_duration": 3.0,  # Duration for title display
    "title_position_y": 200,  # Vertical position of title
    "segment_position_y": 500,  # Vertical position of story segments
    "max_chars_per_segment": 200,  # Maximum characters per segment
    "fade_duration": 0.5,  # Duration of fade in/out for segments
    "show_title_by_default": True,  # Whether to show title cards by default
    "one_sentence_per_segment": True,  # If True, keep each sentence on its own segment (up to char limit)
}

# API credentials from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Aria")
FAL_KEY = os.getenv("FAL_KEY", "") 