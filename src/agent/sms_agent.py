"""
Part 2: Event-Driven AI Agent (Legacy - Backward Compatibility)

This file is maintained for backward compatibility.
All classes are re-exported from modular components.

New code should import from:
- from agent import SMSAgent, EventBus, Event, EventType, TelemetryCollector
- from agent.sms_agent_core import SMSAgent
- from agent.event_bus import EventBus
- from agent.telemetry import TelemetryCollector
- etc.
"""

# Re-export from modular components for backward compatibility
from .sms_agent_core import SMSAgent
from .event_bus import EventBus
from .models import Event, EventType
from .telemetry import TelemetryCollector
from .tools import create_jitter_tools
from .reply_handler import ReplyHandler

# Maintain backward compatibility
__all__ = [
    "SMSAgent",
    "EventBus",
    "Event",
    "EventType",
    "TelemetryCollector",
    "create_jitter_tools",
    "ReplyHandler",
]
