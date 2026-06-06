"""
Abstract base class for Instagram data fetching.
Defines the interface that any Instagram client must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from models.post import Post, PostInfo


class InstagramClientError(Exception):
    """Exception raised for Instagram client errors."""
    pass


class InstagramClient(ABC):
    """
    Abstract base class for Instagram API clients.
    
    This abstraction allows switching between different Instagram data sources
    (official Graph API, unofficial instagrapi, etc.) without changing application logic.
    """
    
    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with Instagram.
        
        Args:
            username: Instagram account username
            password: Instagram account password
            
        Returns:
            bool: True if login successful
            
        Raises:
            InstagramClientError: If authentication fails
        """
        pass
    
    @abstractmethod
    def get_post_by_url(self, url: str) -> Optional[PostInfo]:
        """
        Fetch basic post information by URL.
        
        Args:
            url: Instagram post URL
            
        Returns:
            Optional[PostInfo]: Post information or None if not found
        """
        pass
    
    @abstractmethod
    def get_post_comments(
        self, 
        post_id: str, 
        limit: int = 100,
        include_replies: bool = True
    ) -> List:
        """
        Fetch comments for a specific post.
        
        Args:
            post_id: Instagram media ID
            limit: Maximum number of comments to fetch
            include_replies: Whether to include reply threads
            
        Returns:
            List[Comment]: List of Comment objects
        """
        pass
    
    @abstractmethod
    def get_post_with_comments(
        self, 
        post_url: str,
        comment_limit: int = 100,
        include_replies: bool = True
    ) -> Post:
        """
        Fetch complete post data including comments.
        
        Args:
            post_url: Instagram post URL
            comment_limit: Maximum number of comments to fetch
            include_replies: Whether to include reply threads
            
        Returns:
            Post: Complete post object with comments
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the client connection and clean up resources."""
        pass