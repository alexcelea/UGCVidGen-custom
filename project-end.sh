#!/bin/bash

echo "🏁 Ending UGC Video Generator session..."

# Define project-specific paths for generated content
TTS_FILES="./tts_files"
AI_GENERATED="./ai_generated"
FINAL_VIDEOS="./final_videos"
LOG_FILES=("video_creation.log" "video_list.txt" "used_hooks.txt")

# First, ensure .gitignore has these directories
if [ -f ".gitignore" ]; then
    MISSING_PATTERNS=()
    for pattern in "$TTS_FILES/*" "$AI_GENERATED/images/*" "$AI_GENERATED/videos/*" "$FINAL_VIDEOS/*" "${LOG_FILES[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            MISSING_PATTERNS+=("$pattern")
        fi
    done
    
    if [ ${#MISSING_PATTERNS[@]} -gt 0 ]; then
        echo "⚠️ Some generated files may not be in .gitignore:"
        for pattern in "${MISSING_PATTERNS[@]}"; do
            echo "  - $pattern"
        done
        echo "Consider adding these patterns to .gitignore to prevent accidental commits."
    fi
fi

# Check for running Python processes
RUNNING_PYTHON=$(ps aux | grep -E 'python.*UGCReelGen.py|python.*FalAIGenerator.py' | grep -v grep | wc -l)
if [[ $RUNNING_PYTHON -gt 0 ]]; then
    echo "⚠️ You have running UGC generator processes"
    ps aux | grep -E 'python.*UGCReelGen.py|python.*FalAIGenerator.py' | grep -v grep
    
    read -p "Would you like to terminate these processes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Attempt to gracefully terminate the processes
        ps aux | grep -E 'python.*UGCReelGen.py|python.*FalAIGenerator.py' | grep -v grep | awk '{print $2}' | xargs kill
        echo "✅ Terminated processes"
    fi
fi

# Initialize cleanup selections
ARCHIVE_FIRST=0
DELETE_TTS=0
DELETE_AI_IMAGES=0
DELETE_AI_VIDEOS=0
DELETE_FINAL_VIDEOS=0
CLEAR_LOGS=0

# Ask about archiving first
read -p "Would you like to archive current outputs before cleaning? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ARCHIVE_FIRST=1
fi

# Collect all cleanup choices without taking action yet
echo ""
echo "Select which files to delete (y/n for each):"

# TTS files
TTS_COUNT=$(find "$TTS_FILES" -type f -not -name '.gitkeep' | wc -l)
if [[ $TTS_COUNT -gt 0 ]]; then
    read -p "Delete TTS audio files? ($TTS_COUNT files) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        DELETE_TTS=1
    fi
fi

# AI Generated Images
AI_IMAGES_COUNT=$(find "$AI_GENERATED/images" -type f -not -name '.gitkeep' | wc -l)
if [[ $AI_IMAGES_COUNT -gt 0 ]]; then
    read -p "Delete AI-generated images? ($AI_IMAGES_COUNT files) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        DELETE_AI_IMAGES=1
    fi
fi

# AI Generated Videos
AI_VIDEOS_COUNT=$(find "$AI_GENERATED/videos" -type f -not -name '.gitkeep' | wc -l)
if [[ $AI_VIDEOS_COUNT -gt 0 ]]; then
    read -p "Delete AI-generated videos? ($AI_VIDEOS_COUNT files) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        DELETE_AI_VIDEOS=1
    fi
fi

# Final Generated Videos
FINAL_VIDEOS_COUNT=$(find "$FINAL_VIDEOS" -type f -not -name '.gitkeep' | wc -l)
if [[ $FINAL_VIDEOS_COUNT -gt 0 ]]; then
    read -p "Delete final generated videos? ($FINAL_VIDEOS_COUNT videos) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        DELETE_FINAL_VIDEOS=1
    fi
fi

# Log Files
LOG_FILES_COUNT=0
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ] && [ -s "$log_file" ]; then
        ((LOG_FILES_COUNT++))
    fi
done

if [[ $LOG_FILES_COUNT -gt 0 ]]; then
    read -p "Clear log files? ($LOG_FILES_COUNT files) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CLEAR_LOGS=1
    fi
fi

# Show final review of actions that will be taken
echo ""
echo "📋 REVIEW: The following actions will be taken:"

if [[ $ARCHIVE_FIRST -eq 1 ]]; then
    echo "  ✓ Archive all current outputs before cleaning"
    # Calculate approximate size
    ARCHIVE_SIZE=$(du -sh "$TTS_FILES" "$AI_GENERATED" "$FINAL_VIDEOS" 2>/dev/null | awk '{sum+=$1} END {print sum}')
    if [ ! -z "$ARCHIVE_SIZE" ]; then
        echo "      (Approximate archive size: $ARCHIVE_SIZE)"
    fi
fi

TOTAL_TO_DELETE=0
if [[ $DELETE_TTS -eq 1 ]]; then
    echo "  ✓ Delete $TTS_COUNT TTS audio files"
    TOTAL_TO_DELETE=$((TOTAL_TO_DELETE + TTS_COUNT))
fi

if [[ $DELETE_AI_IMAGES -eq 1 ]]; then
    echo "  ✓ Delete $AI_IMAGES_COUNT AI-generated images"
    TOTAL_TO_DELETE=$((TOTAL_TO_DELETE + AI_IMAGES_COUNT))
fi

if [[ $DELETE_AI_VIDEOS -eq 1 ]]; then
    echo "  ✓ Delete $AI_VIDEOS_COUNT AI-generated videos"
    TOTAL_TO_DELETE=$((TOTAL_TO_DELETE + AI_VIDEOS_COUNT))
fi

if [[ $DELETE_FINAL_VIDEOS -eq 1 ]]; then
    echo "  ✓ Delete $FINAL_VIDEOS_COUNT final generated videos"
    TOTAL_TO_DELETE=$((TOTAL_TO_DELETE + FINAL_VIDEOS_COUNT))
fi

if [[ $CLEAR_LOGS -eq 1 ]]; then
    echo "  ✓ Clear $LOG_FILES_COUNT log files"
fi

if [[ $TOTAL_TO_DELETE -eq 0 && $CLEAR_LOGS -eq 0 && $ARCHIVE_FIRST -eq 0 ]]; then
    echo "  No actions selected - nothing will be changed"
    echo "👋 Session ended - see you next time!"
    exit 0
fi

# Final confirmation before proceeding
echo ""
if [[ $TOTAL_TO_DELETE -gt 0 ]]; then
    echo "⚠️ Total files to be deleted: $TOTAL_TO_DELETE"
fi
read -p "Proceed with these actions? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operation canceled. No files were modified."
    echo "👋 Session ended - see you next time!"
    exit 0
fi

# Now execute the selected actions

# First archive if requested
if [[ $ARCHIVE_FIRST -eq 1 ]]; then
    ARCHIVE_DIR="./archives/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$ARCHIVE_DIR"
    
    # Archive output videos
    if [ -d "$FINAL_VIDEOS" ] && [ "$(ls -A $FINAL_VIDEOS 2>/dev/null)" ]; then
        mkdir -p "$ARCHIVE_DIR/final_videos"
        cp "$FINAL_VIDEOS"/* "$ARCHIVE_DIR/final_videos/" 2>/dev/null
    fi
    
    # Archive logs
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            cp "$log_file" "$ARCHIVE_DIR/" 2>/dev/null
        fi
    done
    
    # Archive TTS files
    if [ -d "$TTS_FILES" ] && [ "$(ls -A $TTS_FILES 2>/dev/null)" ]; then
        mkdir -p "$ARCHIVE_DIR/tts_files"
        cp "$TTS_FILES"/* "$ARCHIVE_DIR/tts_files/" 2>/dev/null
    fi
    
    # Archive AI files
    if [ -d "$AI_GENERATED/images" ] && [ "$(ls -A $AI_GENERATED/images 2>/dev/null)" ]; then
        mkdir -p "$ARCHIVE_DIR/ai_generated/images"
        cp "$AI_GENERATED/images"/* "$ARCHIVE_DIR/ai_generated/images/" 2>/dev/null
    fi
    
    if [ -d "$AI_GENERATED/videos" ] && [ "$(ls -A $AI_GENERATED/videos 2>/dev/null)" ]; then
        mkdir -p "$ARCHIVE_DIR/ai_generated/videos"
        cp "$AI_GENERATED/videos"/* "$ARCHIVE_DIR/ai_generated/videos/" 2>/dev/null
    fi
    
    echo "✅ Current outputs archived to $ARCHIVE_DIR"
fi

# Now perform the deletions
if [[ $DELETE_TTS -eq 1 ]]; then
    find "$TTS_FILES" -type f -not -name '.gitkeep' -delete
    touch "$TTS_FILES/.gitkeep" 2>/dev/null
    echo "✅ Deleted TTS files"
fi

if [[ $DELETE_AI_IMAGES -eq 1 ]]; then
    find "$AI_GENERATED/images" -type f -not -name '.gitkeep' -delete
    touch "$AI_GENERATED/images/.gitkeep" 2>/dev/null
    echo "✅ Deleted AI-generated images"
fi

if [[ $DELETE_AI_VIDEOS -eq 1 ]]; then
    find "$AI_GENERATED/videos" -type f -not -name '.gitkeep' -delete
    touch "$AI_GENERATED/videos/.gitkeep" 2>/dev/null
    echo "✅ Deleted AI-generated videos"
fi

if [[ $DELETE_FINAL_VIDEOS -eq 1 ]]; then
    find "$FINAL_VIDEOS" -type f -not -name '.gitkeep' -delete
    touch "$FINAL_VIDEOS/.gitkeep" 2>/dev/null
    echo "✅ Deleted final videos"
fi

if [[ $CLEAR_LOGS -eq 1 ]]; then
    for log_file in "${LOG_FILES[@]}"; do
        [ -f "$log_file" ] && > "$log_file"
    done
    echo "✅ Cleared log files"
fi

# Final message with helpful stats
echo ""
echo "📊 Project Status After Cleanup:"
echo " - Generated videos: $(find "$FINAL_VIDEOS" -type f -not -name '.gitkeep' | wc -l) videos"
echo " - Used hooks: $(wc -l < used_hooks.txt 2>/dev/null || echo "0") hooks"
echo " - TTS files: $(find "$TTS_FILES" -type f -not -name '.gitkeep' | wc -l) files"
echo " - AI images: $(find "$AI_GENERATED/images" -type f -not -name '.gitkeep' | wc -l) files"
echo " - AI videos: $(find "$AI_GENERATED/videos" -type f -not -name '.gitkeep' | wc -l) files"

echo "👋 Session ended - see you next time!" 