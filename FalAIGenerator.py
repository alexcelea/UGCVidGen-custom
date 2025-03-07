#!/usr/bin/env python3
# FalAIGenerator.py - Generate images and videos using Fal AI
import os
import csv
import json
import time
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import fal_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---- Configuration ----
DEFAULT_IMAGE_MODEL = "fal-ai/flux/dev"
DEFAULT_VIDEO_MODEL = "fal-ai/minimax-video/image-to-video"
DEFAULT_OUTPUT_DIR = "ai_generated"
DEFAULT_CSV_FILE = "ai_prompts.csv"
DEFAULT_BATCH_SIZE = 5  # Number of prompts to process in a batch before pausing

# ---- Helper Functions ----
def setup_directories(base_dir):
    """Create output directories if they don't exist"""
    dirs = {
        'images': os.path.join(base_dir, 'images'),
        'videos': os.path.join(base_dir, 'videos'),
        'logs': os.path.join(base_dir, 'logs')
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return dirs

def validate_env():
    """Validate that required environment variables are set"""
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        print("Error: FAL_KEY not found in .env file")
        print("Please add your Fal AI API key to the .env file:")
        print("FAL_KEY=your_api_key_here")
        return False
    return True

def load_prompts(csv_path):
    """Load prompts from CSV file"""
    if not os.path.exists(csv_path):
        print(f"Error: CSV file {csv_path} not found")
        return []
    
    prompts = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Validate required fields
                if 'id' not in row or 'type' not in row or 'prompt' not in row:
                    print(f"Warning: Row missing required fields (id, type, prompt): {row}")
                    continue
                
                # Parse params if they exist
                if 'params' in row and row['params']:
                    try:
                        row['params'] = json.loads(row['params'])
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse params JSON for row {row['id']}")
                        row['params'] = {}
                else:
                    row['params'] = {}
                
                # Set default model if not specified
                if 'model' not in row or not row['model']:
                    if row['type'] == 'image':
                        row['model'] = DEFAULT_IMAGE_MODEL
                    elif row['type'] == 'video':
                        row['model'] = DEFAULT_VIDEO_MODEL
                
                prompts.append(row)
        
        print(f"Loaded {len(prompts)} prompts from {csv_path}")
        return prompts
    except Exception as e:
        print(f"Error loading prompts from CSV: {e}")
        return []

def on_queue_update(update):
    """Callback for progress updates from Fal AI"""
    if hasattr(update, 'logs') and update.logs:
        for log in update.logs:
            print(f"  Progress: {log['message']}")

def save_image(result, prompt_data, output_dir, prompt_id):
    """Save generated image(s) to output directory"""
    image_dir = os.path.join(output_dir, 'images')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    saved_files = []
    
    # Handle different result formats based on the model
    if 'images' in result:
        # Handle flux model format
        for i, img_data in enumerate(result['images']):
            if 'url' in img_data:
                # Create filename
                ext = os.path.splitext(img_data['url'])[1] or '.png'
                filename = f"{timestamp}_{prompt_id}_{i}{ext}"
                filepath = os.path.join(image_dir, filename)
                
                # Save image URL to file for reference
                with open(f"{filepath}.json", 'w') as f:
                    json.dump({
                        'prompt': prompt_data['prompt'],
                        'model': prompt_data['model'],
                        'params': prompt_data['params'],
                        'image_url': img_data['url'],
                        'generated_at': timestamp
                    }, f, indent=2)
                
                print(f"  Image available at: {img_data['url']}")
                saved_files.append({'url': img_data['url'], 'metadata': f"{filepath}.json"})
    
    elif 'image' in result and 'url' in result['image']:
        # Handle single image result format
        url = result['image']['url']
        ext = os.path.splitext(url)[1] or '.png'
        filename = f"{timestamp}_{prompt_id}{ext}"
        filepath = os.path.join(image_dir, filename)
        
        # Save image URL to file for reference
        with open(f"{filepath}.json", 'w') as f:
            json.dump({
                'prompt': prompt_data['prompt'],
                'model': prompt_data['model'],
                'params': prompt_data['params'],
                'image_url': url,
                'generated_at': timestamp
            }, f, indent=2)
        
        print(f"  Image available at: {url}")
        saved_files.append({'url': url, 'metadata': f"{filepath}.json"})
    
    else:
        print(f"  Warning: Unexpected result format: {result}")
    
    # Return list of saved files
    return saved_files

def save_video(result, prompt_data, output_dir, prompt_id):
    """Save generated video(s) to output directory"""
    video_dir = os.path.join(output_dir, 'videos')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    saved_files = []
    
    # Handle different result formats based on the model
    if 'video' in result and 'url' in result['video']:
        # Handle video result
        url = result['video']['url']
        ext = os.path.splitext(url)[1] or '.mp4'
        filename = f"{timestamp}_{prompt_id}{ext}"
        filepath = os.path.join(video_dir, filename)
        
        # Save video URL to file for reference
        with open(f"{filepath}.json", 'w') as f:
            json.dump({
                'prompt': prompt_data['prompt'],
                'model': prompt_data['model'],
                'params': prompt_data['params'],
                'video_url': url,
                'generated_at': timestamp
            }, f, indent=2)
        
        print(f"  Video available at: {url}")
        saved_files.append({'url': url, 'metadata': f"{filepath}.json"})
    
    elif 'videos' in result:
        # Handle multiple videos result
        for i, video_data in enumerate(result['videos']):
            if 'url' in video_data:
                ext = os.path.splitext(video_data['url'])[1] or '.mp4'
                filename = f"{timestamp}_{prompt_id}_{i}{ext}"
                filepath = os.path.join(video_dir, filename)
                
                # Save video URL to file for reference
                with open(f"{filepath}.json", 'w') as f:
                    json.dump({
                        'prompt': prompt_data['prompt'],
                        'model': prompt_data['model'],
                        'params': prompt_data['params'],
                        'video_url': video_data['url'],
                        'generated_at': timestamp
                    }, f, indent=2)
                
                print(f"  Video available at: {video_data['url']}")
                saved_files.append({'url': video_data['url'], 'metadata': f"{filepath}.json"})
    
    else:
        print(f"  Warning: Unexpected result format for video: {result}")
    
    # Return list of saved files
    return saved_files

def generate_image(prompt_data, output_dir):
    """Generate image with Fal AI"""
    prompt_id = prompt_data['id']
    prompt_text = prompt_data['prompt']
    model = prompt_data['model']
    params = prompt_data['params']
    
    print(f"\nGenerating image for prompt #{prompt_id}:")
    print(f"  Prompt: {prompt_text}")
    print(f"  Model: {model}")
    
    # Set up default parameters if not provided
    if not params:
        params = {}
    
    # Add default image parameters if not specified
    if 'image_size' not in params:
        params['image_size'] = 'portrait_9_16'  # Vertical video format
    if 'num_images' not in params:
        params['num_images'] = 2  # Generate 2 images by default
    
    # Add prompt to params
    args = {"prompt": prompt_text, **params}
    
    try:
        result = fal_client.subscribe(
            model,
            arguments=args,
            with_logs=True,
            on_queue_update=on_queue_update
        )
        
        # Save results
        saved_files = save_image(result, prompt_data, output_dir, prompt_id)
        return saved_files
    except Exception as e:
        print(f"  Error generating image: {str(e)}")
        return []

def generate_video(prompt_data, output_dir):
    """Generate video with Fal AI"""
    prompt_id = prompt_data['id']
    prompt_text = prompt_data['prompt']
    model = prompt_data['model']
    params = prompt_data['params']
    
    print(f"\nGenerating video for prompt #{prompt_id}:")
    print(f"  Prompt: {prompt_text}")
    print(f"  Model: {model}")
    
    # Set up parameters
    if not params:
        params = {}
    
    # For minimax-video model, we need an image or image_url
    if model == "fal-ai/minimax-video/image-to-video":
        if 'image_url' not in params:
            # We need to generate an image first
            print("  No image_url provided, generating image first using flux model...")
            
            # Create temporary image prompt data
            image_prompt_data = {
                'id': f"{prompt_id}_img",
                'type': 'image',
                'prompt': prompt_text,
                'model': DEFAULT_IMAGE_MODEL,
                'params': {
                    'image_size': 'portrait_9_16',
                    'num_images': 1
                }
            }
            
            # Generate the image
            image_results = generate_image(image_prompt_data, output_dir)
            
            if image_results and 'url' in image_results[0]:
                # Use the generated image URL for the video
                params['image_url'] = image_results[0]['url']
            else:
                print("  Error: Failed to generate image for video")
                return []
    
    # Add prompt to params
    args = {"prompt": prompt_text, **params}
    
    try:
        result = fal_client.subscribe(
            model,
            arguments=args,
            with_logs=True,
            on_queue_update=on_queue_update
        )
        
        # Save results
        saved_files = save_video(result, prompt_data, output_dir, prompt_id)
        return saved_files
    except Exception as e:
        print(f"  Error generating video: {str(e)}")
        return []

def save_summary(results, output_dir):
    """Save a summary of generated content"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = os.path.join(output_dir, 'logs', f"summary_{timestamp}.json")
    
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSummary saved to: {summary_path}")

def generate_csv_template(output_path):
    """Generate a template CSV file with example prompts"""
    if os.path.exists(output_path) and not args.force:
        print(f"File {output_path} already exists. Use --force to overwrite.")
        return False
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'type', 'prompt', 'model', 'params'])
        writer.writerow(['1', 'image', 'A person excitedly looking at their phone with a surprised expression', 'fal-ai/flux/dev', '{"image_size": "portrait_9_16", "num_images": 2}'])
        writer.writerow(['2', 'video', 'A stylish person walking through a busy mall looking at their phone', 'fal-ai/minimax-video/image-to-video', '{}'])
        writer.writerow(['3', 'image', 'Close-up of hands typing on laptop with coffee mug nearby', 'fal-ai/recraft-v3', '{"image_size": "portrait_9_16", "num_images": 1}'])
    
    print(f"Template CSV created at: {output_path}")
    print("Edit this file to add your own prompts, then run the generator.")
    return True

# ---- Main Application ----
def main():
    """Main function to process prompts and generate content"""
    # Validate environment
    if not validate_env():
        return
    
    # Create template if requested
    if args.create_template:
        generate_csv_template(args.csv)
        return
    
    # Set up directories
    dirs = setup_directories(args.output_dir)
    
    # Load prompts
    prompts = load_prompts(args.csv)
    if not prompts:
        return
    
    # Filter prompts by type if specified
    if args.type != 'all':
        prompts = [p for p in prompts if p['type'] == args.type]
        print(f"Filtered to {len(prompts)} {args.type} prompts")
    
    # Filter prompts by ID if specified
    if args.id:
        prompts = [p for p in prompts if p['id'] == args.id]
        print(f"Filtered to prompt with ID {args.id}")
    
    # Filter prompts by batch if specified
    if args.batch > 0:
        start_idx = (args.batch - 1) * args.batch_size
        end_idx = start_idx + args.batch_size
        batch_prompts = prompts[start_idx:end_idx]
        print(f"Processing batch {args.batch}: prompts {start_idx+1} to {min(end_idx, len(prompts))}")
        prompts = batch_prompts
    
    # Check if we have any prompts to process
    if not prompts:
        print("No prompts to process after filtering. Exiting.")
        return
    
    # Process prompts
    results = []
    for i, prompt in enumerate(prompts):
        print(f"\n--- Processing prompt {i+1}/{len(prompts)} ---")
        
        try:
            if prompt['type'] == 'image':
                files = generate_image(prompt, args.output_dir)
            elif prompt['type'] == 'video':
                files = generate_video(prompt, args.output_dir)
            else:
                print(f"Unsupported type: {prompt['type']}")
                files = []
            
            results.append({
                'prompt_id': prompt['id'],
                'type': prompt['type'],
                'prompt': prompt['prompt'],
                'model': prompt['model'],
                'files': files
            })
            
            # Small delay between prompts to avoid rate limiting
            if i < len(prompts) - 1:
                time.sleep(1)
        
        except Exception as e:
            print(f"Error processing prompt {prompt['id']}: {e}")
    
    # Save summary
    save_summary(results, args.output_dir)
    
    print("\nContent generation complete!")
    print(f"Generated {len(results)} items")
    print(f"Check {args.output_dir} for the generated content")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate images and videos using Fal AI")
    parser.add_argument("--csv", default=DEFAULT_CSV_FILE, help="CSV file with prompts")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--type", choices=["all", "image", "video"], default="all", 
                        help="Type of content to generate")
    parser.add_argument("--id", help="Process only the prompt with this ID")
    parser.add_argument("--batch", type=int, default=0, 
                        help="Process a specific batch of prompts")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="Number of prompts per batch")
    parser.add_argument("--create-template", action="store_true",
                        help="Create a template CSV file")
    parser.add_argument("--force", action="store_true",
                        help="Force overwrite existing files")
    
    args = parser.parse_args()
    
    main() 