"""
AI summarization module for Instagram comments.
Handles comment processing and orchestrates Gemini API calls.
"""

import logging
import re
import json
import time
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from models.post import Post
from models.comment import Comment
from models.summary import SummaryResult
from core.gemini_client import GeminiClient, GeminiClientError
from config.settings import settings

logger = logging.getLogger(__name__)


class CommentSummarizer:
    """
    Orchestrates AI-powered summarization of Instagram posts and comments.
    
    This class handles:
    - Preparing comment data for AI processing
    - Calling Gemini API for analysis
    - Parsing and structuring the results
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer with a Gemini client.
        
        Args:
            api_key: Optional Gemini API key (uses settings if not provided)
        """
        self.gemini = GeminiClient(api_key=api_key)
        self.max_summary_length = settings.SUMMARY_MAX_LENGTH
    
    def _preprocess_comments(self, comments: List[Comment], max_comments: int = 100) -> List[Comment]:
        """
        Preprocess and filter comments for summarization.
        
        Args:
            comments: List of Comment objects
            max_comments: Maximum number of comments to include
            
        Returns:
            List[Comment]: Filtered and sorted comments
        """
        if not comments:
            return []
        
        # Sort by like count (most popular first)
        sorted_comments = sorted(
            comments, 
            key=lambda c: c.like_count, 
            reverse=True
        )
        
        return sorted_comments[:max_comments]
    
    def summarize_post(self, post: Post) -> SummaryResult:
        """
        Generate a comprehensive summary of an Instagram post and its comments.
        
        Args:
            post: Post object containing post info and comments
            
        Returns:
            SummaryResult: Structured summary with analysis
        """
        result = SummaryResult()
        start_time = time.time()
        
        try:
            # Validate input
            if not post or not post.info:
                result.error = "No post data provided"
                return result
            
            # Preprocess comments
            processed_comments = self._preprocess_comments(post.comments)
            
            if not processed_comments and post.info.comment_count > 0:
                logger.warning("No comments available for summarization")
                result.error = "No comments could be fetched for analysis"
                return result
            
            # Generate summary using Gemini
            raw_response = self.gemini.generate_structured_summary(
                post_caption=post.info.caption,
                comments=processed_comments,
                max_length=self.max_summary_length
            )
            
            
            max_chars = self.max_summary_length * 4
            if len(raw_response) > max_chars:
                raw_response = raw_response[:max_chars]
                logger.warning(f"Response truncated from {len(raw_response)} to {max_chars} characters")
            
            # Parse and structure the response
            result.raw_response = raw_response
            result = self._parse_summary_response_robust(raw_response, result)
            result.model_used = self.gemini.model
            
        except GeminiClientError as e:
            logger.error(f"Gemini API error: {e}")
            result.error = str(e)
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            result.error = f"Processing error: {str(e)}"
        
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result
    
    def _parse_summary_response_robust(self, raw_response: str, result: SummaryResult) -> SummaryResult:
        """
        Parse the raw Gemini response into structured fields using multiple strategies.
        
        Strategies:
        1. Try JSON format (preferred)
        2. Try Markdown section headers
        3. Fallback to storing raw response
        """
        # Strategy 1: Try JSON output
        json_data = self._try_parse_as_json(raw_response)
        if json_data:
            logger.info("Successfully parsed response as JSON")
            self._apply_json_to_result(json_data, result)
            return result
        
        # Strategy 2: Try Markdown section headers
        markdown_data = self._try_parse_markdown_sections(raw_response)
        if markdown_data['any_found']:
            logger.info("Successfully parsed response using markdown sections")
            self._apply_markdown_to_result(markdown_data['sections'], result)
            return result
        
        # Strategy 3: Fallback - store raw response
        logger.warning("Could not parse structured response, storing raw text")
        result.post_overview = raw_response[:self.max_summary_length]
        
        return result
    
    def _try_parse_as_json(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """
        Try to parse the response as JSON.
        
        Looks for:
        - JSON code blocks (```json ... ```)
        - Raw JSON objects
        """
        # Find JSON code blocks
        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Find JSON objects (starting with { and ending with })
        json_object_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
        if json_object_match:
            try:
                return json.loads(json_object_match.group(1))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _try_parse_markdown_sections(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse markdown formatted sections.
        
        Returns:
            Dict with 'sections' and 'any_found' keys
        """
        lines = raw_response.split('\n')
        sections = {
            'post_overview': '',
            'sentiment_analysis': '',
            'key_topics': [],
            'popular_opinions': [],
            'notable_quotes': [],
            'reply_highlights': [],
            'controversial_points': []
        }
        
        # More flexible title matching modes
        section_patterns = {
            r'(?:#+\s*)?(?:1\.?\s*)?POST\s+OVERVIEW|OVERVIEW': 'post_overview',
            r'(?:#+\s*)?(?:2\.?\s*)?SENTIMENT\s+ANALYSIS|SENTIMENT': 'sentiment_analysis',
            r'(?:#+\s*)?(?:3\.?\s*)?KEY\s+TOPICS|TOPICS': 'key_topics',
            r'(?:#+\s*)?(?:4\.?\s*)?POPULAR\s+OPINIONS|OPINIONS': 'popular_opinions',
            r'(?:#+\s*)?(?:5\.?\s*)?NOTABLE\s+QUOTES|QUOTES': 'notable_quotes',
            r'(?:#+\s*)?(?:6\.?\s*)?REPLY\s+HIGHLIGHTS|REPLY': 'reply_highlights',
            r'(?:#+\s*)?(?:7\.?\s*)?CONTROVERSIAL|DISAGREEMENT': 'controversial_points',
        }
        
        current_section = None
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if it is a chapter title
            matched = False
            for pattern, field in section_patterns.items():
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    # Save previous chapters
                    if current_section and current_content:
                        self._save_markdown_section(current_section, current_content, sections)
                    current_section = field
                    current_content = []
                    matched = True
                    break
            
            # If it is not a title and we are currently in a section, accumulate content
            if not matched and current_section:
                # Skip blank lines and purely decorative symbols
                if len(line_stripped) > 2 or line_stripped not in ['-', '*', '=']:
                    current_content.append(line_stripped)
        
        # Save the last chapter
        if current_section and current_content:
            self._save_markdown_section(current_section, current_content, sections)
        
        any_found = any(
            v for v in sections.values() 
            if v and (isinstance(v, str) and len(v) > 10) or (isinstance(v, list) and len(v) > 0)
        )
        
        return {'sections': sections, 'any_found': any_found}
    
    def _save_markdown_section(self, field: str, content_lines: List[str], sections: Dict):
        """Save the markdown chapter content to the sections dictionary."""
        if not content_lines:
            return
        
        # Text fields
        if field in ['post_overview', 'sentiment_analysis']:
            content = ' '.join(content_lines).strip()
            if content:
                sections[field] = content[:1000]
        
        # List fields
        elif field in sections and isinstance(sections[field], list):
            items = []
            for line in content_lines:
                line = line.strip()
                # Match list item markers
                if re.match(r'^[\d\-\*•✓→▶️]+\s*', line):
                    item = re.sub(r'^[\d\-\*•✓→▶️]+\s*', '', line)
                    if item and len(item) > 5:
                        items.append(item[:200])
                elif len(line) > 10 and not line.startswith('#'):
                    # Normal text might also be a description
                    items.append(line[:200])
            
            if items:
                sections[field] = items[:10]  # limit to 10 items
            elif content_lines:
                # If there are no list items, take the first row as the content.
                first_line = content_lines[0][:200]
                if first_line:
                    sections[field] = [first_line]
    
    def _apply_json_to_result(self, json_data: Dict, result: SummaryResult):
        """Apply JSON data to the SummaryResult object."""
        field_mapping = {
            'post_overview': 'post_overview',
            'sentiment_analysis': 'sentiment_analysis',
            'key_topics': 'key_topics',
            'popular_opinions': 'popular_opinions',
            'notable_quotes': 'notable_quotes',
            'reply_highlights': 'reply_highlights',
            'controversial_points': 'controversial_points',
        }
        
        for json_key, result_field in field_mapping.items():
            if json_key in json_data and json_data[json_key]:
                value = json_data[json_key]
                if isinstance(value, list) and hasattr(result, result_field):
                    setattr(result, result_field, value[:10])
                elif isinstance(value, str) and hasattr(result, result_field):
                    setattr(result, result_field, value[:1000])
    
    def _apply_markdown_to_result(self, sections: Dict, result: SummaryResult):
        """Apply the parsed markdown sections to the SummaryResult object."""
        if sections.get('post_overview'):
            result.post_overview = sections['post_overview']
        if sections.get('sentiment_analysis'):
            result.sentiment_analysis = sections['sentiment_analysis']
        if sections.get('key_topics'):
            result.key_topics = sections['key_topics'][:10]
        if sections.get('popular_opinions'):
            result.popular_opinions = sections['popular_opinions'][:10]
        if sections.get('notable_quotes'):
            result.notable_quotes = sections['notable_quotes'][:5]
        if sections.get('reply_highlights'):
            result.reply_highlights = sections['reply_highlights'][:3]
        if sections.get('controversial_points'):
            result.controversial_points = sections['controversial_points'][:3]