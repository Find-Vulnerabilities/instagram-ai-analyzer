"""
Instagram Graph API adapter - Official Facebook Graph API implementation.

Uses official Instagram Graph API with access tokens for maximum stability and reliability.
This is the recommended approach for production applications.
"""

import logging
import time
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin

from core.instagram_client import InstagramClient, InstagramClientError
from models.post import Post, PostInfo
from models.comment import Comment

logger = logging.getLogger(__name__)


class GraphAPIAdapter(InstagramClient):
    """
    Instagram client implementation using the official Facebook Graph API.
    
    This adapter provides stable, production-ready access to Instagram data
    through the official Graph API. It includes:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Connection pooling
    - Comprehensive error handling and logging
    """
    
    BASE_URL = "https://graph.instagram.com/v18.0"
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 30  # seconds
    
    # Rate limit configuration
    RATE_LIMIT_BUFFER = 0.2  # Wait 20% longer than limit suggests
    MIN_REQUEST_INTERVAL = 0.1  # Minimum time between requests
    
    # Timeout configuration
    CONNECT_TIMEOUT = 10  # seconds
    READ_TIMEOUT = 30  # seconds
    
    def __init__(self, access_token: str, business_account_id: str):
        """
        Initialize the Graph API client.
        
        Args:
            access_token: Instagram access token (long-lived preferred)
            business_account_id: Instagram Business Account ID
            
        Raises:
            InstagramClientError: If parameters are invalid
        """
        if not access_token or not business_account_id:
            raise InstagramClientError(
                "access_token and business_account_id are required"
            )
        
        self.access_token = access_token
        self.business_account_id = business_account_id
        
        # Session management
        self._session = self._create_session()
        self._last_request_time = 0
        self._rate_limit_reset_time = 0
        self._rate_limit_remaining = 100
        
        logger.info("Graph API adapter initialized with Business Account")
        self._verify_credentials()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with connection pooling."""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0  # We handle retries manually
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session
    
    def _verify_credentials(self) -> None:
        """Verify that credentials are valid."""
        try:
            response = self._make_request(
                "GET",
                f"/{self.business_account_id}",
                params={"fields": "id,username,name"}
            )
            logger.info(f"Credentials verified for account: {response.get('username', 'Unknown')}")
        except Exception as e:
            raise InstagramClientError(
                f"Failed to verify credentials: {str(e)}. "
                f"Please check access_token and business_account_id."
            )
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make a request to the Graph API with retry logic and rate limit handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to BASE_URL)
            params: Query parameters
            data: Request body data
            retry_count: Current retry attempt
            
        Returns:
            Response JSON data
            
        Raises:
            InstagramClientError: If request fails after retries
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = urljoin(self.BASE_URL, endpoint)
        
        # Add access token to params
        if params is None:
            params = {}
        params['access_token'] = self.access_token
        
        # Rate limit enforcement
        self._enforce_rate_limit()
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT)
            )
            
            # Update rate limit info from headers
            self._update_rate_limit_info(response)
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.MAX_RETRIES:
                    wait_time = self._calculate_backoff(retry_count)
                    logger.warning(
                        f"Rate limited. Waiting {wait_time:.1f}s before retry "
                        f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                    )
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, params, data, retry_count + 1)
                else:
                    raise InstagramClientError("Rate limit exceeded after retries")
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                error_data = self._parse_error_response(response)
                raise InstagramClientError(
                    f"Graph API error {response.status_code}: {error_data}"
                )
            
            # Record request time
            self._last_request_time = time.time()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            if retry_count < self.MAX_RETRIES:
                wait_time = self._calculate_backoff(retry_count)
                logger.warning(f"Request timeout. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, data, retry_count + 1)
            else:
                raise InstagramClientError("Request timeout after retries")
        
        except requests.exceptions.ConnectionError as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = self._calculate_backoff(retry_count)
                logger.warning(f"Connection error. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, data, retry_count + 1)
            else:
                raise InstagramClientError(f"Connection failed after retries: {str(e)}")
        
        except requests.exceptions.RequestException as e:
            raise InstagramClientError(f"Request failed: {str(e)}")
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting based on API response headers."""
        # Check if we need to wait for rate limit reset
        if time.time() < self._rate_limit_reset_time:
            wait_time = self._rate_limit_reset_time - time.time()
            logger.info(f"Waiting for rate limit reset ({wait_time:.1f}s remaining)...")
            time.sleep(wait_time)
        
        # Minimum interval between requests
        time_since_last = time.time() - self._last_request_time
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - time_since_last)
    
    def _update_rate_limit_info(self, response: requests.Response) -> None:
        """Update rate limit information from response headers."""
        try:
            # Extract rate limit info from headers
            x_rate_limit_use_remaining = response.headers.get(
                'X-Rate-Limit-Use-Remaining', '0'
            )
            x_rate_limit_use_total = response.headers.get(
                'X-Rate-Limit-Use-Total', '1'
            )
            
            if x_rate_limit_use_remaining and x_rate_limit_use_total:
                remaining = int(x_rate_limit_use_remaining)
                total = int(x_rate_limit_use_total)
                self._rate_limit_remaining = remaining
                
                # If approaching limit, back off
                if remaining < total * 0.1:  # Less than 10% remaining
                    logger.warning(
                        f"Approaching rate limit: {remaining}/{total} requests remaining"
                    )
                    # Set a reset time (conservative estimate)
                    self._rate_limit_reset_time = time.time() + 60
        except Exception as e:
            logger.debug(f"Could not parse rate limit headers: {e}")
    
    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff time."""
        backoff = self.INITIAL_BACKOFF * (2 ** retry_count)
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.8, 1.2)
        return min(backoff * jitter, self.MAX_BACKOFF)
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """Parse error information from Graph API error response."""
        try:
            data = response.json()
            error = data.get('error', {})
            
            if isinstance(error, dict):
                error_message = error.get('message', 'Unknown error')
                error_code = error.get('code', 'N/A')
                return f"[{error_code}] {error_message}"
            else:
                return str(error)
        except Exception:
            return response.text[:200]
    
    def login(self, username: str, password: str) -> bool:
        """
        Not applicable for Graph API.
        
        Graph API uses access tokens instead of username/password.
        Verification is done automatically in __init__.
        
        Returns:
            bool: Always returns True if object was successfully initialized
        """
        logger.warning(
            "login() not applicable for Graph API. "
            "Credentials are verified via access_token."
        )
        return True
    
    def is_session_valid(self) -> bool:
        """
        Check if the access token is still valid.
        
        Returns:
            bool: True if token is valid
        """
        try:
            self._make_request("GET", "/me", params={"fields": "id"})
            return True
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh the session.
        
        For Graph API, this simply validates the token.
        
        Returns:
            bool: True if session is valid
        """
        return self.is_session_valid()
    
    def get_post_by_url(self, url: str) -> Optional[PostInfo]:
        """
        Fetch basic post information by URL.
        
        Args:
            url: Instagram post URL (e.g., https://instagram.com/p/ABC123/)
            
        Returns:
            Optional[PostInfo]: Post information or None if not found
        """
        try:
            # Extract shortcode from URL
            shortcode = self._extract_shortcode_from_url(url)
            if not shortcode:
                logger.error(f"Invalid Instagram URL: {url}")
                return None
            
            # Get media ID from shortcode
            media_id = self._get_media_id_from_shortcode(shortcode)
            if not media_id:
                logger.error(f"Could not find media for shortcode: {shortcode}")
                return None
            
            # Fetch media info
            response = self._make_request(
                "GET",
                f"/{media_id}",
                params={
                    "fields": "id,caption,media_type,media_product_type,"
                             "timestamp,like_count,comments_count"
                }
            )
            
            post_info = PostInfo(
                id=response.get('id', ''),
                code=shortcode,
                caption=response.get('caption', ''),
                like_count=response.get('like_count', 0),
                comment_count=response.get('comments_count', 0),
                timestamp=self._parse_timestamp(response.get('timestamp')),
                username='',  # Need to fetch separately
                media_type=self._map_media_type(response.get('media_type', 'IMAGE')),
                thumbnail_url=response.get('media_product_type', ''),
            )
            
            logger.info(f"Successfully fetched post info: {post_info.id}")
            return post_info
            
        except InstagramClientError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch post by URL: {e}")
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
        comments = []
        
        try:
            # Graph API limits per-request to 100, so we need to paginate
            fields = "id,text,timestamp,like_count,from,username"
            
            if include_replies:
                fields += ",replies{" + fields + "}"
            
            response = self._make_request(
                "GET",
                f"/{post_id}/comments",
                params={
                    "fields": fields,
                    "limit": min(limit, 100),  # Max 100 per request
                    "sort": "ranking"  # Most relevant first
                }
            )
            
            for comment_data in response.get('data', []):
                comment = self._parse_comment(comment_data)
                if comment:
                    comments.append(comment)
                
                # Parse nested replies if included
                if include_replies and 'replies' in comment_data:
                    for reply_data in comment_data.get('replies', {}).get('data', []):
                        reply = self._parse_comment(reply_data, parent_id=comment.id)
                        if reply:
                            comment.replies.append(reply)
            
            logger.info(f"Fetched {len(comments)} comments for post {post_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to fetch comments: {e}")
            return []
    
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
        try:
            # Fetch post info
            post_info = self.get_post_by_url(post_url)
            if not post_info:
                raise InstagramClientError(f"Could not fetch post from URL: {post_url}")
            
            # Fetch comments
            comments = self.get_post_comments(
                post_info.id,
                limit=comment_limit,
                include_replies=include_replies
            )
            
            post = Post(
                info=post_info,
                comments=comments,
                error=None
            )
            
            logger.info(
                f"Successfully fetched post with {len(comments)} comments: {post_url}"
            )
            return post
            
        except InstagramClientError as e:
            logger.error(f"Failed to fetch post with comments: {e}")
            return Post(
                info=PostInfo(
                    id='', code='', caption='', like_count=0,
                    comment_count=0, timestamp=datetime.now(), username=''
                ),
                comments=[],
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching post: {e}")
            return Post(
                info=PostInfo(
                    id='', code='', caption='', like_count=0,
                    comment_count=0, timestamp=datetime.now(), username=''
                ),
                comments=[],
                error=str(e)
            )
    
    def _extract_shortcode_from_url(self, url: str) -> Optional[str]:
        """Extract Instagram shortcode from URL."""
        import re
        
        patterns = [
            r'instagram\.com/p/([a-zA-Z0-9_-]+)',
            r'ig\.instagram\.com/reel/([a-zA-Z0-9_-]+)',
            r'instagram\.com/reel/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_media_id_from_shortcode(self, shortcode: str) -> Optional[str]:
        """
        Get media ID from shortcode using Graph API.
        
        Graph API does not provide a direct shortcode->ID conversion.
        We use a workaround by querying all media and caching results.
        """
        try:
            # Query business account media
            response = self._make_request(
                "GET",
                f"/{self.business_account_id}/media",
                params={
                    "fields": "id,shortcode,media_product_type,timestamp",
                    "limit": 100,
                    "sort": "DESC"  # Most recent first
                }
            )
            
            logger.debug(f"Searching for shortcode in {len(response.get('data', []))} recent media")
            
            # Search for matching shortcode
            for item in response.get('data', []):
                if item.get('shortcode') == shortcode:
                    media_id = item.get('id')
                    logger.info(f"Found media ID for shortcode {shortcode}: {media_id}")
                    return media_id
            
            logger.warning(f"Shortcode {shortcode} not found in recent media")
            # If not found, return None - user may need to use media ID directly
            return None
            
        except Exception as e:
            logger.error(f"Failed to get media ID from shortcode: {e}")
            return None
    
    def _parse_comment(
        self,
        comment_data: Dict[str, Any],
        parent_id: Optional[str] = None
    ) -> Optional[Comment]:
        """Parse comment data from Graph API response."""
        try:
            return Comment(
                id=comment_data.get('id', ''),
                text=comment_data.get('text', ''),
                username=comment_data.get('username') or 
                        comment_data.get('from', {}).get('username', 'Unknown'),
                timestamp=self._parse_timestamp(comment_data.get('timestamp')),
                like_count=comment_data.get('like_count', 0),
                parent_id=parent_id,
            )
        except Exception as e:
            logger.warning(f"Failed to parse comment: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse ISO 8601 timestamp to datetime."""
        if not timestamp_str:
            return datetime.now()
        
        try:
            # Handle ISO 8601 format
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.now()
    
    def _map_media_type(self, media_type: str) -> int:
        """Map Graph API media type to internal representation."""
        mapping = {
            'IMAGE': 1,
            'VIDEO': 2,
            'CAROUSEL': 8,
            'REELS': 2,
            'STORY': 0,
        }
        return mapping.get(media_type.upper(), 1)
    
    def close(self) -> None:
        """Close the client and clean up resources."""
        if self._session:
            self._session.close()
            logger.info("Graph API adapter closed")


# Utility function for getting business account ID from access token
def get_business_account_id(access_token: str) -> Optional[str]:
    """
    Retrieve Instagram Business Account ID using the provided access token.
    
    Args:
        access_token: Facebook/Instagram access token
        
    Returns:
        Optional[str]: Business Account ID or None if not found
        
    Raises:
        InstagramClientError: If request fails
    """
    if not access_token:
        raise InstagramClientError("Access token is required")
    
    try:
        session = requests.Session()
        response = session.get(
            f"https://graph.instagram.com/v18.0/me",
            params={'access_token': access_token, 'fields': 'id,username'},
            timeout=(10, 30)
        )
        
        if response.status_code == 200:
            data = response.json()
            account_id = data.get('id')
            username = data.get('username')
            logger.info(f"Found Instagram Business Account: {username} (ID: {account_id})")
            if not account_id:
                raise InstagramClientError("Account ID not found in response")
            return account_id
        
        elif response.status_code == 401:
            raise InstagramClientError("Invalid or expired access token")
        
        elif response.status_code == 400:
            error_data = response.json().get('error', {})
            raise InstagramClientError(
                f"Invalid request: {error_data.get('message', response.text)}"
            )
        
        else:
            error_data = response.json().get('error', {})
            raise InstagramClientError(
                f"Failed to get business account (Status {response.status_code}): "
                f"{error_data.get('message', response.text)}"
            )
    
    except requests.exceptions.Timeout:
        raise InstagramClientError("Request timeout while retrieving account ID")
    
    except requests.exceptions.ConnectionError as e:
        raise InstagramClientError(f"Connection error: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        raise InstagramClientError(f"Request failed: {str(e)}")
    
    except requests.exceptions.ConnectionError as e:
        raise InstagramClientError(f"Connection error: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        raise InstagramClientError(f"Request failed: {str(e)}")
