"""
Comment data model definitions.
Represents Instagram comments and reply threads.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Comment:
    """
    Data class representing an Instagram comment.
    
    Attributes:
        id: Comment ID
        text: Comment content
        username: Author's username
        timestamp: Comment creation time
        like_count: Number of likes on this comment
        replies: List of replies to this comment
        parent_id: ID of parent comment (None for top-level)
    """
    id: str
    text: str
    username: str
    timestamp: datetime
    like_count: int = 0
    replies: List["Comment"] = field(default_factory=list)
    parent_id: Optional[str] = None
    
    @property
    def is_reply(self) -> bool:
        """Check if this comment is a reply to another comment."""
        return self.parent_id is not None
    
    @property
    def reply_count(self) -> int:
        """Get number of replies to this comment."""
        return len(self.replies)


@dataclass
class CommentThread:
    """
    Represents a thread of comments with hierarchy.
    
    Attributes:
        root: The top-level comment
        depth: Nesting depth (0 for top-level)
    """
    root: Comment
    depth: int = 0
    
    def flatten(self) -> List[Comment]:
        """Flatten the comment thread into a list."""
        result = [self.root]
        for reply in self.root.replies:
            result.extend(CommentThread(reply, self.depth + 1).flatten())
        return result