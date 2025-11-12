"""
Models and Enums for Agent Module

All data models and enums for the agent package.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class EventType(Enum):
    """Types of events in the jitter algorithm workflow."""
    MESSAGE_QUEUED = "message_queued"
    MESSAGE_SCHEDULED = "message_scheduled"
    TYPING_STARTED = "typing_started"
    MESSAGE_SENT = "message_sent"
    REPLY_RECEIVED = "reply_received"
    PATTERN_DETECTED = "pattern_detected"
    SCHEDULE_ADJUSTED = "schedule_adjusted"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """Represents an event in the system."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "context": self.context or {},
        }
