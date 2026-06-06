"""
Utility helper functions for the application.
"""

import re
import json
from datetime import datetime
from typing import Optional, Any


def extract_shortcode_from_url(url: str) -> Optional[str]:
    """
    Extract Instagram post shortcode from URL.
    
    Args:
        url: Instagram post URL (e.g., https://www.instagram.com/p/Cxyz123/)
        
    Returns:
        Optional[str]: Shortcode or None if not found
    """
    # Pattern matches /p/SHORTCODE/ or /reel/SHORTCODE/ or /tv/SHORTCODE/
    pattern = r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with suffix.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        suffix: Suffix to add when truncated
        
    Returns:
        str: Truncated text
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string.
    
    Args:
        dt: Datetime object
        format_str: Desired format string
        
    Returns:
        str: Formatted date string
    """
    if not dt:
        return ""
    return dt.strftime(format_str)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string, returning default on error.
    
    Args:
        json_str: JSON string to parse
        default: Value to return if parsing fails
        
    Returns:
        Any: Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default