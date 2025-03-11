#!/usr/bin/env python3
"""Shared utilities for content generators"""

import os
import logging
import csv
import json
import random
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

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
        reader = csv.DictReader(f)
        for row in reader:
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
                      stroke_color="black", stroke_width=2):
    """Add text overlay to video clip"""
    text_width = clip.w - 120  # Add margin
    
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