"""
Reply Handler

Handles recipient replies and reschedules remaining messages.
Uses jitter algorithm via clean 2-call pattern:
  1. schedule_message() - for immediate reply
  2. schedule_message_queue() - for rescheduled batch
"""

import logging
import uuid
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from jitter import Message, ScheduledMessage, JitterAlgorithm
from .models import Event, EventType
from .event_bus import EventBus

logger = logging.getLogger(__name__)


class ReplyHandler:
    """
    Handles recipient replies and manages message rescheduling.
    
    Clean design:
    - Pause remaining messages
    - Call jitter.schedule_message() for immediate reply
    - Call jitter.schedule_message_queue() for rescheduled batch
    - Naturally supports loops for multiple replies
    """
    
    def __init__(self, 
                 jitter_algorithm: JitterAlgorithm,
                 event_bus: EventBus,
                 scheduled_messages_by_recipient: Dict[str, List[ScheduledMessage]],
                 paused_messages: Dict[str, List[ScheduledMessage]],
                 recipient_engagement: Dict[str, Dict[str, Any]]):
        self.jitter_algorithm = jitter_algorithm
        self.event_bus = event_bus
        self.scheduled_messages_by_recipient = scheduled_messages_by_recipient
        self.paused_messages = paused_messages
        self.recipient_engagement = recipient_engagement
    
    def generate_immediate_reply(self, reply_content: str, recipient: str) -> Optional[str]:
        """
        Generate an immediate reply to recipient's message.
        Uses simple heuristics (can be enhanced with LLM later).
        """
        reply_lower = reply_content.lower().strip()
        
        # Simple response generation (can be enhanced with LLM)
        if any(word in reply_lower for word in ["yes", "ok", "sure", "alright", "okay"]):
            return "Great! Please click the link to verify your account."
        elif any(word in reply_lower for word in ["no", "stop", "unsubscribe", "remove"]):
            return "I understand. If you change your mind, the link will be available for 24 hours."
        elif any(word in reply_lower for word in ["what", "who", "why", "how"]):
            return "This is an automated security check. Please verify your account using the link."
        elif "?" in reply_content:
            return "Please use the verification link I sent earlier to complete the process."
        else:
            # Generic acknowledgment
            return "Thank you for your response. Please use the verification link to proceed."
    
    def handle_reply(self, reply_data: Dict[str, Any], memory: List[Dict[str, Any]]) -> None:
        """
        Handle a reply from a recipient using clean 2-call jitter pattern.
        
        Flow:
        1. Pause all remaining messages for this recipient
        2. CALL 1: schedule_message() - Send immediate reply (jitter handles timing)
        3. CALL 2: schedule_message_queue() - Reschedule remaining messages (jitter handles batch)
        4. Loop support: If another reply comes, this function is called again
        """
        recipient = reply_data.get("recipient")
        reply_content = reply_data.get("reply_content", "")
        original_message_id = reply_data.get("original_message_id")
        reply_time = datetime.now()
        
        if not recipient:
            logger.warning("Reply received but no recipient specified")
            return
        
        # Store in memory
        memory.append({
            "type": "reply",
            "timestamp": reply_time.isoformat(),
            "data": reply_data
        })
        
        # Mark recipient as engaged
        if recipient not in self.recipient_engagement:
            self.recipient_engagement[recipient] = {
                "engaged": False,
                "last_reply_time": None,
                "last_message_index": -1
            }
        
        self.recipient_engagement[recipient]["engaged"] = True
        self.recipient_engagement[recipient]["last_reply_time"] = reply_time
        
        # Find which message index this reply is for
        scheduled_messages = self.scheduled_messages_by_recipient.get(recipient, [])
        message_index = -1
        
        if original_message_id:
            # Try to find by original_message_id
            for i, scheduled_msg in enumerate(scheduled_messages):
                if scheduled_msg.message.original_message_id == original_message_id:
                    message_index = i
                    break
        
        # If not found by ID, assume it's for the last sent message
        if message_index < 0 and scheduled_messages:
            message_index = len(scheduled_messages) - 1
        
        if message_index >= 0:
            self.recipient_engagement[recipient]["last_message_index"] = message_index
        
        # STEP 1: Pause remaining messages for this recipient
        remaining_messages = scheduled_messages[message_index + 1:] if message_index >= 0 else scheduled_messages
        
        if remaining_messages:
            # Move to paused queue
            if recipient not in self.paused_messages:
                self.paused_messages[recipient] = []
            self.paused_messages[recipient].extend(remaining_messages)
            
            # Remove from scheduled queue
            self.scheduled_messages_by_recipient[recipient] = scheduled_messages[:message_index + 1]
            
            logger.info(f"Paused {len(remaining_messages)} remaining messages for {recipient}")
            
            # Publish pause event
            self.event_bus.publish(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.SCHEDULE_ADJUSTED,
                timestamp=reply_time,
                data={
                    "recipient": recipient,
                    "action": "paused",
                    "paused_count": len(remaining_messages),
                    "reason": "reply_received"
                }
            ))
        
        # STEP 2: Generate immediate reply
        immediate_reply = self.generate_immediate_reply(reply_content, recipient)
        immediate_scheduled_time = None
        
        if immediate_reply:
            # Create reply message object
            reply_message = Message(
                content=immediate_reply,
                recipient=recipient,
                is_correction=True  # Mark as follow-up/correction
            )
            
            # ===== CALL 1: Use jitter.schedule_message() =====
            # This handles:
            # - Complexity calculation
            # - Typing time (with thinking pauses)
            # - Delay calculation (jitter respects is_correction=True)
            # - Pattern avoidance
            # All in ONE clean call!
            scheduled_reply = self.jitter_algorithm.schedule_message(
                message=reply_message,
                current_time=reply_time
            )
            immediate_scheduled_time = scheduled_reply.scheduled_time
            
            # Add to scheduled queue
            if recipient not in self.scheduled_messages_by_recipient:
                self.scheduled_messages_by_recipient[recipient] = []
            self.scheduled_messages_by_recipient[recipient].append(scheduled_reply)
            
            logger.info(f"Scheduled immediate reply for {recipient} at {immediate_scheduled_time.strftime('%H:%M:%S')}")
            
            # Publish reply scheduled event
            self.event_bus.publish(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.MESSAGE_SCHEDULED,
                timestamp=datetime.now(),
                data={
                    "recipient": recipient,
                    "scheduled_time": immediate_scheduled_time.isoformat(),
                    "typing_duration": scheduled_reply.typing_duration,
                    "explanation": scheduled_reply.explanation,
                    "is_reply": True
                }
            ))
        
        # STEP 3: Reschedule remaining messages using jitter batch
        if remaining_messages:
            start_time = immediate_scheduled_time if immediate_reply else reply_time
            
            # Extract Message objects from ScheduledMessage objects
            # (remaining_messages are ScheduledMessage objects, but jitter expects Message objects)
            messages_to_reschedule = [sm.message for sm in remaining_messages]
            
            # ===== CALL 2: Use jitter.schedule_message_queue() =====
            # This handles:
            # - Complexity for each message
            # - Typing time for each message (with thinking pauses)
            # - Inter-message delays (with exponential randomness)
            # - Pattern avoidance across all messages
            # - Time window constraints
            # All in ONE clean batch call!
            rescheduled = self.jitter_algorithm.schedule_message_queue(
                messages=messages_to_reschedule,
                start_time=start_time,
                enforce_time_window=False  # No time window constraint for rescheduled
            )
            
            # Add rescheduled messages back to scheduled queue
            if recipient not in self.scheduled_messages_by_recipient:
                self.scheduled_messages_by_recipient[recipient] = []
            self.scheduled_messages_by_recipient[recipient].extend(rescheduled)
            
            # Clear paused messages
            self.paused_messages[recipient] = []
            
            logger.info(f"Rescheduled {len(rescheduled)} messages for {recipient} starting at {start_time.strftime('%H:%M:%S')}")
            
            # Publish reschedule event
            self.event_bus.publish(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.SCHEDULE_ADJUSTED,
                timestamp=datetime.now(),
                data={
                    "recipient": recipient,
                    "action": "rescheduled",
                    "rescheduled_count": len(rescheduled),
                    "reason": "reply_received_using_clean_jitter_calls"
                }
            ))
