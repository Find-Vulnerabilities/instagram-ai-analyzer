"""
Summary result model definitions.
Structures for Gemini AI summarization outputs.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class KeyPoint:
    """
    Individual key point extracted from comments.
    
    Attributes:
        title: Short title of the key point
        description: Detailed description
        relevance_score: Score from 0-10 indicating importance
        supporting_mentions: Number of comments supporting this point
    """
    title: str
    description: str
    relevance_score: float
    supporting_mentions: int


@dataclass
class SummaryResult:
    """
    Complete summary result from AI analysis.
    
    Attributes:
        post_overview: One-paragraph overview of the post
        sentiment_analysis: Overall sentiment distribution
        key_topics: Main topics discussed in comments
        popular_opinions: Most common opinions expressed by users
        notable_quotes: Selected impactful quotes from comments
        reply_highlights: Notable patterns in reply threads
        controversial_points: Points that generated disagreement
        processing_time_ms: Time taken to generate summary
        model_used: Which Gemini model was used
    """
    post_overview: str = ""
    sentiment_analysis: str = ""
    key_topics: List[str] = field(default_factory=list)
    popular_opinions: List[str] = field(default_factory=list)
    notable_quotes: List[str] = field(default_factory=list)
    reply_highlights: List[str] = field(default_factory=list)
    controversial_points: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    model_used: str = "gemini-2.5-flash"
    raw_response: str = ""
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if summary was generated successfully."""
        return self.error is None and bool(self.post_overview)
    
    def to_dict(self) -> dict:
        """Convert summary to dictionary for API responses."""
        return {
            "post_overview": self.post_overview,
            "sentiment_analysis": self.sentiment_analysis,
            "key_topics": self.key_topics,
            "popular_opinions": self.popular_opinions,
            "notable_quotes": self.notable_quotes,
            "reply_highlights": self.reply_highlights,
            "controversial_points": self.controversial_points,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
        }