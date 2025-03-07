# UGC Video Generator - customized

A Python script to automatically generate UGC (User Generated Content) style videos by combining hook videos, text overlays, TTS voiceover, product/CTA videos, and background music.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Project Maintenance](#project-maintenance)
- [Directory Structure](#directory-structure)
- [Usage](#usage)
  - [Standard Video Generation](#standard-video-generation)
  - [AI Content Generation](#ai-content-generation)
- [Configuration Files](#configuration-files)
  - [hooks.csv Example](#hookscsv-example)
  - [ai_prompts.csv Example](#ai_promptscsv-example)
- [Configuration Options](#configuration-options)
- [API Integrations](#api-integrations)
- [Output Files](#output-files)
- [Workflow for AI-Enhanced Content](#workflow-for-ai-enhanced-content)
- [Notes and Best Practices](#notes-and-best-practices)
- [License](#license)

## Features

- Combines hook videos with text overlays
- Adds narration using ElevenLabs Text-to-Speech API
- Supports multiple CTA (Call to Action) videos with time limits
- Includes background music with balanced audio mixing
- Generates descriptive filenames with hook details for easy tracking
- Tracks used hooks to avoid repetition
- Maintains a log of generated videos
- AI-generated images and videos using Fal AI

## Requirements

- Python 3.11+ recommended
- FFmpeg installed on your system (required for audio/video processing)
- Required Python packages (install using `requirements.txt`)

## Installation

1. Clone this repository
2. Install FFmpeg:
   - Mac: `brew install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Linux: `sudo apt install ffmpeg`
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.sample` to `.env` and add your API keys:
   ```
   cp .env.sample .env
   # Then edit .env with your API keys
   ```
5. Set up the project maintenance scripts:
   ```
   # Make the scripts executable
   chmod +x project-start.sh project-end.sh
   ```

## Project Maintenance

This project includes two maintenance scripts to help manage generated content and keep your working environment clean.

### Starting a Project Session

Run the project-start.sh script when beginning to work:

```
./project-start.sh
```

This script will:
- Check and create all required directories
- Ensure your .gitignore is properly configured
- Manage log files from previous sessions
- Verify that environment files are set up
- Show the current state of your project

### Ending a Project Session

Run the project-end.sh script when finishing your work:

```
./project-end.sh
```

This script will:
- Check for running generator processes
- Ask which files you want to clean up:
  - TTS audio files
  - AI-generated images
  - AI-generated videos
  - Final output videos
  - Log files
- Show a summary of actions before execution
- Archive files before deletion if requested
- Clean up only the selected file types
- Show a final project status summary

These scripts help maintain a clean workspace while preserving your important project structure and ensuring generated files don't clutter your repository.

## Directory Structure

Create the following folders in the same directory as the script:
```
UGCReelGen/
├── UGCReelGen.py
├── FalAIGenerator.py (AI content generator script)
├── .env (your API credentials)
├── hooks.csv
├── ai_prompts.csv (prompts for AI content generation)
├── hook_videos/
│   └── (your hook videos here)
├── cta_videos/
│   └── (your CTA videos here)
├── music/
│   └── (your background music files here - any music you place here will be randomly picked and used) 
├── fonts/
│   └── BeVietnamPro-Bold.ttf (or your preferred font)
├── final_videos/
│   └── (generated videos will appear here)
├── tts_files/
│   └── (generated TTS audio files will be saved here for reference)
└── ai_generated/ (folder for AI-generated content)
    ├── images/
    ├── videos/
    └── logs/
```

## Usage

### Standard Video Generation

1. Add your hook videos to the `hook_videos` folder (recommended size: 1080x1920)
2. Add your CTA videos to the `cta_videos` folder (must be 1080x1920 for best results)
3. Add background music to the `music` folder (.mp3, .wav, or .m4a)
4. Create a `hooks.csv` file with columns: `id,text` (see example below)
5. Run the script:
   ```
   python UGCReelGen.py
   ```

### AI Content Generation

You can now generate hook videos and images using Fal AI's powerful models:

1. Ensure you have your Fal AI API key in `.env`: `FAL_KEY=your_fal_api_key_here`
2. Create or edit `ai_prompts.csv` with your desired prompts (see format below)
3. Run the AI generator:
   ```
   python FalAIGenerator.py
   ```
4. Review generated content in the `ai_generated` folder
5. Move selected content to your `hook_videos` folder for use with UGCReelGen

#### AI Generator Command-Line Options

```
python FalAIGenerator.py --help  # View all options

# Generate only images
python FalAIGenerator.py --type image

# Generate only videos
python FalAIGenerator.py --type video

# Create a template CSV file
python FalAIGenerator.py --create-template

# Process only a specific prompt by ID
python FalAIGenerator.py --id 5

# Process prompts in batches
python FalAIGenerator.py --batch 1 --batch-size 3
```

## Configuration Files

### hooks.csv Example

```
id,text
1,This simple hack saved me $500 on my electric bill
2,I never knew this trick for removing stains
3,The one thing most people forget when cleaning their kitchen
```

### ai_prompts.csv Example

```
id,type,prompt,model,params
1,image,"Person looking shocked at their electric bill, holding it up to camera","fal-ai/flux/dev","{""width"": 576, ""height"": 1024, ""num_images"": 2}"
2,video,"A stylish person walking through a busy mall looking at their phone","fal-ai/minimax-video/image-to-video","{}"
3,image,"Someone cleaning kitchen counter with a surprised look on their face","fal-ai/flux/dev","{""width"": 576, ""height"": 1024, ""num_images"": 2}"
```

Note: We use `width` and `height` parameters for true 9:16 vertical format (576x1024) instead of `image_size`.

## Configuration Options

You can modify these variables at the top of the script:

- `PROJECT_NAME`: Name of your project (used in filenames)
- `NUM_VIDEOS`: Number of videos to generate (default: 1)
- `FONT_SIZE`: Size of the text overlay (default: 70)
- `TEXT_COLOR`: Color of the text (default: "white")
- `FONT`: Path to the font file (default: "./fonts/BeVietnamPro-Bold.ttf")
- `GENERATE_ALL_COMBINATIONS`: Set to True to generate videos for every hook with every video (default: False)
- `MAX_CTA_VIDEOS`: Maximum number of CTA videos to use per final video (default: 3)
- `MAX_CTA_DURATION`: Maximum duration in seconds for all CTA videos combined (default: 60)
- `USE_ELEVENLABS`: Enable/disable ElevenLabs TTS (default: True)
- `SAVE_TTS_FILES`: Save TTS audio files for debugging (default: True)

## API Integrations

### ElevenLabs Integration

The script supports Text-to-Speech narration using the ElevenLabs API. To set up:

1. Create an account at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key from the ElevenLabs dashboard
3. Add it to your `.env` file:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ELEVENLABS_VOICE=Aria  # or any other available voice name
   ```

### Fal AI Integration

The FalAIGenerator script uses Fal AI to generate images and videos. To set up:

1. Create an account at [fal.ai](https://fal.ai)
2. Get your API key from the Fal AI dashboard
3. Add it to your `.env` file:
   ```
   FAL_KEY=your_fal_api_key_here
   ```

Default models include:
- `fal-ai/flux/dev`: Fast image generation
- `fal-ai/minimax-video/image-to-video`: Turn images into videos
- `fal-ai/recraft-v3`: High-quality image generation

## Output Files

- Generated videos are saved in the `final_videos` folder
- TTS audio files are saved in the `tts_files` folder
- AI-generated content is saved in the `ai_generated` folder
- A log file `video_creation.log` tracks the process
- `video_list.txt` contains details of all generated videos
- `used_hooks.txt` tracks which hooks have been used

### UGCReelGen Output Filenames
Videos are saved with descriptive filenames that include:
- Date (YYYYMMDD)
- Project name
- Sequential number
- Hook ID from CSV
- Hook summary (in camelCase)
- Hook video name
- Number of CTA videos used

Example: `20250307_ugcReelGen_005_h11_thisSimpleHack_ai_ugc_5_1cta.mp4`

### FalAIGenerator Output Filenames

The AI-generated content is organized as follows:

- **Filenames**: All generated files include the prompt ID in their filename for easy reference (format: `prompt{id}_{timestamp}.png` or `prompt{id}_{timestamp}.mp4`)
- **Logs**: Detailed summary logs are saved in the `ai_generated/logs` folder, containing complete metadata for all generated files

Instead of creating individual JSON files for each image/video, the system now saves comprehensive logs that include:
- Prompt ID and text
- Model used for generation 
- All parameters used
- Source URLs
- Local file paths
- Generation timestamps

This simpler approach keeps the image and video folders clean while maintaining all the important metadata in the logs.

## Workflow for AI-Enhanced Content

1. Review your hooks in hooks.csv
2. Create visual prompts in ai_prompts.csv that match your hook themes
3. Generate AI content using `python FalAIGenerator.py`
4. Review generated content and select the best options
5. Move selected content to your hook_videos folder
6. Run UGCReelGen.py as usual to create final videos

The content is generated with true 9:16 vertical format (576x1024) for perfect compatibility with social media platforms like TikTok and Instagram.

## Notes and Best Practices

- For best results, ensure your CTA videos are exactly 1080x1920 resolution
- Hook videos will be automatically resized and cropped to fit
- The script will stop when all hooks have been used
- If audio issues occur, check that ffmpeg is properly installed and in your PATH
- TTS files are saved separately for quality verification
- AI-generated videos may be short (typically 2-4 seconds) but will be looped to match TTS duration
- For high-quality results, review all generated AI content before using it in your final videos

## License

MIT

---

This project is a fork of the original UGC Video Generator from [justshipthings.com](https://justshipthings.com), with additional features including ElevenLabs TTS integration, multiple CTA videos support, improved audio handling, descriptive filenames, and Fal AI integration for AI-generated content.