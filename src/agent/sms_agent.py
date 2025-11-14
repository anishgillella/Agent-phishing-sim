"""
Part 2: Event-Driven AI Agent (Backward Compatibility)

Re-exports from modular components for backward compatibility.
"""

from .sms_agent_core import SMSAgent
from .event_bus import EventBus
from .models import Event, EventType
from .telemetry import TelemetryCollector
from .tools import create_jitter_tools
from .reply_handler import ReplyHandler

__all__ = [
    "SMSAgent",
    "EventBus",
    "Event",
    "EventType",
    "TelemetryCollector",
    "create_jitter_tools",
    "ReplyHandler",
]
