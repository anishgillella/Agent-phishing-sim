"""
Agent Tools

LangChain tools for the SMS agent.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from langchain.tools import tool
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jitter import JitterAlgorithm, Message
from .models import Event, EventType
from .event_bus import EventBus


def create_jitter_tools(jitter_algorithm: JitterAlgorithm, event_bus: EventBus, agent_instance: Optional[Any] = None):
    """
    Create jitter algorithm tools for the agent.
    
    Args:
        jitter_algorithm: JitterAlgorithm instance
        event_bus: EventBus instance
        agent_instance: Optional SMSAgent instance for reply handling
    
    Returns:
        List of tool functions
    """
    
    @tool
    def schedule_message(
        message_content: str,
        recipient: str,
        is_correction: bool = False
    ) -> Dict[str, Any]:
        """
        Schedule a single message using the jitter algorithm.
        
        Args:
            message_content: The message text to send
            recipient: Phone number of recipient
            is_correction: Whether this is a correction/follow-up message
        
        Returns:
            Dictionary with scheduled time, typing duration, and explanation
        """
        message = Message(
            content=message_content,
            recipient=recipient,
            is_correction=is_correction
        )
        
        # Publish queued event
        event_bus.publish(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.MESSAGE_QUEUED,
            timestamp=datetime.now(),
            data={"message": message_content, "recipient": recipient}
        ))
        
        # Schedule the message
        scheduled = jitter_algorithm.schedule_message(
            message=message,
            current_time=datetime.now()
        )
        
        # Publish scheduled event
        event_bus.publish(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.MESSAGE_SCHEDULED,
            timestamp=datetime.now(),
            data={
                "scheduled_time": scheduled.scheduled_time.isoformat(),
                "typing_duration": scheduled.typing_duration,
                "explanation": scheduled.explanation
            }
        ))
        
        return {
            "scheduled_time": scheduled.scheduled_time.isoformat(),
            "typing_duration": scheduled.typing_duration,
            "explanation": scheduled.explanation,
            "message_content": message_content
        }
    
    @tool
    def schedule_batch(
        messages: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Schedule multiple messages at once using the jitter algorithm.
        
        Args:
            messages: List of message dictionaries with 'content', 'recipient', and optional 'is_correction'
        
        Returns:
            List of scheduled message dictionaries
        """
        message_objects = [
            Message(
                content=msg["content"],
                recipient=msg["recipient"],
                is_correction=msg.get("is_correction", False)
            )
            for msg in messages
        ]
        
        scheduled = jitter_algorithm.schedule_message_queue(message_objects)
        
        return [
            {
                "scheduled_time": s.scheduled_time.isoformat(),
                "typing_duration": s.typing_duration,
                "explanation": s.explanation,
                "message_content": s.message.content
            }
            for s in scheduled
        ]
    
    @tool
    def analyze_pattern(
        pattern_description: str
    ) -> Dict[str, Any]:
        """
        Analyze a detected pattern and provide recommendations.
        
        Args:
            pattern_description: Description of the detected pattern
        
        Returns:
            Analysis with recommendations
        """
        # This would use the agent's LLM to analyze
        # For now, return structured format
        return {
            "pattern_detected": True,
            "description": pattern_description,
            "recommendation": "Adjust schedule to break pattern"
        }
    
    @tool
    def handle_reply(
        recipient: str,
        reply_content: str,
        original_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a reply from a recipient.
        This will:
        1. Pause all remaining messages for this recipient
        2. Send an immediate reply (30-120 seconds)
        3. Reschedule remaining messages with extended delays (2-5 minutes)
        
        Args:
            recipient: Phone number of recipient
            reply_content: Content of the reply received
            original_message_id: ID of the original message being replied to
        
        Returns:
            Dictionary with action taken and details
        """
        if agent_instance:
            # Use agent's reply handling method
            agent_instance.receive_reply(recipient, reply_content, original_message_id)
            return {
                "action": "reply_handled",
                "recipient": recipient,
                "paused_messages": len(agent_instance.paused_messages.get(recipient, [])),
                "immediate_reply_scheduled": True,
                "remaining_messages_rescheduled": True
            }
        else:
            # Fallback: just publish event
            event_bus.publish(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.REPLY_RECEIVED,
                timestamp=datetime.now(),
                data={
                    "recipient": recipient,
                    "reply_content": reply_content,
                    "original_message_id": original_message_id
                }
            ))
            return {
                "action": "reply_event_published",
                "recipient": recipient,
                "note": "Agent instance not available, event published only"
            }
    
    return [schedule_message, schedule_batch, analyze_pattern, handle_reply]

