#!/usr/bin/env python3
"""
CLI for Web Scraper - Command line interface for the universal web scraper
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Optional
from loguru import logger

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.universal_scraper import UniversalScraper
from scraper.data_processor import DataProcessor, process_raw_file


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")


def scrape_command(args):
    """Handle scrape command"""
    setup_logging(args.verbose)
    
    logger.info(f"Starting scrape of {args.url}")
    
    # Create scraper instance
    scraper = UniversalScraper(
        base_url=args.url,
        output_dir=args.output_dir,
        expected_pages=args.pages
    )
    
    # Perform scraping
    result = scraper.scrape_and_save(output_format=args.format)
    
    logger.info(f"Scraping completed!")
    logger.info(f"Output file: {result.get('output_file', 'N/A')}")
    logger.info(f"Stats: {result.get('stats', {})}")


def process_command(args):
    """Handle process command"""
    setup_logging(args.verbose)
    
    logger.info(f"Processing raw data file: {args.input_file}")
    
    # Process the raw data
    output_file = process_raw_file(args.input_file, getattr(args, 'output_file', None))
    
    logger.info(f"Processing completed!")
    logger.info(f"Output file: {output_file}")


def analyze_command(args):
    """Handle analyze command"""
    setup_logging(args.verbose)
    
    logger.info(f"Analyzing data file: {args.input_file}")
    
    # Load and analyze the data
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create processor for analysis
    processor = DataProcessor()
    
    if 'pages' in data:
        # This is raw scraped data
        logger.info("Detected raw scraped data format")
        processed_data = processor.process_raw_data(data)
    else:
        # This is already processed data
        logger.info("Detected processed data format")
        processed_data = data
    
    # Generate analysis
    summary = processor.create_readable_summary(processed_data)
    
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"Analysis saved to: {args.output_file}")
    else:
        print(summary)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Universal Web Scraper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape a website
  python cli.py scrape https://example.com --pages 10 --output data/raw

  # Process raw scraped data
  python cli.py process data/raw/scraped_example.json --output data/processed/processed.json

  # Analyze scraped data
  python cli.py analyze data/raw/scraped_example.json --output analysis.txt
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a website')
    scrape_parser.add_argument('url', help='URL to scrape')
    scrape_parser.add_argument('--pages', type=int, help='Number of pages to scrape')
    scrape_parser.add_argument('--output-dir', default='data/raw', help='Output directory')
    scrape_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    scrape_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    scrape_parser.set_defaults(func=scrape_command)
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process raw scraped data')
    process_parser.add_argument('input_file', help='Input raw data file')
    process_parser.add_argument('--output-file', help='Output processed file')
    process_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    process_parser.set_defaults(func=process_command)
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze scraped data')
    analyze_parser.add_argument('input_file', help='Input data file (raw or processed)')
    analyze_parser.add_argument('--output-file', help='Output analysis file')
    analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    analyze_parser.set_defaults(func=analyze_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main() 