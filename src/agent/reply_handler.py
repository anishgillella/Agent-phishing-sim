"""
Reply Handler

Handles recipient replies and reschedules remaining messages.
"""

import random
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
        Handle a reply from a recipient.
        
        Flow:
        1. Pause all remaining messages for this recipient
        2. Send immediate reply (30-120 seconds)
        3. Reschedule remaining messages with extended delays (2-5 minutes)
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
        # In production, this would be tracked via message delivery callbacks
        if message_index < 0 and scheduled_messages:
            # Assume reply is for the most recently sent message
            # In real scenario, we'd track which messages were actually sent
            message_index = len(scheduled_messages) - 1
        
        if message_index >= 0:
            self.recipient_engagement[recipient]["last_message_index"] = message_index
        
        # Step 1: Pause remaining messages for this recipient
        # Pause all messages after the one that received the reply
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
        
        # Step 2: Generate and send immediate reply (30-120 seconds)
        immediate_reply = self.generate_immediate_reply(reply_content, recipient)
        immediate_scheduled_time = None
        
        if immediate_reply:
            # Schedule immediate reply with short delay (30-120 seconds)
            reply_delay = random.uniform(30.0, 120.0)  # Human-like response time
            immediate_scheduled_time = reply_time + timedelta(seconds=reply_delay)
            
            reply_message = Message(
                content=immediate_reply,
                recipient=recipient,
                is_correction=True  # Mark as follow-up/correction
            )
            
            scheduled_reply = ScheduledMessage(
                message=reply_message,
                scheduled_time=immediate_scheduled_time,
                typing_duration=random.uniform(5.0, 15.0),  # Quick reply typing time
                explanation=f"Immediate reply to recipient response (scheduled {reply_delay:.1f}s after reply received)"
            )
            
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
        
        # Step 3: Reschedule remaining messages with extended delays (2-5 minutes between messages)
        if remaining_messages:
            self._reschedule_remaining_messages(recipient, immediate_scheduled_time if immediate_reply else reply_time)
    
    def _reschedule_remaining_messages(self, recipient: str, start_time: datetime):
        """
        Reschedule remaining paused messages using jitter algorithm.
        Respects message complexity and correction flags.
        Only slightly extends delays for engaged conversations (1.2-1.5x multiplier).
        """
        if recipient not in self.paused_messages or not self.paused_messages[recipient]:
            return
        
        paused = self.paused_messages[recipient]
        rescheduled: List[ScheduledMessage] = []
        current_time = start_time
        
        logger.info(f"Rescheduling {len(paused)} remaining messages for {recipient}")
        
        for paused_msg in paused:
            # Ensure message complexity is determined (needed for delay calculation)
            if paused_msg.message.complexity is None:
                paused_msg.message.complexity = self.jitter_algorithm.determine_message_complexity(
                    paused_msg.message
                )
            
            # Use jitter algorithm's delay calculation (respects complexity, corrections, etc.)
            base_delay = self.jitter_algorithm.calculate_inter_message_delay(
                previous_time=current_time,
                current_time=current_time,
                message=paused_msg.message
            )
            
            # Slightly extend delay for engaged conversations (1.2-1.5x multiplier)
            # This accounts for active conversation pacing without being too rigid
            engagement_multiplier = random.uniform(1.2, 1.5)
            adjusted_delay = base_delay * engagement_multiplier
            
            # Calculate typing time (respects message complexity)
            typing_duration, typing_explanation = self.jitter_algorithm.typing_model.calculate_typing_time(
                paused_msg.message
            )
            
            # Calculate new scheduled time
            new_scheduled_time = current_time + timedelta(seconds=adjusted_delay + typing_duration)
            
            # Create rescheduled message
            rescheduled_msg = ScheduledMessage(
                message=paused_msg.message,
                scheduled_time=new_scheduled_time,
                typing_duration=typing_duration,
                explanation=(
                    f"Rescheduled after reply. "
                    f"Base delay: {base_delay/60:.1f} min (jitter algo), "
                    f"Extended: {adjusted_delay/60:.1f} min (engaged conversation), "
                    f"Typing: {typing_duration:.1f}s ({typing_explanation})"
                )
            )
            
            rescheduled.append(rescheduled_msg)
            current_time = new_scheduled_time
            
            # Update pattern avoidance with this scheduled time
            self.jitter_algorithm.pattern_avoidance.add_sent_time(new_scheduled_time)
        
        # Add rescheduled messages back to scheduled queue
        if recipient not in self.scheduled_messages_by_recipient:
            self.scheduled_messages_by_recipient[recipient] = []
        self.scheduled_messages_by_recipient[recipient].extend(rescheduled)
        
        # Clear paused messages
        self.paused_messages[recipient] = []
        
        logger.info(f"Rescheduled {len(rescheduled)} messages for {recipient}")
        
        # Publish reschedule event
        self.event_bus.publish(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SCHEDULE_ADJUSTED,
            timestamp=datetime.now(),
            data={
                "recipient": recipient,
                "action": "rescheduled",
                "rescheduled_count": len(rescheduled),
                "reason": "reply_received_using_jitter_algo"
            }
        ))

