# UGC Video Generator - customized

A Python script to automatically generate UGC (User Generated Content) style videos by combining hook videos, text overlays, CTA videos, and background music.

## Features

- Combines hook videos with text overlays
- Adds CTA (Call to Action) videos
- Includes background music
- Tracks used hooks to avoid repetition
- Maintains a log of generated videos

## Requirements

- Python 3.11+ recommended
- FFmpeg installed on your system
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

## Directory Structure

Create the following folders in the same directory as the script:
```
UGCReelGen/
├── UGCReelGen.py
├── hooks.csv
├── hook_videos/
│   └── (your hook videos here)
├── cta_videos/
│   └── (your CTA videos here)
├── music/
│   └── (your background music files here - any music you place here will be randomly picked and used) 
├── fonts/
│   └── BeVietnamPro-Bold.ttf (or your preferred font)
└── final_videos/
    └── (generated videos will appear here)
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

- `NUM_VIDEOS`: Number of videos to generate (default: 10)
- `FONT_SIZE`: Size of the text overlay (default: 70)
- `TEXT_COLOR`: Color of the text (default: "white")
- `FONT`: Path to the font file (default: "./fonts/BeVietnamPro-Bold.ttf")

## Output

- Generated videos are saved in the `final_videos` folder
- A log file `video_creation.log` tracks the process
- `video_list.txt` contains details of all generated videos
- `used_hooks.txt` tracks which hooks have been used

## Notes

- For best results, ensure your CTA videos are exactly 1080x1920 resolution
- Hook videos will be automatically resized and cropped to fit
- The script will stop when all hooks have been used

## License

MIT

---

For a more detailed guide, visit [justshipthings.com](https://justshipthings.com) 