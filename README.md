# UGC Video Generator - customized

A Python script to automatically generate UGC (User Generated Content) style videos by combining hook videos, text overlays, TTS voiceover, product/CTA videos, and background music.

## Features

- Combines hook videos with text overlays
- Adds narration using ElevenLabs Text-to-Speech API
- Supports multiple CTA (Call to Action) videos with time limits
- Includes background music with balanced audio mixing
- Generates descriptive filenames with hook details for easy tracking
- Tracks used hooks to avoid repetition
- Maintains a log of generated videos

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
4. Copy `.env.sample` to `.env` and add your ElevenLabs API key:
   ```
   cp .env.sample .env
   # Then edit .env with your API credentials
   ```

## Directory Structure

Create the following folders in the same directory as the script:
```
UGCReelGen/
├── UGCReelGen.py
├── .env (your ElevenLabs API credentials)
├── hooks.csv
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
└── tts_files/
    └── (generated TTS audio files will be saved here for reference)
```

## Usage

1. Add your hook videos to the `hook_videos` folder (recommended size: 1080x1920)
2. Add your CTA videos to the `cta_videos` folder (must be 1080x1920 for best results)
3. Add background music to the `music` folder (.mp3, .wav, or .m4a)
4. Create a `hooks.csv` file with columns: `id,text` (see example below)
5. Run the script:
   ```
   python UGCReelGen.py
   ```

## hooks.csv Example

```
id,text
1,This simple hack saved me $500 on my electric bill
2,I never knew this trick for removing stains
3,The one thing most people forget when cleaning their kitchen
```

## Configuration

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

## ElevenLabs Integration

The script supports Text-to-Speech narration using the ElevenLabs API. To set up:

1. Create an account at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key from the ElevenLabs dashboard
3. Add it to your `.env` file:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ELEVENLABS_VOICE=Aria  # or any other available voice name
   ```

## Output Filenames

Videos are saved with descriptive filenames that include:
- Date (YYYYMMDD)
- Project name
- Sequential number
- Hook ID from CSV
- Hook summary (in camelCase)
- Hook video name
- Number of CTA videos used

Example: `20250307_ugcReelGen_005_h11_thisSimpleHack_ai_ugc_5_1cta.mp4`

## Output

- Generated videos are saved in the `final_videos` folder
- TTS audio files are saved in the `tts_files` folder
- A log file `video_creation.log` tracks the process
- `video_list.txt` contains details of all generated videos
- `used_hooks.txt` tracks which hooks have been used

## Notes

- For best results, ensure your CTA videos are exactly 1080x1920 resolution
- Hook videos will be automatically resized and cropped to fit
- The script will stop when all hooks have been used
- If audio issues occur, check that ffmpeg is properly installed and in your PATH
- TTS files are saved separately for quality verification

## License

MIT

---

This project is a fork of the original UGC Video Generator from [justshipthings.com](https://justshipthings.com), with additional features including ElevenLabs TTS integration, multiple CTA videos support, improved audio handling, and descriptive filenames.