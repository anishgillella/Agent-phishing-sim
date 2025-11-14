"""
Models and Classes for Jitter Algorithm

All data models, enums, and classes for the jitter algorithm package.
"""

import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple, List, Dict


# ========== ENUMS ==========

class MessageComplexity(Enum):
    """Message complexity levels affecting typing time."""
    SIMPLE = "simple"  # Short, common phrases (5-20 words)
    MEDIUM = "medium"  # Standard messages (20-50 words)
    COMPLEX = "complex"  # Long, detailed messages (50+ words)
    CORRECTION = "correction"  # Quick follow-up corrections


# ========== DATA MODELS ==========

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
    jitter_details: Optional[Dict] = None  # Detailed jitter factors applied


# ========== BEHAVIORAL CLASSES ==========

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
    def calculate_typing_time(message: Message) -> Tuple[float, str, Dict]:
        """
        Calculate realistic typing time for a message.
        
        Returns:
            Tuple of (typing_duration_seconds, explanation, detailed_metrics)
        """
        word_count = HumanTypingModel.estimate_word_count(message.content)
        
        # Get WPM range for complexity
        wpm_min, wpm_max = HumanTypingModel.WPM_RANGES[message.complexity]
        
        # Add some randomness to typing speed (humans vary)
        wpm = random.uniform(wpm_min, wpm_max)
        
        # Calculate base typing time
        words_per_second = wpm / 60.0
        base_typing_time = word_count / words_per_second
        
        # Add thinking pauses (humans pause while composing - NOT at end, but MID-MESSAGE)
        thinking_pause = 0.0
        pause_explanation = ""
        has_thinking_pause = False
        pause_position_ratio = 0.5  # Default: middle (0.0-1.0, where 0=start, 1=end)
        
        if random.random() < HumanTypingModel.THINKING_PAUSE_PROBABILITY:
            # YES, this message gets a pause
            thinking_pause = random.uniform(
                HumanTypingModel.THINKING_PAUSE_MIN,
                HumanTypingModel.THINKING_PAUSE_MAX
            )
            
            # RANDOMIZE PAUSE POSITION (not always at 50%)
            # Position varies: 20% (early), 50% (middle), 80% (late), etc.
            pause_position_ratio = random.uniform(0.25, 0.75)  # Pause between 25%-75% of typing
            
            pause_explanation = (
                f" (includes {thinking_pause:.1f}s thinking pause at {pause_position_ratio*100:.0f}% of composition)"
            )
            has_thinking_pause = True
        
        # Calculate typing split around pause
        typing_before_pause = base_typing_time * pause_position_ratio
        typing_after_pause = base_typing_time * (1 - pause_position_ratio)
        
        # Total time still includes all typing + pause
        total_time = typing_before_pause + thinking_pause + typing_after_pause
        
        # Ensure minimum time (humans don't type instantly)
        min_time = 5.0 if not message.is_correction else 2.0
        total_time = max(total_time, min_time)
        
        explanation = (
            f"Typing {word_count} words at ~{wpm:.0f} WPM "
            f"({base_typing_time:.1f}s base{pause_explanation})"
        )
        
        # Return detailed metrics for logging
        detailed_metrics = {
            "word_count": word_count,
            "wpm_range": (wpm_min, wpm_max),
            "actual_wpm": wpm,
            "base_typing_time": base_typing_time,
            "has_thinking_pause": has_thinking_pause,
            "thinking_pause_duration": thinking_pause if has_thinking_pause else 0.0,
            "pause_position_ratio": pause_position_ratio if has_thinking_pause else None,
            "typing_before_pause": typing_before_pause if has_thinking_pause else 0.0,
            "typing_after_pause": typing_after_pause if has_thinking_pause else 0.0,
            "total_typing_time": total_time
        }
        
        return total_time, explanation, detailed_metrics


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
