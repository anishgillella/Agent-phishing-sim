"""
Agent Tools

LangChain tools for the SMS agent.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from langchain.tools import tool
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jitter import JitterAlgorithm, Message
from .models import Event, EventType
from .event_bus import EventBus

logger = logging.getLogger(__name__)


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
        messages: List[Dict[str, str]],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        enforce_time_window: bool = False,
        max_messages_per_hour: Optional[int] = None,
        distribution_mode: str = "clustered"
    ) -> List[Dict[str, Any]]:
        """
        Schedule multiple messages at once using the jitter algorithm.
        
        Args:
            messages: List of message dictionaries with 'content', 'recipient', and optional 'is_correction'
            start_time: Optional ISO format start time (e.g., "2025-11-12T09:00:00"). Defaults to now if not provided.
            end_time: Optional ISO format end time (required if enforce_time_window=True)
            enforce_time_window: If True, ensure all messages fit within start_time to end_time window
            max_messages_per_hour: Maximum messages per hour for density control (optional)
            distribution_mode: "clustered" (default) or "even" - how to distribute messages
        
        Returns:
            List of scheduled message dictionaries
        """
        import uuid
        from datetime import datetime as dt
        
        # Set batch mode to prevent schedule reviews during batch operations
        if agent_instance:
            agent_instance._batch_mode = True
        
        try:
            message_objects = []
            for msg in messages:
                msg_id = msg.get("original_message_id") or str(uuid.uuid4())
                message_objects.append(
                    Message(
                        content=msg["content"],
                        recipient=msg["recipient"],
                        is_correction=msg.get("is_correction", False),
                        original_message_id=msg_id
                    )
                )
            
            # Parse start_time and end_time if provided
            parsed_start_time = None
            parsed_end_time = None
            if start_time:
                try:
                    parsed_start_time = dt.fromisoformat(start_time.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid start_time format: {start_time}, using current time")
            if end_time:
                try:
                    parsed_end_time = dt.fromisoformat(end_time.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid end_time format: {end_time}, ignoring")
            
            # Validate: if enforce_time_window=True, end_time is required
            if enforce_time_window and not parsed_end_time:
                logger.warning("enforce_time_window=True but end_time not provided. Disabling time window enforcement.")
                enforce_time_window = False
            
            # Publish queued events
            for msg_obj in message_objects:
                event_bus.publish(Event(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.MESSAGE_QUEUED,
                    timestamp=datetime.now(),
                    data={"message": msg_obj.content, "recipient": msg_obj.recipient}
                ))
            
            scheduled = jitter_algorithm.schedule_message_queue(
                message_objects,
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                enforce_time_window=enforce_time_window,
                max_messages_per_hour=max_messages_per_hour,
                distribution_mode=distribution_mode
            )
            
            # Publish scheduled events
            for s in scheduled:
                event_bus.publish(Event(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.MESSAGE_SCHEDULED,
                    timestamp=datetime.now(),
                    data={
                        "scheduled_time": s.scheduled_time.isoformat(),
                        "typing_duration": s.typing_duration,
                        "explanation": s.explanation,
                        "recipient": s.message.recipient,
                        "message_content": s.message.content  # ✅ ADDED - for agent phase analysis
                    }
                ))
            
            # Store in agent's scheduled_messages_by_recipient if agent_instance available
            if agent_instance:
                for s in scheduled:
                    recipient = s.message.recipient
                    if recipient not in agent_instance.scheduled_messages_by_recipient:
                        agent_instance.scheduled_messages_by_recipient[recipient] = []
                    agent_instance.scheduled_messages_by_recipient[recipient].append(s)
            
            return [
                {
                    "scheduled_time": s.scheduled_time.isoformat(),
                    "typing_duration": s.typing_duration,
                    "explanation": s.explanation,
                    "message_content": s.message.content,
                    "recipient": s.message.recipient
                }
                for s in scheduled
            ]
        finally:
            # Always reset batch mode when done and process deferred events agent-driven
            if agent_instance:
                agent_instance._batch_mode = False
                # Process any deferred events agent-driven now that batch is complete
                if agent_instance._deferred_events:
                    logger.info(f"Processing {len(agent_instance._deferred_events)} deferred events agent-driven...")
                    deferred = agent_instance._deferred_events.copy()
                    agent_instance._deferred_events.clear()
                    for event in deferred:
                        if event.event_type == EventType.PATTERN_DETECTED:
                            if agent_instance.enable_llm_event_handling and not agent_instance._api_circuit_open:
                                agent_instance._agent_handle_pattern(event)
                            else:
                                agent_instance._handle_pattern(event.data)
    
    @tool
    def generate_messages(
        scenario_description: str,
        num_messages: int,
        recipients: List[str],
        message_types: Optional[List[str]] = None,
        sequence_strategy: Optional[str] = None,
        previous_messages_context: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Generate messages for a phishing simulation scenario.
        Creates COHERENT CAMPAIGN FLOWS per recipient with psychological manipulation.
        
        CRITICAL REQUIREMENTS:
        - Messages form coherent campaign sequences (not random)
        - ONE main campaign thread per recipient (not 5 different angles)
        - Natural progression: Alert → Urgency → Verification → Deadline → Follow-up
        - Complexity: 20% SIMPLE, 60% MEDIUM, 20% COMPLEX
        - EXACTLY num_messages messages generated
        - Realistic links (bit.ly/verify, verify-account-now.com)
        - Psychological manipulation: scarcity, urgency, authority, fear, social proof
        
        Args:
            scenario_description: Description of the scenario
            num_messages: Number of messages to generate (typically 50)
            recipients: List of recipient phone numbers
            message_types: Optional list of message types
            sequence_strategy: Optional strategy for sequencing
            previous_messages_context: Optional dict mapping recipient -> previous messages
        
        Returns:
            List of message dictionaries with 'content' and 'recipient'
        """
        import random
        from datetime import datetime, timedelta
        
        # SMISHING CAMPAIGN SEQUENCES - One coherent flow per recipient
        # CRITICAL: Vary links (not every message has one) and remove emojis from messages
        campaign_sequences = {
            "initial_alert": [
                "Security alert: Unusual login activity detected on your account from {location} at {timestamp}. Please verify your identity immediately.",
                "Alert: We detected suspicious activity on your account. Immediate verification required. Visit: verify-account-now.com",
                "Your account flagged for verification. Unauthorized login attempt detected from {location}. Action required immediately.",
            ],
            "urgency_building": [
                "URGENT: Complete account verification within 24 hours to prevent suspension.",
                "Your account will be locked in 12 hours if not verified. Verify now: verify-account-now.com/?id=secure",
                "Time-sensitive: Verify your identity immediately to maintain account access.",
                "Final warning: You have 6 hours to verify. After that, permanent suspension will occur.",
            ],
            "verification_request": [
                "Hello, this is an important security notification regarding your account. We've been conducting routine security checks and have identified some anomalies. Our system has flagged your account for potential security risks based on recent activity patterns, including login attempts from unfamiliar devices and locations. To protect your account and personal information, we require you to verify your identity through our secure verification portal.",
                "Account verification required to restore full access. Please verify your identity at: verify-account-now.com/secure-portal",
                "We need immediate verification of your account identity. This is your second notice. Complete verification within 2 hours.",
            ],
            "deadline_pressure": [
                "URGENT: Only 2 hours remaining to verify your account. After expiration, account will be permanently locked.",
                "Last chance: Your account verification window closes in 1 hour. Do not delay. This is your final notice.",
                "FINAL NOTICE: Account suspension imminent. Only 30 minutes to verify. Act immediately: verify-account-now.com",
            ],
            "follow_up": [
                "Haven't verified yet? Your account remains at critical risk. We sent you a verification link.",
                "Reminder: Your account verification is still incomplete. This is your final reminder.",
                "Account still unverified. We sent you a verification link. Check spam folder if needed.",
                "Status update: Verification still pending. Risk of suspension continues. This is your last chance.",
            ],
            "social_proof": [
                "Similar accounts have been compromised recently. Verify yours to stay safe.",
                "Other users reported suspicious activity from same IP location as yours. Immediate verification needed.",
                "Your organization recommends immediate verification due to recent security incidents in your region.",
            ]
        }
        
        # Calculate complexity distribution for 50 messages
        # 20% SIMPLE (10), 60% MEDIUM (30), 20% COMPLEX (10)
        num_simple = max(1, int(num_messages * 0.2))
        num_complex = max(1, int(num_messages * 0.2))
        num_medium = num_messages - num_simple - num_complex
        
        complexity_distribution = (
            ["simple"] * num_simple +
            ["medium"] * num_medium +
            ["complex"] * num_complex
        )
        random.shuffle(complexity_distribution)
        
        # Distribute messages per recipient
        messages_per_recipient = {}
        for i, recipient in enumerate(recipients):
            # Distribute as evenly as possible
            count = num_messages // len(recipients)
            if i < num_messages % len(recipients):
                count += 1
            messages_per_recipient[recipient] = count
        
        messages = []
        message_index = 0
        
        # Create ONE COHERENT CAMPAIGN THREAD per recipient
        for recipient in recipients:
            recipient_count = messages_per_recipient[recipient]
            recipient_messages = []
            
            # Define campaign progression for this recipient
            campaign_flow = [
                ("initial_alert", 1),      # 1-2 initial alerts
                ("urgency_building", 2),   # 2-3 urgency messages
                ("verification_request", 1), # 1-2 detailed verification requests
                ("deadline_pressure", 1),  # 1-2 deadline messages
                ("follow_up", 1),          # 1-2 follow-ups
            ]
            
            # Adjust distribution based on message count for this recipient
            if recipient_count <= 5:
                campaign_flow = [("initial_alert", 1), ("urgency_building", 1), ("verification_request", 1), ("follow_up", recipient_count - 3)]
            elif recipient_count <= 10:
                campaign_flow = [("initial_alert", 1), ("urgency_building", 2), ("verification_request", 1), ("deadline_pressure", 1), ("follow_up", recipient_count - 5)]
            
            # Generate campaign messages for this recipient
            for phase_name, phase_count in campaign_flow:
                if phase_name in campaign_sequences:
                    templates = campaign_sequences[phase_name]
                    for _ in range(phase_count):
                        if len(recipient_messages) < recipient_count:
                            template = random.choice(templates)
                            
                            # Add timestamp/location context
                            timestamp = datetime.now() + timedelta(hours=random.randint(0, 5))
                            location = random.choice(["Shanghai", "Moscow", "Lagos", "Bangalore", "Unknown"])
                            
                            content = template.format(
                                timestamp=timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                                location=location
                            )
                            
                            recipient_messages.append(content)
            
            # Pad with additional follow-ups if needed
            while len(recipient_messages) < recipient_count:
                template = random.choice(campaign_sequences["follow_up"])
                timestamp = datetime.now() + timedelta(hours=random.randint(0, 5))
                location = random.choice(["Shanghai", "Moscow", "Lagos", "Bangalore"])
                content = template.format(timestamp=timestamp.strftime("%Y-%m-%d %H:%M UTC"), location=location)
                recipient_messages.append(content)
            
            # Add messages with complexity tracking
            for msg_content in recipient_messages:
                complexity_type = complexity_distribution[message_index % len(complexity_distribution)]
                messages.append({
                    "content": msg_content,
                    "recipient": recipient,
                    "complexity": complexity_type
                })
                message_index += 1
        
        # Ensure EXACTLY num_messages
        if len(messages) > num_messages:
            messages = messages[:num_messages]
        elif len(messages) < num_messages:
            # Fill remaining with follow-ups
            while len(messages) < num_messages:
                recipient = random.choice(recipients)
                template = random.choice(campaign_sequences["follow_up"])
                timestamp = datetime.now() + timedelta(hours=random.randint(0, 5))
                location = random.choice(["Shanghai", "Moscow", "Lagos"])
                content = template.format(timestamp=timestamp.strftime("%Y-%m-%d %H:%M UTC"), location=location)
                messages.append({
                    "content": content,
                    "recipient": recipient,
                    "complexity": random.choice(["simple", "medium"])
                })
        
        return messages
    
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
            # Check if we're already handling a reply (prevent event loop)
            # If agent is handling via LLM, call reply handler directly
            if agent_instance.enable_llm_event_handling:
                # Direct call to reply handler (bypasses event publishing to avoid loop)
                reply_data = {
                    "recipient": recipient,
                    "reply_content": reply_content,
                    "original_message_id": original_message_id
                }
                agent_instance.reply_handler.handle_reply(reply_data, agent_instance.memory)
                
                return {
                    "action": "reply_handled_by_agent",
                    "recipient": recipient,
                    "paused_messages": len(agent_instance.paused_messages.get(recipient, [])),
                    "immediate_reply_scheduled": True,
                    "remaining_messages_rescheduled": True,
                    "note": "Agent made decision and executed reply handling"
                }
            else:
                # Direct mode: publish event (will trigger handler)
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
    
    return [schedule_message, schedule_batch, generate_messages, handle_reply]

