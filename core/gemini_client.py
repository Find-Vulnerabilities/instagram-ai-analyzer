"""
Google Gemini AI client wrapper.
Handles API communication, error handling, and response parsing.
"""

import logging
import time
from typing import Optional, List

from config.settings import settings

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    """Exception raised for Gemini API errors."""
    pass


class GeminiClient:
    """
    Client for interacting with Google's Gemini API.
    
    This wrapper handles authentication, request formatting,
    and response processing for text generation tasks.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key (defaults to settings.GEMINI_API_KEY)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None
        
        if not self.api_key:
            raise GeminiClientError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable."
            )
    
    @property
    def client(self):
        """Lazy initialization of the Google GenAI client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model: {self.model}")
            except ImportError:
                raise GeminiClientError(
                    "google-genai package not installed. Run: pip install google-genai"
                )
            except Exception as e:
                raise GeminiClientError(f"Failed to initialize Gemini client: {e}")
        return self._client
    
    def generate_text(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_output_tokens: int = 2048
    ) -> str:
        """
        Generate text response from Gemini.
        
        Args:
            prompt: The input prompt for the model
            temperature: Controls randomness (0.0 to 1.0)
            max_output_tokens: Maximum length of response in TOKENS
            
        Returns:
            str: Generated text response
            
        Raises:
            GeminiClientError: If generation fails
        """
        start_time = time.time()
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Generated {len(response.text)} chars in {elapsed_ms}ms")
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise GeminiClientError(f"Failed to generate content: {str(e)}")
    
    # 注意：以下方法必须在类内部，且缩进正确（4个空格）
    def generate_structured_summary(
        self,
        post_caption: str,
        comments: List,
        max_length: int = 2000
    ) -> str:
        """
        Generate a structured summary of post and comments.
        
        Args:
            post_caption: The original post caption
            comments: List of Comment objects
            max_length: Approximate maximum summary length in CHARACTERS
            
        Returns:
            str: Structured summary text
        """
        # Prepare comment texts for the prompt
        comment_texts = []
        for comment in comments[:100]:  # Limit to first 100 comments
            comment_texts.append(f"@{comment.username}: {comment.text[:500]}")
            # Include replies
            for reply in comment.replies[:10]:
                comment_texts.append(f"  ↳ @{reply.username}: {reply.text[:300]}")
        
        comments_text = "\n".join(comment_texts)
        
        # Truncate comments if they exceed the max prompt size
        MAX_PROMPT_CHARS = 30000
        if len(comments_text) > MAX_PROMPT_CHARS:
            comments_text = comments_text[:MAX_PROMPT_CHARS] + "\n...[truncated]"
            logger.warning(f"Comments truncated to {MAX_PROMPT_CHARS} characters")
        
        # Truncate caption to reasonable length (handle None case)
        truncated_caption = (post_caption[:1000] if post_caption else "")
        
        prompt = f"""You are an expert social media analyst. Analyze the following Instagram post and its comments, then provide a comprehensive summary.

## POST CAPTION:
{truncated_caption}

## COMMENTS ({len(comment_texts)} comments):
{comments_text}

## TASK:
Analyze the above content and provide a structured summary in the following format. Write thorough, detailed analysis for each section:

1. POST OVERVIEW: A concise summary of what the post is about and its main message. Include any calls-to-action or questions asked by the creator.

2. SENTIMENT ANALYSIS: Describe the overall sentiment distribution among comments (positive, negative, neutral, mixed). Identify any emotional patterns or shifts in the conversation.

3. KEY TOPICS DISCUSSED: List the main topics users are discussing in the comments, ordered by frequency/prominence. For each topic, briefly explain why it's significant.

4. POPULAR OPINIONS: Summarize the most common viewpoints, agreements, or shared experiences expressed by commenters. Group similar opinions together.

5. NOTABLE QUOTES: Select 3-5 impactful, representative, or insightful direct quotes from the comments (with attribution to usernames).

6. REPLY HIGHLIGHTS: Describe meaningful interactions in reply threads. Note any debates, clarifications, or community support patterns.

7. CONTROVERSIAL POINTS: Identify any points of disagreement, debate, or polarized views among commenters.

Please write naturally and thoroughly. The summary should be substantive and provide real insight into the community's reaction to this post.
"""

        max_tokens = max(1024, min(8192, max_length // 4))
        logger.info(f"Summary request: max_length={max_length} chars -> max_output_tokens={max_tokens}")
        
        return self.generate_text(prompt, temperature=0.5, max_output_tokens=max_tokens)