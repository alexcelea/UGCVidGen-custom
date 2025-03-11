#!/bin/bash

echo "🏁 Ending Content Generator session..."

# Define project-specific paths for generated content
OUTPUT_DIR="./output"
ASSETS_DIR="./assets"
CONTENT_DIR="./content"

# Define paths for different content types
UGC_OUTPUT="$OUTPUT_DIR/ugc"
STORIES_OUTPUT="$OUTPUT_DIR/stories" 
AI_GENERATED="$OUTPUT_DIR/ai_generated"
TTS_FILES="$UGC_OUTPUT/tts_files"
LOG_FILES=("$UGC_OUTPUT/video_creation.log" "$UGC_OUTPUT/video_list.txt" "$STORIES_OUTPUT/story_creation.log")

# Check for running processes
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️ Warning: Content generator processes are still running."
    echo "   Please wait for them to finish before cleaning up."
    echo "   Use 'ps aux | grep python' to check processes."
    exit 1
fi

# Show all generated content stats
echo -e "\n📊 Current Content Stats"
echo "==============================="
TTS_COUNT=$(find "$TTS_FILES" -type f -not -name '.gitkeep' | wc -l)
AI_IMAGES_COUNT=$(find "$AI_GENERATED/images" -type f -not -name '.gitkeep' | wc -l)
AI_VIDEOS_COUNT=$(find "$AI_GENERATED/videos" -type f -not -name '.gitkeep' | wc -l)
UGC_VIDEOS_COUNT=$(find "$UGC_OUTPUT" -name "*.mp4" | wc -l)
STORY_VIDEOS_COUNT=$(find "$STORIES_OUTPUT" -name "*.mp4" | wc -l)
HOOKS_COUNT=$(find "$ASSETS_DIR/videos/hooks" -type f -not -name '.gitkeep' | wc -l)
CTA_COUNT=$(find "$ASSETS_DIR/videos/ctas" -type f -not -name '.gitkeep' | wc -l)
BG_COUNT=$(find "$ASSETS_DIR/videos/backgrounds" -type f -not -name '.gitkeep' | wc -l)
USED_HOOKS_COUNT=$(wc -l < "$CONTENT_DIR/used_hooks.txt" 2>/dev/null || echo "0")

echo "📁 INPUT ASSETS:"
echo " - Used hooks: $USED_HOOKS_COUNT hooks"
echo " - Hook videos: $HOOKS_COUNT files"
echo " - CTA videos: $CTA_COUNT files"
echo " - Background videos: $BG_COUNT files"
echo ""
echo "🎬 GENERATED CONTENT:"
echo " - TTS files: $TTS_COUNT files"
echo " - AI generated images: $AI_IMAGES_COUNT files"
echo " - AI generated videos: $AI_VIDEOS_COUNT files"
echo " - UGC videos: $UGC_VIDEOS_COUNT files"
echo " - Story videos: $STORY_VIDEOS_COUNT files"
echo "==============================="

# Ask which files to clean up
echo -e "\n🧹 Cleanup Options"
echo "Which files would you like to clean up?"
echo "1. TTS files ($TTS_COUNT files)"
echo "2. AI generated images ($AI_IMAGES_COUNT files)"
echo "3. AI generated videos ($AI_VIDEOS_COUNT files)"
echo "4. UGC videos ($UGC_VIDEOS_COUNT files)"
echo "5. Story videos ($STORY_VIDEOS_COUNT files)"
echo "6. Log files"
echo "7. All files"
echo "8. Exit (no cleanup)"
echo ""
read -p "Enter your choice (1-8): " choice

# Process user selection
case $choice in
    1) selections=(0) ;;
    2) selections=(1) ;;
    3) selections=(2) ;;
    4) selections=(3) ;;
    5) selections=(4) ;;
    6) selections=(5) ;;
    7) selections=(0 1 2 3 4 5) ;;  # All files - include all indices
    8) echo "No files selected for cleanup. Exiting."; exit 0 ;;
    *) echo "Invalid choice. Exiting."; exit 1 ;;
esac

# Confirm cleanup
echo -e "\n🔍 Summary of actions to be performed:"
for i in "${selections[@]}"; do
    case $i in
        0) echo " - Clean TTS files ($TTS_COUNT files)" ;;
        1) echo " - Clean AI generated images ($AI_IMAGES_COUNT files)" ;;
        2) echo " - Clean AI generated videos ($AI_VIDEOS_COUNT files)" ;;
        3) echo " - Clean UGC videos ($UGC_VIDEOS_COUNT files)" ;;
        4) echo " - Clean Story videos ($STORY_VIDEOS_COUNT files)" ;;
        5) echo " - Clean log files" ;;
        6) echo " - Clean ALL files" ;;
    esac
done

read -p "Proceed with cleanup? This cannot be undone. (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Archive before deletion?
SHOULD_ARCHIVE=false
read -p "Would you like to archive files before deletion? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SHOULD_ARCHIVE=true
    ARCHIVE_DIR="./backups/archive_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$ARCHIVE_DIR"
    echo "Files will be archived to: $ARCHIVE_DIR"
fi

# Perform cleanup
echo "Cleaning up selected files..."

# Function to handle cleanup of a directory
cleanup_dir() {
    local dir=$1
    local archive_subdir=$2
    local file_pattern=$3
    
    # Skip if directory doesn't exist
    if [ ! -d "$dir" ]; then
        return
    fi
    
    # Archive if requested
    if [ "$SHOULD_ARCHIVE" = true ] && [ -d "$dir" ] && [ "$(ls -A $dir 2>/dev/null)" ]; then
        mkdir -p "$ARCHIVE_DIR/$archive_subdir"
        find "$dir" -type f -name "$file_pattern" -exec cp {} "$ARCHIVE_DIR/$archive_subdir/" \;
        echo "  Archived $(find "$dir" -type f -name "$file_pattern" | wc -l) files from $dir"
    fi
    
    # Delete files
    find "$dir" -type f -name "$file_pattern" -delete
    echo "  Cleaned $dir"
    
    # Recreate .gitkeep
    touch "$dir/.gitkeep" 2>/dev/null
}

# Process selections
for i in "${selections[@]}"; do
    case $i in
        0) 
            # TTS files
            cleanup_dir "$TTS_FILES" "tts_files" "*" 
            ;;
        1) 
            # AI generated images
            cleanup_dir "$AI_GENERATED/images" "ai_generated/images" "*" 
            ;;
        2) 
            # AI generated videos
            cleanup_dir "$AI_GENERATED/videos" "ai_generated/videos" "*" 
            ;;
        3) 
            # UGC videos
            cleanup_dir "$UGC_OUTPUT" "ugc" "*.mp4" 
            ;;
        4) 
            # Story videos
            cleanup_dir "$STORIES_OUTPUT" "stories" "*.mp4" 
            ;;
        5) 
            # Log files
            for log_file in "${LOG_FILES[@]}"; do
                if [ -f "$log_file" ]; then
                    # Archive if requested
                    if [ "$SHOULD_ARCHIVE" = true ]; then
                        log_dir=$(dirname "$log_file")
                        log_base=$(basename "$log_file")
                        mkdir -p "$ARCHIVE_DIR/logs/$(basename "$log_dir")"
                        cp "$log_file" "$ARCHIVE_DIR/logs/$(basename "$log_dir")/"
                    fi
                    
                    # Clear log file
                    > "$log_file"
                    echo "  Cleared $log_file"
                fi
            done
            ;;
    esac
done

# Final status report
echo -e "\n📊 Updated Content Stats"
echo "==============================="
# Get updated counts
TTS_COUNT=$(find "$TTS_FILES" -type f -not -name '.gitkeep' | wc -l)
AI_IMAGES_COUNT=$(find "$AI_GENERATED/images" -type f -not -name '.gitkeep' | wc -l)
AI_VIDEOS_COUNT=$(find "$AI_GENERATED/videos" -type f -not -name '.gitkeep' | wc -l)
UGC_VIDEOS_COUNT=$(find "$UGC_OUTPUT" -name "*.mp4" | wc -l)
STORY_VIDEOS_COUNT=$(find "$STORIES_OUTPUT" -name "*.mp4" | wc -l)
HOOKS_COUNT=$(find "$ASSETS_DIR/videos/hooks" -type f -not -name '.gitkeep' | wc -l)
CTA_COUNT=$(find "$ASSETS_DIR/videos/ctas" -type f -not -name '.gitkeep' | wc -l)
BG_COUNT=$(find "$ASSETS_DIR/videos/backgrounds" -type f -not -name '.gitkeep' | wc -l)
USED_HOOKS_COUNT=$(wc -l < "$CONTENT_DIR/used_hooks.txt" 2>/dev/null || echo "0")

echo "📁 INPUT ASSETS:"
echo " - Used hooks: $USED_HOOKS_COUNT hooks"
echo " - Hook videos: $HOOKS_COUNT files"
echo " - CTA videos: $CTA_COUNT files"
echo " - Background videos: $BG_COUNT files"
echo ""
echo "🎬 GENERATED CONTENT:"
echo " - TTS files: $TTS_COUNT files"
echo " - AI generated images: $AI_IMAGES_COUNT files"
echo " - AI generated videos: $AI_VIDEOS_COUNT files"
echo " - UGC videos: $UGC_VIDEOS_COUNT files"
echo " - Story videos: $STORY_VIDEOS_COUNT files"
echo "==============================="

if [ "$SHOULD_ARCHIVE" = true ]; then
    echo -e "\n📦 Archive Summary"
    echo "Archive location: $ARCHIVE_DIR"
    echo "Archive size: $(du -sh "$ARCHIVE_DIR" | cut -f1)"
fi

echo -e "\n✅ Cleanup complete. Project is ready for next session." 