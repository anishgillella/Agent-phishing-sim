"""
Part 1: Jitter Algorithm

Designs a message scheduling algorithm that models realistic human SMS behavior.
Considers typing time, thinking pauses, pattern avoidance, and realistic randomness.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MessageComplexity(Enum):
    """Message complexity levels affecting typing time."""
    SIMPLE = "simple"  # Short, common phrases (5-20 words)
    MEDIUM = "medium"  # Standard messages (20-50 words)
    COMPLEX = "complex"  # Long, detailed messages (50+ words)
    CORRECTION = "correction"  # Quick follow-up corrections


@dataclass
class Message:
    """Represents a message to be sent."""
    content: str
    recipient: str
    complexity: Optional[MessageComplexity] = None  # Determined by algorithm if not provided
    is_correction: bool = False
    original_message_id: Optional[str] = None


@dataclass
class ScheduledMessage:
    """Represents a scheduled message with timing explanation."""
    message: Message
    scheduled_time: datetime
    typing_duration: float  # seconds
    explanation: str


class HumanTypingModel:
    """
    Models human typing behavior based on message characteristics.
    
    Based on research:
    - Average typing speed: 40 WPM (words per minute)
    - Range: 20-80 WPM depending on skill
    - Thinking pauses: 2-30 seconds
    - Correction time: immediate to 5 minutes
    """
    
    # Words per minute ranges by complexity
    WPM_RANGES = {
        MessageComplexity.SIMPLE: (35, 50),  # Faster for simple messages
        MessageComplexity.MEDIUM: (30, 45),
        MessageComplexity.COMPLEX: (25, 40),  # Slower for complex
        MessageComplexity.CORRECTION: (40, 60),  # Fast corrections
    }
    
    # Thinking pause probabilities and durations
    THINKING_PAUSE_PROBABILITY = 0.3  # 30% chance of pause
    THINKING_PAUSE_MIN = 2.0  # seconds
    THINKING_PAUSE_MAX = 30.0  # seconds
    
    @staticmethod
    def estimate_word_count(text: str) -> int:
        """Estimate word count from message content."""
        return len(text.split())
    
    @staticmethod
    def calculate_typing_time(message: Message) -> Tuple[float, str]:
        """
        Calculate realistic typing time for a message.
        
        Returns:
            Tuple of (typing_duration_seconds, explanation)
        """
        word_count = HumanTypingModel.estimate_word_count(message.content)
        
        # Get WPM range for complexity
        wpm_min, wpm_max = HumanTypingModel.WPM_RANGES[message.complexity]
        
        # Add some randomness to typing speed (humans vary)
        wpm = random.uniform(wpm_min, wpm_max)
        
        # Calculate base typing time
        words_per_second = wpm / 60.0
        base_typing_time = word_count / words_per_second
        
        # Add thinking pauses (humans pause while composing)
        thinking_pause = 0.0
        pause_explanation = ""
        if random.random() < HumanTypingModel.THINKING_PAUSE_PROBABILITY:
            thinking_pause = random.uniform(
                HumanTypingModel.THINKING_PAUSE_MIN,
                HumanTypingModel.THINKING_PAUSE_MAX
            )
            pause_explanation = f" (includes {thinking_pause:.1f}s thinking pause)"
        
        total_time = base_typing_time + thinking_pause
        
        # Ensure minimum time (humans don't type instantly)
        min_time = 5.0 if not message.is_correction else 2.0
        total_time = max(total_time, min_time)
        
        explanation = (
            f"Typing {word_count} words at ~{wpm:.0f} WPM "
            f"({base_typing_time:.1f}s base{pause_explanation})"
        )
        
        return total_time, explanation


class TimePatternModel:
    """
    Models time-of-day patterns in human messaging behavior.
    
    Humans tend to:
    - Cluster messages around certain times (hour boundaries, after meetings)
    - Send more during work hours
    - Have natural breaks (lunch, meetings)
    """
    
    # Work hours (9 AM - 5 PM)
    WORK_START_HOUR = 9
    WORK_END_HOUR = 17
    
    # Peak activity times (more likely to send)
    PEAK_HOURS = [9, 10, 11, 14, 15, 16]  # Morning and afternoon peaks
    
    @staticmethod
    def get_time_cluster_factor(current_time: datetime) -> float:
        """
        Returns a factor indicating how likely messages are at this time.
        Higher factor = more likely to send multiple messages.
        """
        hour = current_time.hour
        
        # Outside work hours: lower activity
        if hour < TimePatternModel.WORK_START_HOUR or hour >= TimePatternModel.WORK_END_HOUR:
            return 0.3
        
        # Peak hours: higher activity
        if hour in TimePatternModel.PEAK_HOURS:
            return 1.2
        
        # Regular work hours
        return 0.8
    
    @staticmethod
    def should_cluster_around_time(current_time: datetime) -> bool:
        """
        Determines if messages should cluster around this time.
        Humans often send messages at hour boundaries or after meetings.
        """
        minute = current_time.minute
        
        # More likely to cluster at :00, :15, :30, :45 (meeting boundaries)
        if minute in [0, 15, 30, 45]:
            return random.random() < 0.4
        
        return random.random() < 0.1


class PatternAvoidance:
    """
    Avoids detectable patterns in message timing.
    
    Techniques:
    - Track historical send times
    - Avoid uniform intervals
    - Add anti-pattern randomness
    """
    
    def __init__(self):
        self.historical_times: List[datetime] = []
    
    def add_sent_time(self, send_time: datetime):
        """Record a sent message time."""
        self.historical_times.append(send_time)
    
    def calculate_anti_pattern_delay(self, base_delay: float) -> float:
        """
        Add randomness to avoid uniform patterns.
        Uses non-uniform distribution (exponential-like) to mimic human behavior.
        """
        # Use exponential distribution for more realistic delays
        # Humans have bursts followed by longer pauses
        multiplier = random.expovariate(1.0 / base_delay)
        
        # Cap at reasonable maximum (don't wait days)
        max_delay = base_delay * 3
        return min(multiplier * base_delay, max_delay)
    
    def check_pattern_violation(self, proposed_time: datetime, 
                                min_interval: float = 30.0) -> bool:
        """
        Check if proposed time violates anti-pattern rules.
        Returns True if time is acceptable, False if it creates a pattern.
        """
        if not self.historical_times:
            return True
        
        # Check minimum interval between messages
        for past_time in self.historical_times[-5:]:  # Check last 5 messages
            interval = abs((proposed_time - past_time).total_seconds())
            if interval < min_interval:
                return False
        
        return True


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
                        previous_scheduled_time: Optional[datetime] = None) -> ScheduledMessage:
        """
        Schedule a single message with human-realistic timing.
        
        Args:
            message: Message to schedule
            current_time: Current time
            previous_scheduled_time: Time of previously scheduled message (if any)
        
        Returns:
            ScheduledMessage with timing and explanation
        """
        # Determine complexity
        message.complexity = self.determine_message_complexity(message)
        
        # Calculate typing time
        typing_duration, typing_explanation = self.typing_model.calculate_typing_time(message)
        
        # Calculate when to start typing (and thus when to send)
        if previous_scheduled_time:
            # Calculate delay from previous message
            delay = self.calculate_inter_message_delay(
                previous_scheduled_time, current_time, message
            )
            start_typing_time = previous_scheduled_time + timedelta(seconds=delay)
        else:
            # First message: start soon but not instantly
            start_typing_time = current_time + timedelta(seconds=random.uniform(10.0, 60.0))
        
        # Ensure we don't schedule in the past
        if start_typing_time < current_time:
            start_typing_time = current_time + timedelta(seconds=random.uniform(10.0, 60.0))
        
        # Add typing duration to get send time
        scheduled_send_time = start_typing_time + timedelta(seconds=typing_duration)
        
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
                              start_time: Optional[datetime] = None) -> List[ScheduledMessage]:
        """
        Schedule a queue of messages with human-realistic timing.
        
        Args:
            messages: List of messages to schedule
            start_time: When to start scheduling (defaults to now)
        
        Returns:
            List of ScheduledMessage objects in order
        """
        if start_time is None:
            start_time = datetime.now()
        
        scheduled_messages: List[ScheduledMessage] = []
        previous_time: Optional[datetime] = None
        
        for message in messages:
            scheduled = self.schedule_message(
                message=message,
                current_time=start_time,
                previous_scheduled_time=previous_time
            )
            
            scheduled_messages.append(scheduled)
            previous_time = scheduled.scheduled_time
            
            # Update pattern avoidance with this scheduled time
            self.pattern_avoidance.add_sent_time(scheduled.scheduled_time)
        
        return scheduled_messages


# Example usage and testing
if __name__ == "__main__":
    # Example messages
    messages = [
        Message(content="Hey, can you check the report?", recipient="+1234567890"),
        Message(content="Actually, make sure to include the Q4 numbers too", recipient="+1234567890", is_correction=True),
        Message(content="Thanks! Let me know when you're done.", recipient="+1234567890"),
        Message(
            content="I need you to review the quarterly financial report and provide feedback on the revenue projections. Please pay special attention to the assumptions we made about market growth and customer acquisition costs.",
            recipient="+1234567890"
        ),
    ]
    
    # Initialize algorithm
    jitter = JitterAlgorithm()
    
    # Schedule messages
    scheduled = jitter.schedule_message_queue(messages)
    
    # Display results
    print("=" * 80)
    print("Jitter Algorithm - Scheduled Messages")
    print("=" * 80)
    print()
    
    for i, scheduled_msg in enumerate(scheduled, 1):
        print(f"Message {i}:")
        print(f"  Content: {scheduled_msg.message.content[:60]}...")
        print(f"  Scheduled Time: {scheduled_msg.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Typing Duration: {scheduled_msg.typing_duration:.1f}s")
        print(f"  Explanation: {scheduled_msg.explanation}")
        print()

