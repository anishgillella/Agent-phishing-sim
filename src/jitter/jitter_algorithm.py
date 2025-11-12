"""
Jitter Algorithm

Main algorithm that schedules messages with human-realistic timing.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .models import (
    Message, ScheduledMessage, MessageComplexity,
    HumanTypingModel, TimePatternModel, PatternAvoidance
)


class JitterAlgorithm:
    """
    Main jitter algorithm that schedules messages with human-realistic timing.
    """
    
    def __init__(self):
        self.pattern_avoidance = PatternAvoidance()
        self.time_model = TimePatternModel()
        self.typing_model = HumanTypingModel()
    
    def determine_message_complexity(self, message: Message) -> MessageComplexity:
        """Determine message complexity from content."""
        if message.is_correction:
            return MessageComplexity.CORRECTION
        
        word_count = self.typing_model.estimate_word_count(message.content)
        
        if word_count < 20:
            return MessageComplexity.SIMPLE
        elif word_count < 50:
            return MessageComplexity.MEDIUM
        else:
            return MessageComplexity.COMPLEX
    
    def calculate_inter_message_delay(self, 
                                     previous_time: Optional[datetime],
                                     current_time: datetime,
                                     message: Message) -> float:
        """
        Calculate delay between messages.
        Considers time patterns, clustering, and anti-pattern measures.
        """
        # Base delay: humans don't send messages instantly
        if message.is_correction:
            # Corrections can be immediate or delayed (humans vary)
            if random.random() < 0.3:  # 30% immediate
                return random.uniform(5.0, 30.0)
            else:
                return random.uniform(60.0, 300.0)  # 1-5 minutes
        
        # Regular messages: longer delays
        base_delay = random.uniform(120.0, 600.0)  # 2-10 minutes base
        
        # Adjust for time patterns
        cluster_factor = self.time_model.get_time_cluster_factor(current_time)
        if self.time_model.should_cluster_around_time(current_time):
            # Reduce delay if clustering
            base_delay *= 0.3
        
        # Apply anti-pattern adjustments
        adjusted_delay = self.pattern_avoidance.calculate_anti_pattern_delay(base_delay)
        
        return adjusted_delay
    
    def schedule_message(self,
                        message: Message,
                        current_time: datetime,
                        previous_scheduled_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        max_delay: Optional[float] = None,
                        target_interval: Optional[float] = None) -> ScheduledMessage:
        """
        Schedule a single message with human-realistic timing.
        
        Args:
            message: Message to schedule
            current_time: Current time
            previous_scheduled_time: Time of previously scheduled message (if any)
            end_time: Optional end time for time window constraint
            max_delay: Optional maximum delay in seconds (for time window enforcement)
            target_interval: Optional target interval in seconds (for even distribution)
        
        Returns:
            ScheduledMessage with timing and explanation
        """
        # Determine complexity
        message.complexity = self.determine_message_complexity(message)
        
        # Calculate typing time
        typing_duration, typing_explanation = self.typing_model.calculate_typing_time(message)
        
        # Calculate when to start typing (and thus when to send)
        if previous_scheduled_time:
            if target_interval is not None:
                # Even distribution mode: use target interval
                delay = target_interval
            else:
                # Calculate delay from previous message using jitter algorithm
                delay = self.calculate_inter_message_delay(
                    previous_scheduled_time, current_time, message
                )
            
            # Apply max_delay constraint if provided
            if max_delay is not None:
                delay = min(delay, max_delay)
            
            start_typing_time = previous_scheduled_time + timedelta(seconds=delay)
        else:
            # First message: start soon but not instantly
            first_delay = random.uniform(10.0, 60.0)
            if max_delay is not None:
                first_delay = min(first_delay, max_delay)
            start_typing_time = current_time + timedelta(seconds=first_delay)
        
        # Ensure we don't schedule in the past
        if start_typing_time < current_time:
            start_typing_time = current_time + timedelta(seconds=random.uniform(10.0, 60.0))
        
        # Add typing duration to get send time
        scheduled_send_time = start_typing_time + timedelta(seconds=typing_duration)
        
        # Check end_time constraint
        if end_time and scheduled_send_time > end_time:
            # Adjust to fit within window
            # Schedule at end_time minus typing duration
            adjusted_start_time = end_time - timedelta(seconds=typing_duration)
            if adjusted_start_time < (previous_scheduled_time or current_time):
                # Can't fit typing time, schedule at end_time
                scheduled_send_time = end_time
            else:
                scheduled_send_time = end_time
                start_typing_time = adjusted_start_time
        
        # Verify no pattern violations
        max_attempts = 10
        attempt = 0
        while not self.pattern_avoidance.check_pattern_violation(scheduled_send_time) and attempt < max_attempts:
            # Add small random adjustment
            adjustment = random.uniform(30.0, 120.0)
            scheduled_send_time += timedelta(seconds=adjustment)
            attempt += 1
        
        # Build explanation
        if previous_scheduled_time:
            interval = (scheduled_send_time - previous_scheduled_time).total_seconds()
            explanation = (
                f"{typing_explanation}. "
                f"Inter-message interval: {interval/60:.1f} minutes "
                f"(accounts for human pacing and time-of-day patterns)."
            )
        else:
            explanation = (
                f"{typing_explanation}. "
                f"Initial message scheduled with realistic startup delay."
            )
        
        return ScheduledMessage(
            message=message,
            scheduled_time=scheduled_send_time,
            typing_duration=typing_duration,
            explanation=explanation
        )
    
    def schedule_message_queue(self,
                              messages: List[Message],
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              enforce_time_window: bool = False,
                              max_messages_per_hour: Optional[int] = None,
                              distribution_mode: str = "clustered") -> List[ScheduledMessage]:
        """
        Schedule a queue of messages with human-realistic timing.
        
        Args:
            messages: List of messages to schedule
            start_time: When to start scheduling (defaults to now)
            end_time: Optional end time for time window (required if enforce_time_window=True)
            enforce_time_window: If True, ensure all messages fit within start_time to end_time window
            max_messages_per_hour: Maximum messages per hour for density control (optional)
            distribution_mode: "clustered" (default) or "even" - how to distribute messages
        
        Returns:
            List of ScheduledMessage objects in order
        """
        if start_time is None:
            start_time = datetime.now()
        
        if enforce_time_window and end_time is None:
            raise ValueError("end_time is required when enforce_time_window=True")
        
        if enforce_time_window and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        
        # Calculate available time window
        if enforce_time_window:
            total_seconds = (end_time - start_time).total_seconds()
            total_hours = total_seconds / 3600.0
            
            # Calculate minimum required time
            min_interval = 30.0  # Minimum 30 seconds between messages
            min_required_time = len(messages) * min_interval
            
            if min_required_time > total_seconds:
                raise ValueError(
                    f"Cannot fit {len(messages)} messages in {total_hours:.1f} hour window. "
                    f"Minimum required: {min_required_time/3600:.1f} hours"
                )
            
            # Calculate target distribution
            if distribution_mode == "even":
                # Even distribution: calculate target interval
                target_interval = total_seconds / len(messages)
            else:
                # Clustered: use jitter algorithm delays
                target_interval = None
        else:
            total_seconds = None
            total_hours = None
            target_interval = None
        
        scheduled_messages: List[ScheduledMessage] = []
        previous_time: Optional[datetime] = None
        
        # Track messages per hour for density control
        messages_by_hour: Dict[int, int] = {}
        
        for i, message in enumerate(messages):
            # Check if we need to adjust for time window
            if enforce_time_window and end_time:
                # Calculate remaining messages and time
                remaining_messages = len(messages) - i
                if previous_time:
                    remaining_time = (end_time - previous_time).total_seconds()
                else:
                    remaining_time = (end_time - start_time).total_seconds()
                
                # Calculate maximum delay to fit remaining messages
                if remaining_messages > 0:
                    max_delay = remaining_time / remaining_messages
                    # Ensure minimum interval
                    max_delay = max(max_delay, 30.0)
                else:
                    max_delay = None
            else:
                max_delay = None
            
            # Schedule message
            scheduled = self.schedule_message(
                message=message,
                current_time=start_time,
                previous_scheduled_time=previous_time,
                end_time=end_time if enforce_time_window else None,
                max_delay=max_delay,
                target_interval=target_interval if distribution_mode == "even" else None
            )
            
            # Check density limits
            if max_messages_per_hour:
                message_hour = scheduled.scheduled_time.hour
                messages_this_hour = messages_by_hour.get(message_hour, 0)
                
                if messages_this_hour >= max_messages_per_hour:
                    # Adjust to next hour or reduce delay
                    if previous_time:
                        # Move to start of next hour
                        next_hour_start = scheduled.scheduled_time.replace(
                            minute=0, second=0, microsecond=0
                        ) + timedelta(hours=1)
                        if next_hour_start <= (end_time if enforce_time_window else scheduled.scheduled_time + timedelta(hours=24)):
                            scheduled = ScheduledMessage(
                                message=scheduled.message,
                                scheduled_time=next_hour_start,
                                typing_duration=scheduled.typing_duration,
                                explanation=f"{scheduled.explanation} (adjusted for density limit)"
                            )
                
                messages_by_hour[message_hour] = messages_by_hour.get(message_hour, 0) + 1
            
            # Validate time window constraint
            if enforce_time_window and end_time:
                if scheduled.scheduled_time > end_time:
                    # Adjust to fit within window
                    # Use remaining time divided by remaining messages
                    remaining_messages = len(messages) - i - 1
                    if remaining_messages > 0:
                        # Back-calculate: fit remaining messages before end_time
                        adjusted_time = end_time - timedelta(
                            seconds=(remaining_messages * (max_delay or 60.0))
                        )
                        scheduled = ScheduledMessage(
                            message=scheduled.message,
                            scheduled_time=max(adjusted_time, previous_time + timedelta(seconds=30)) if previous_time else adjusted_time,
                            typing_duration=scheduled.typing_duration,
                            explanation=f"{scheduled.explanation} (adjusted to fit time window)"
                        )
                    else:
                        # Last message: schedule at end_time
                        scheduled = ScheduledMessage(
                            message=scheduled.message,
                            scheduled_time=end_time,
                            typing_duration=scheduled.typing_duration,
                            explanation=f"{scheduled.explanation} (scheduled at window end)"
                        )
            
            scheduled_messages.append(scheduled)
            previous_time = scheduled.scheduled_time
            
            # Update pattern avoidance with this scheduled time
            self.pattern_avoidance.add_sent_time(scheduled.scheduled_time)
        
        return scheduled_messages

