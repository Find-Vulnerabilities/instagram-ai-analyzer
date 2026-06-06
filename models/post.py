"""
Post data model definition.
Represents an Instagram post with its core information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PostInfo:
    """
    Data class representing Instagram post information.
    
    Attributes:
        id: Instagram media ID
        code: Shortcode for the post (used in URLs)
        caption: Post caption/text content
        like_count: Number of likes
        comment_count: Number of comments
        timestamp: Post creation time
        username: Author's username
        media_type: Type of media (1=photo, 2=video, 8=carousel)
        thumbnail_url: URL to post thumbnail
    """
    id: str
    code: str
    caption: str
    like_count: int
    comment_count: int
    timestamp: datetime
    username: str
    media_type: int = 1
    thumbnail_url: str = ""


@dataclass
class Post:
    """
    Complete Instagram post data including media info and comments.
    """
    info: PostInfo
    comments: List["Comment"] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Generate Instagram post URL from shortcode."""
        return f"https://www.instagram.com/p/{self.info.code}/"
    
    @property
    def total_comments_fetched(self) -> int:
        """Get number of comments fetched."""
        return len(self.comments)