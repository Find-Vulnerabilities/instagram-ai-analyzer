"""
Instagram client implementation using the unofficial instagrapi library.
Note: This approach simulates mobile app requests and may violate Instagram's ToS.
Use responsibly and only for personal, non-commercial purposes.
"""

import logging
from typing import List, Optional
from datetime import datetime

from core.instagram_client import InstagramClient, InstagramClientError
from models.post import Post, PostInfo
from models.comment import Comment

# Try to import instagrapi, provide helpful error if not installed
try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ClientError
except ImportError:
    raise ImportError(
        "instagrapi is not installed. Run: pip install instagrapi"
    )

logger = logging.getLogger(__name__)


class InstagrapiAdapter(InstagramClient):
    """
    Instagram client implementation using the unofficial instagrapi library.
    
    This adapter wraps the instagrapi library to provide the standard interface.
    It handles session persistence, login management, and data transformation.
    
    WARNING: This uses Instagram's private API which violates their Terms of Service.
    Your account may be banned if used aggressively or for commercial purposes.
    """
    
    def __init__(self, session_file: Optional[str] = "session.json"):
        """
        Initialize the instagrapi client.
        
        Args:
            session_file: Path to file for session persistence
        """
        self._client = None
        self._session_file = session_file
        self._is_logged_in = False
        self._username = None
        self._password = None
        
    @property
    def client(self):
        """Lazy initialization of instagrapi client."""
        if self._client is None:
            self._client = Client()
        return self._client
    
    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with Instagram using instagrapi.
        
        Attempts to load existing session first to avoid repeated logins.
        
        Args:
            username: Instagram username
            password: Instagram password
            
        Returns:
            bool: True if login successful
            
        Raises:
            InstagramClientError: If authentication fails
        """
        # Store credentials for potential session refresh
        self._username = username
        self._password = password
        
        try:
            # Try to load existing session
            if self._session_file:
                try:
                    self.client.load_settings(self._session_file)
                    logger.info("Loaded session from file")
                except Exception as e:
                    logger.debug(f"No existing session found: {e}")
            
            # Perform login
            self.client.login(username, password)
            self._is_logged_in = True
            
            # Save session for future use
            if self._session_file:
                try:
                    self.client.dump_settings(self._session_file)
                    logger.info("Session saved to file")
                except Exception as e:
                    logger.warning(f"Failed to save session: {e}")
                
                
            logger.info(f"Successfully logged in as {username}")
            return True
            
        except (LoginRequired, ClientError) as e:
            raise InstagramClientError(f"Login failed: {str(e)}")
        except Exception as e:
            raise InstagramClientError(f"Unexpected error during login: {str(e)}")
    
    def is_session_valid(self) -> bool:
        """
        Check if current session is still valid.
        
        Returns:
            bool: True if session is valid and user is logged in
        """
        if not self._is_logged_in:
            return False
        try:
            # Try to get current user ID to validate session
            user_id = self.client.user_id
            return user_id is not None
        except Exception:
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh the session if needed.
        
        Returns:
            bool: True if session is valid after refresh
        """
        if self.is_session_valid():
            return True
        
        # Session invalid, try to re-login using stored credentials
        if self._username and self._password:
            try:
                logger.info("Attempting to refresh Instagram session...")
                self.login(self._username, self._password)
                return True
            except Exception as e:
                logger.error(f"Session refresh failed: {e}")
                return False
        
        return False
    
    def get_post_by_url(self, url: str) -> Optional[PostInfo]:
        """
        Fetch basic post information by URL.
        
        Args:
            url: Instagram post URL
            
        Returns:
            Optional[PostInfo]: Post info or None if not found
        """
        if not self._is_logged_in:
            raise InstagramClientError("Not logged in. Call login() first.")
        
        try:
            # Extract shortcode from URL and get media info
            media_pk = self.client.media_pk_from_url(url)
            media = self.client.media_info(media_pk)
            
            return PostInfo(
                id=str(media.pk),
                code=media.code,
                caption=media.caption_text or "",
                like_count=media.like_count,
                comment_count=media.comment_count,
                timestamp=media.taken_at,
                username=media.user.username,
                media_type=media.media_type,
                thumbnail_url=media.thumbnail_url or "",
            )
        except Exception as e:
            logger.error(f"Failed to fetch post: {e}")
            return None
    
    def get_post_comments(
        self, 
        post_id: str, 
        limit: int = 100,
        include_replies: bool = True
    ) -> List[Comment]:
        """
        Fetch comments for a specific post.
        
        Args:
            post_id: Instagram media ID
            limit: Maximum number of comments to fetch
            include_replies: Whether to include reply threads
            
        Returns:
            List[Comment]: List of Comment objects
        """
        if not self._is_logged_in:
            raise InstagramClientError("Not logged in. Call login() first.")
        
        comments = []
        
        try:
            # Fetch comments from instagrapi
            media_comments = self.client.media_comments(
                int(post_id), 
                amount=limit
            )
            
            for comment_data in media_comments:
                comment = Comment(
                    id=str(comment_data.pk),
                    text=comment_data.text,
                    username=comment_data.user.username,
                    timestamp=comment_data.created_at_utc,
                    like_count=getattr(comment_data, 'like_count', 0),
                )
                
                # Securely retrieve reply_count and avoid AttributeError.
                reply_count = getattr(comment_data, 'reply_count', 0)
                
                # Fetch replies if requested
                if include_replies and reply_count > 0:
                    try:
                        replies = self.client.media_comment_replies(
                            int(post_id), 
                            int(comment_data.pk),
                            amount=min(reply_count, 50)  # Maximum number of replies
                        )
                        for reply_data in replies:
                            reply = Comment(
                                id=str(reply_data.pk),
                                text=reply_data.text,
                                username=reply_data.user.username,
                                timestamp=reply_data.created_at_utc,
                                like_count=getattr(reply_data, 'like_count', 0),
                                parent_id=str(comment_data.pk),
                            )
                            comment.replies.append(reply)
                    except Exception as e:
                        logger.warning(f"Failed to fetch replies for comment {comment_data.pk}: {e}")
                
                comments.append(comment)
                
        except Exception as e:
            logger.error(f"Failed to fetch comments: {e}")
            
        return comments
    
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
        if not self._is_logged_in:
            raise InstagramClientError("Not logged in. Call login() first.")
        
        # Fetch post info
        post_info = self.get_post_by_url(post_url)
        if not post_info:
            return Post(
                info=PostInfo(
                    id="", code="", caption="", like_count=0,
                    comment_count=0, timestamp=datetime.now(), username=""
                ),
                error="Failed to fetch post information"
            )
        
        # Fetch comments
        comments = self.get_post_comments(
            post_info.id, 
            limit=comment_limit,
            include_replies=include_replies
        )
        
        return Post(info=post_info, comments=comments)
    
    def close(self) -> None:
        """Close the client connection and clean up resources."""
        if self._client:
            # instagrapi doesn't have an explicit close method
            # but we can clear the client
            self._client = None
        self._is_logged_in = False