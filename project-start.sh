#!/bin/bash

echo "🚀 Starting UGC Video Generator session..."

# Define project-specific paths
TTS_FILES="./tts_files"
AI_GENERATED="./ai_generated"
FINAL_VIDEOS="./final_videos"
REQUIRED_DIRS=("$TTS_FILES" "$AI_GENERATED/images" "$AI_GENERATED/videos" "$AI_GENERATED/logs" "$FINAL_VIDEOS" "hook_videos" "cta_videos" "music")

# Ensure all required directories exist and have .gitkeep
echo "🔍 Checking project structure..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  Creating directory: $dir"
        mkdir -p "$dir"
        touch "$dir/.gitkeep"
    fi
done

# Check .gitignore to ensure generated content isn't committed
if [ ! -f ".gitignore" ]; then
    echo "⚠️ No .gitignore file found. Creating one with recommended patterns..."
    cat > .gitignore << EOL
# UGC Video Generator output directories
tts_files/*
!tts_files/.gitkeep
ai_generated/images/*
!ai_generated/images/.gitkeep
ai_generated/videos/*
!ai_generated/videos/.gitkeep
ai_generated/logs/*
!ai_generated/logs/.gitkeep
final_videos/*
!final_videos/.gitkeep

# Log files
video_creation.log
video_list.txt
used_hooks.txt

# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
.venv
venv/
ENV/

# OS specific
.DS_Store
Thumbs.db
EOL
    echo "✅ Created .gitignore file"
else
    # Check if important patterns are in .gitignore
    MISSING_PATTERNS=()
    for pattern in "tts_files/*" "ai_generated/images/*" "ai_generated/videos/*" "final_videos/*" "video_creation.log" "video_list.txt" "used_hooks.txt" ".env"; do
        if ! grep -q "$pattern" .gitignore; then
            MISSING_PATTERNS+=("$pattern")
        fi
    done
    
    if [ ${#MISSING_PATTERNS[@]} -gt 0 ]; then
        echo "⚠️ Some generated files may not be in .gitignore:"
        for pattern in "${MISSING_PATTERNS[@]}"; do
            echo "  - $pattern"
        done
        read -p "Would you like to add these patterns to .gitignore? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "" >> .gitignore
            echo "# UGC Video Generator output patterns" >> .gitignore
            for pattern in "${MISSING_PATTERNS[@]}"; do
                echo "$pattern" >> .gitignore
            done
            echo "!tts_files/.gitkeep" >> .gitignore
            echo "!ai_generated/images/.gitkeep" >> .gitignore
            echo "!ai_generated/videos/.gitkeep" >> .gitignore
            echo "!ai_generated/logs/.gitkeep" >> .gitignore
            echo "!final_videos/.gitkeep" >> .gitignore
            echo "✅ Added missing patterns to .gitignore"
        fi
    fi
fi

# Check for log files from previous runs
if [ -f "video_creation.log" ] && [ -s "video_creation.log" ]; then
    LOG_SIZE=$(stat -f%z "video_creation.log" 2>/dev/null || stat -c%s "video_creation.log" 2>/dev/null || echo "unknown")
    if [ "$LOG_SIZE" != "unknown" ]; then
        LOG_SIZE_HUMAN=$(numfmt --to=iec --format="%.2f" $LOG_SIZE 2>/dev/null || echo "$LOG_SIZE bytes")
        echo "📝 Found existing log file ($LOG_SIZE_HUMAN)"
    else
        echo "📝 Found existing log file"
    fi
    
    echo "Options:"
    echo "1. Keep log file"
    echo "2. Archive log file (create backup and start fresh)"
    echo "3. Clear log file (start fresh without backup)"
    read -p "Select an option (1-3): " -n 1 -r
    echo
    
    case $REPLY in
        2)
            # Archive
            ARCHIVE_DIR="./archives/$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$ARCHIVE_DIR"
            cp "video_creation.log" "$ARCHIVE_DIR/"
            > "video_creation.log"
            echo "✅ Log file archived to $ARCHIVE_DIR and reset"
            ;;
        3)
            # Clear
            > "video_creation.log"
            echo "✅ Log file cleared"
            ;;
        *)
            echo "⏭️ Keeping log file as is"
            ;;
    esac
fi

# Environment check
if [ ! -f ".env" ]; then
    echo "⚠️ No .env file found. API integrations may not work."
    
    # Check if sample exists
    if [ -f ".env.sample" ]; then
        read -p "Would you like to create .env from sample? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.sample .env
            echo "✅ Created .env file from sample. Please edit with your API keys."
        fi
    fi
fi

# Project status
echo ""
echo "📊 Project Status:"
echo " - Generated videos: $(find "$FINAL_VIDEOS" -type f -not -name '.gitkeep' | wc -l) videos"
echo " - Used hooks: $(wc -l < used_hooks.txt 2>/dev/null || echo "0") hooks"
echo " - Available hook videos: $(find "hook_videos" -type f -not -name '.gitkeep' | wc -l) videos"
echo " - Available CTA videos: $(find "cta_videos" -type f -not -name '.gitkeep' | wc -l) videos"

echo "💻 UGC Video Generator environment ready!"
echo "Run 'python UGCReelGen.py' to generate videos or 'python FalAIGenerator.py' to create AI content." 