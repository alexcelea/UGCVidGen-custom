#!/bin/bash

echo "🚀 Starting Content Generator session..."

# Define project-specific paths
OUTPUT_DIR="./output"
ASSETS_DIR="./assets"
CONTENT_DIR="./content"

# Define the required directory structure
REQUIRED_DIRS=(
    # Output directories
    "$OUTPUT_DIR/ugc" 
    "$OUTPUT_DIR/ugc/tts_files" 
    "$OUTPUT_DIR/stories" 
    "$OUTPUT_DIR/ai_generated/images" 
    "$OUTPUT_DIR/ai_generated/videos" 
    "$OUTPUT_DIR/ai_generated/logs"
    
    # Asset directories 
    "$ASSETS_DIR/videos/hooks" 
    "$ASSETS_DIR/videos/ctas" 
    "$ASSETS_DIR/videos/backgrounds"
    "$ASSETS_DIR/music" 
    "$ASSETS_DIR/fonts"
    
    # Content directory
    "$CONTENT_DIR"
)

# Ensure all required directories exist and have .gitkeep
echo "🔍 Checking project structure..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  Creating directory: $dir"
        mkdir -p "$dir"
        touch "$dir/.gitkeep"
    fi
done

# Check for .gitignore file
if [ ! -f ".gitignore" ]; then
    echo "  Creating .gitignore file"
    cat > .gitignore << 'EOL'
# Virtual Environment
venv/
env/
ENV/

# Environment variables and secrets
.env
.env.*

# Python cache files
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Distribution / packaging
dist/
build/
*.egg-info/

# Logs
/logs/*
!/logs/.gitkeep
*.log

# New structure - directory content ignore patterns with .gitkeep exceptions
output/ugc/*.mp4
output/ugc/tts_files/*
!output/ugc/tts_files/.gitkeep
output/ugc/*.log
output/ugc/video_list.txt
output/stories/*.mp4
output/stories/*.log
output/ai_generated/images/*
!output/ai_generated/images/.gitkeep
output/ai_generated/videos/*
!output/ai_generated/videos/.gitkeep
output/ai_generated/logs/*
!output/ai_generated/logs/.gitkeep

# Content backup
backups/

# OS specific files
.DS_Store
Thumbs.db

# IDE specific files
.idea/
.vscode/
*.swp
*.swo
EOL
else
    # Ensure all important patterns are in .gitignore
    patterns_to_check=(
        "output/ugc/*.mp4"
        "output/ugc/tts_files/*"
        "output/stories/*.mp4"
        "output/ai_generated/images/*"
        "output/ai_generated/videos/*"
        "output/ai_generated/logs/*"
    )
    
    missing_patterns=()
    for pattern in "${patterns_to_check[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            missing_patterns+=("$pattern")
        fi
    done
    
    if [ ${#missing_patterns[@]} -gt 0 ]; then
        echo "⚠️ .gitignore file missing important patterns. Consider updating it."
    fi
fi

# Check for content files
for file in "$CONTENT_DIR/hooks.csv" "$CONTENT_DIR/ai_prompts.csv" "$CONTENT_DIR/stories.csv"; do
    if [ ! -f "$file" ]; then
        echo "⚠️ Warning: $file not found. You may need to create this file."
    fi
done

# Check for existing log files
log_files=("$OUTPUT_DIR/ugc/video_creation.log" "$OUTPUT_DIR/ugc/video_list.txt")
for log_file in "${log_files[@]}"; do
    if [ -f "$log_file" ] && [ -s "$log_file" ]; then
        log_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "unknown")
        echo "📝 Found log file: $log_file (size: $log_size bytes)"
    fi
done

# Display project information
echo -e "\n📊 Project Status"
echo "==============================="
echo "📁 INPUT ASSETS:"
echo " - Used hooks: $(wc -l < "$CONTENT_DIR/used_hooks.txt" 2>/dev/null || echo "0") hooks"
echo " - Hook videos: $(find "$ASSETS_DIR/videos/hooks" -type f -not -name ".gitkeep" | wc -l) files"
echo " - CTA videos: $(find "$ASSETS_DIR/videos/ctas" -type f -not -name ".gitkeep" | wc -l) files"
echo " - Background videos: $(find "$ASSETS_DIR/videos/backgrounds" -type f -not -name ".gitkeep" | wc -l) files"
echo ""
echo "🎬 GENERATED CONTENT:"
echo " - AI generated images: $(find "$OUTPUT_DIR/ai_generated/images" -type f -not -name ".gitkeep" | wc -l) files"
echo " - AI generated videos: $(find "$OUTPUT_DIR/ai_generated/videos" -type f -not -name ".gitkeep" | wc -l) files"
echo " - Final UGC videos: $(find "$OUTPUT_DIR/ugc" -name "*.mp4" | wc -l) files"
echo " - Final Story videos: $(find "$OUTPUT_DIR/stories" -name "*.mp4" | wc -l) files"
echo "==============================="

echo "✅ Project setup complete. Ready to generate content!" 