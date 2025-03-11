# UGC Video Generator - customized

A Python toolkit to automatically generate different types of content videos, including UGC (User Generated Content) style videos and text-based storytelling videos.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
  - [Using the Unified Interface](#using-the-unified-interface)
  - [Project Workflow Scripts](#project-workflow-scripts)
  - [Standard UGC Video Generation](#standard-ugc-video-generation)
  - [AI Content Generation](#ai-content-generation)
  - [Story Video Generation](#story-video-generation)
- [Configuration Files](#configuration-files)
  - [hooks.csv Example](#hookscsv-example)
  - [ai_prompts.csv Example](#ai_promptscsv-example)
  - [stories.csv Example](#storiescsv-example)
- [Configuration Options](#configuration-options)
- [API Integrations](#api-integrations)
- [Output Files](#output-files)
- [Notes and Best Practices](#notes-and-best-practices)
- [License](#license)

## Features

- **UGC Video Generator**
  - Combines hook videos with text overlays
  - Adds narration using ElevenLabs Text-to-Speech API
  - Supports multiple CTA (Call to Action) videos with time limits
  - Includes background music with balanced audio mixing
  - Creates text overlays with subtle glow effects for better readability
  - Processes hook text from CSV and tracks used hooks to avoid repetition
- **AI Content Generator**
  - Generate images and videos using Fal AI
  - Multiple models supported for different visual styles
  - Batch processing capability
  - Can generate videos directly from prompts or from AI-generated images
  - Organizes content with detailed metadata for easy management
  - Downloads and saves results with descriptive filenames
- **Story Video Generator** 
  - Creates text-based storytelling videos
  - Dark overlay for text contrast
  - Segmented text display with timing
  - Theme-based background selection
  - Intelligently breaks stories into readable segments
  - Combines title and story segments with appropriate timing
- **Shared Features**
  - Descriptive filenames with content details
  - Tracking of used content to avoid repetition
  - Detailed logging
  - Background music integration

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

## Project Structure

The project has been reorganized to support multiple types of content generators:

```
UGCVidGen/                 # Project root directory
├── scripts/                # All generator scripts
│   ├── ugc_generator.py    # UGC hook video generator 
│   ├── ai_generator.py     # AI content generator
│   ├── story_generator.py  # Story video generator
│   └── utils.py            # Shared utility functions
│
├── content/                # Content data files
│   ├── hooks.csv           # UGC hooks
│   ├── ai_prompts.csv      # AI prompts
│   ├── stories.csv         # Story content
│   └── used_hooks.txt      # Tracking used hooks
│
├── assets/                 # All media assets
│   ├── videos/
│   │   ├── hooks/          # Hook videos
│   │   ├── ctas/           # CTA videos
│   │   └── backgrounds/    # Background videos for stories
│   ├── music/              # Background music files
│   └── fonts/              # Font files
│
├── output/                 # Generated content
│   ├── ugc/                # UGC output videos
│   │   ├── tts_files/      # TTS audio files
│   │   └── video_creation.log  # UGC generation log
│   ├── stories/            # Story output videos
│   │   └── story_creation.log  # Story generation log
│   └── ai_generated/       # AI-generated content
│       ├── images/
│       ├── videos/
│       └── logs/
│
├── backups/                # Backup directory for archives
│
├── project-start.sh        # Script to setup and start the project
├── project-end.sh          # Script to clean up and archive content
├── config.py               # Centralized configuration
├── main.py                 # Unified entry point
├── requirements.txt
└── README.md
```

## Usage

### Using the Unified Interface

The project now has a unified interface for generating all content types:

```bash
# Generate UGC videos (default)
python main.py --type ugc --count 3

# Generate story videos
python main.py --type story

# Generate AI content
python main.py --type ai --batch 1 --batch-size 5
```

### Project Workflow Scripts

The project includes two shell scripts to manage your content generation workflow:

- **project-start.sh**: Sets up the project structure, ensures all required directories exist, and displays current project status.
  ```bash
  # Start a new content generation session
  ./project-start.sh
  ```

- **project-end.sh**: Helps clean up generated files and provides options to archive content before deletion.
  ```bash
  # End a content generation session and clean up files
  ./project-end.sh
  ```
  This script provides options to:
  - Clean specific types of generated files
  - Clean all generated files at once
  - Archive files before deletion
  - View updated content statistics after cleanup

### Standard UGC Video Generation

1. Add your hook videos to the `assets/videos/hooks` folder
2. Add your CTA videos to the `assets/videos/ctas` folder
3. Add background music to the `assets/music` folder
4. Create or edit `content/hooks.csv` with your hook text
5. Run the generator:
   ```
   python main.py --type ugc
   ```

### AI Content Generation

You can generate hook videos and images using Fal AI:

1. Ensure you have your Fal AI API key in `.env`: `FAL_KEY=your_fal_api_key_here`
2. Create or edit `content/ai_prompts.csv` with your desired prompts
3. Run the AI generator:
   ```
   python main.py --type ai
   ```
4. Review generated content in the `output/ai_generated` folder
5. Move selected content to your `assets/videos/hooks` folder for use with the UGC generator

### Story Video Generation

1. Add background videos to the `assets/videos/backgrounds` folder
2. Create or edit `content/stories.csv` with your story content
3. Run the story generator:
   ```
   python main.py --type story
   ```

For thematic backgrounds, organize videos in theme subfolders:
```
assets/videos/backgrounds/urban/
assets/videos/backgrounds/nature/
assets/videos/backgrounds/minimal/
```

Similarly, for mood-based music:
```
assets/music/reflective/
assets/music/energetic/
assets/music/inspiring/
```

## Configuration Files

### hooks.csv Example

```csv
id,text
1,This simple hack saved me $500 on my electric bill
2,I never knew this trick for removing stains
3,The one thing most people forget when cleaning their kitchen
```

### ai_prompts.csv Example

```csv
id,type,prompt,model,params
1,image,"Person looking shocked at their electric bill, holding it up to camera","fal-ai/flux/dev","{""width"": 576, ""height"": 1024, ""num_images"": 2}"
2,video,"A stylish person walking through a busy mall looking at their phone","fal-ai/minimax-video/image-to-video","{}"
```

### stories.csv Example

```csv
id,title,story_text,background_theme,music_mood
1,"The Unexpected Gift","I never expected that a simple act of kindness would change my life. It was a rainy Tuesday when a stranger offered me their umbrella. It seemed small at the time, but that conversation led to a job opportunity that changed everything.",urban,reflective
2,"Morning Routine Hack","Most people waste the first hour of their day. Here's what successful people do differently: They don't check social media first thing. They drink a full glass of water. They write down three goals for the day. Try this for a week and watch what happens.",minimal,energetic
```

## Configuration Options

All configuration settings are now centralized in `config.py`:

- **Common Settings**
  - `PROJECT_NAME`: Name of your project (used in filenames)
  - `TARGET_RESOLUTION`: Video resolution (default: 1080x1920)

- **UGC Generator Settings**
  - `num_videos`: Number of videos to generate (default: 1)
  - `font_size`: Size of the text overlay (default: 70)
  - `max_cta_videos`: Maximum number of CTA videos to use (default: 3)
  - `max_cta_duration`: Maximum duration for CTA videos (default: 60)

- **Story Generator Settings**
  - `heading_font_size`: Size of the title text (default: 70)
  - `body_font_size`: Size of the story text (default: 50)
  - `overlay_opacity`: Opacity of the dark overlay (default: 0.6)

## API Integrations

### ElevenLabs Integration

To set up Text-to-Speech narration:

1. Create an account at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key from the ElevenLabs dashboard
3. Add it to your `.env` file:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ELEVENLABS_VOICE=Aria  # or any other available voice name
   ```

### Fal AI Integration

To set up AI image and video generation:

1. Create an account at [fal.ai](https://fal.ai)
2. Get your API key from the Fal AI dashboard
3. Add it to your `.env` file:
   ```
   FAL_KEY=your_fal_api_key_here
   ```

## Output Files

- UGC videos: `output/ugc/*.mp4`
- TTS audio files: `output/ugc/tts_files/*.mp3`
- Story videos: `output/stories/*.mp4`
- AI-generated content: `output/ai_generated/{images,videos}/*`
- Log files:
  - `output/ugc/video_creation.log` - UGC generation logs
  - `output/ugc/video_list.txt` - List of generated UGC videos
  - `output/stories/story_creation.log` - Story generation logs
  - `output/ai_generated/logs/*` - AI content generation logs
- Backups: If enabled during cleanup, archived content will be stored in `backups/archive_TIMESTAMP/`

## Notes and Best Practices

- For best results, ensure your videos are exactly 1080x1920 resolution
- Videos will be automatically resized and cropped to fit if necessary
- The UGC generator will stop when all hooks have been used
- If audio issues occur, check that ffmpeg is properly installed
- AI-generated videos may be short but will be looped to match TTS duration
- For story videos, keep stories concise for better readability

## License

MIT

---

This project is a fork of the original UGC Video Generator from [justshipthings.com](https://justshipthings.com), with additional features including the text-based storytelling system and modular architecture for future expansion.