#!/usr/bin/env python3
"""
Content Generator - Main Entry Point
Provides a unified interface to run different content generators
"""

import os
import sys
import argparse
import logging

def setup_logging(log_file=None):
    """Set up logging configuration"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

def main():
    """Main entry point for the content generator"""
    parser = argparse.ArgumentParser(description="Content Generation System")
    parser.add_argument("--type", choices=["ugc", "story", "ai"], default="ugc",
                        help="Type of content to generate")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of videos to generate")
    parser.add_argument("--id", type=str,
                        help="Specific IDs to use (comma-separated for multiple IDs)")
    parser.add_argument("--all", action="store_true",
                        help="Generate all combinations (for UGC generator)")
    parser.add_argument("--batch", type=int, 
                        help="Batch number to process (for AI generator)")
    parser.add_argument("--batch-size", type=int, 
                        help="Batch size (for AI generator)")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Import appropriate generator based on type
    if args.type == "ugc":
        from scripts.ugc_generator import main as ugc_main
        logging.info("Starting UGC video generator")
        
        # Override NUM_VIDEOS if count is specified
        if args.count > 1:
            from config import UGC_CONFIG
            UGC_CONFIG["num_videos"] = args.count
            
        # Override GENERATE_ALL_COMBINATIONS if --all is specified
        if args.all:
            from config import UGC_CONFIG
            UGC_CONFIG["generate_all_combinations"] = True
            
        # Handle specific hook IDs if provided
        if args.id:
            from config import UGC_CONFIG
            # Convert comma-separated string to list of integers
            try:
                hook_ids = [int(id.strip()) for id in args.id.split(',')]
                UGC_CONFIG["specific_hook_ids"] = hook_ids
                logging.info(f"Processing specific hook IDs: {hook_ids}")
            except ValueError as e:
                logging.error(f"Invalid hook ID format: {e}")
                sys.exit(1)
            
        ugc_main()
        
    elif args.type == "story":
        from scripts.story_generator import main as story_main
        logging.info("Starting Story video generator")
        
        # TODO: Add story generator specific overrides
        
        story_main()
        
    elif args.type == "ai":
        from scripts.ai_generator import main as ai_main
        logging.info("Starting AI content generator")
        
        # Set up command line args to pass to the AI generator
        sys.argv = [sys.argv[0]]
        
        # Add batch and batch-size if specified
        if args.batch is not None:
            sys.argv.extend(["--batch", str(args.batch)])
            
        if args.batch_size is not None:
            sys.argv.extend(["--batch-size", str(args.batch_size)])
            
        # Add id if specified
        if args.id is not None:
            sys.argv.extend(["--id", str(args.id)])
            
        # Override other args
        if args.type == "image" or args.type == "video":
            sys.argv.extend(["--type", args.type])
            
        ai_main()
        
    else:
        logging.error(f"Unknown generator type: {args.type}")
        sys.exit(1)

if __name__ == "__main__":
    main() 