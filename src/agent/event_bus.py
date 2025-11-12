"""
Event Bus

Event-driven architecture for handling system events.
"""

from typing import List, Dict, Optional, Callable
import logging

from .models import Event, EventType

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for event-driven architecture.
    Handles event publishing and subscription.
    """
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe a handler to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self.event_history.append(event)
        
        # Notify subscribers
        handlers = self.subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.event_type.value}: {e}", exc_info=True)
    
    def get_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self.event_history if e.event_type == event_type]
        return self.event_history

