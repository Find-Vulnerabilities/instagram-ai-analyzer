#!/usr/bin/env python3
"""
Instagram AI Analyzer - Main entry point.

This application fetches Instagram posts with comments and uses
Google Gemini AI to generate comprehensive summaries and insights.

Usage:
    python main.py
    # or
    python -m ui.app
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import main

if __name__ == '__main__':
    main()