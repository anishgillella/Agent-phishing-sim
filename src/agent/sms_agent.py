"""
Part 2: Event-Driven AI Agent

Event-driven AI agent that packages the jitter algorithm as a tool.
Uses LangChain v1 with OpenRouter (GPT-4o-mini) and LangSmith telemetry.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import nullcontext
import uuid

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langsmith import Client as LangSmithClient
from pydantic import BaseModel
import logfire

# Import jitter algorithm
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from jitter import JitterAlgorithm, Message, ScheduledMessage
from utils.token_tracker import TokenTracker
from utils.callbacks import TokenTrackingCallback


class EventType(Enum):
    """Types of events in the jitter algorithm workflow."""
    MESSAGE_QUEUED = "message_queued"
    MESSAGE_SCHEDULED = "message_scheduled"
    TYPING_STARTED = "typing_started"
    MESSAGE_SENT = "message_sent"
    REPLY_RECEIVED = "reply_received"
    PATTERN_DETECTED = "pattern_detected"
    SCHEDULE_ADJUSTED = "schedule_adjusted"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """Represents an event in the system."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "context": self.context or {},
        }


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
                print(f"Error in event handler: {e}")
    
    def get_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self.event_history if e.event_type == event_type]
        return self.event_history


class TelemetryCollector:
    """
    Collects telemetry data for monitoring and evaluation.
    
    Three-tier telemetry system:
    1. Local metrics/traces (always available, no API key needed)
    2. LangSmith integration (optional, for LLM tracing and general telemetry)
    3. Logfire integration (optional, for Pydantic model validation and evaluation)
    
    Works without API keys - all telemetry stored locally.
    With API keys - also sends to cloud services for production observability.
    """
    
    def __init__(self, 
                 langsmith_api_key: Optional[str] = None,
                 logfire_api_key: Optional[str] = None):
        # Local metrics storage (no API key needed)
        self.metrics: Dict[str, Any] = {
            "messages_queued": 0,
            "messages_scheduled": 0,
            "messages_sent": 0,
            "replies_received": 0,
            "pattern_violations": 0,
            "schedule_adjustments": 0,
            "average_typing_time": 0.0,
            "average_inter_message_delay": 0.0,
            "total_typing_time": 0.0,
            "total_inter_message_delays": 0.0,
            "typing_time_count": 0,
            "delay_count": 0,
            "pydantic_validation_errors": 0,
            "pydantic_validation_successes": 0,
        }
        self.traces: List[Dict[str, Any]] = []
        self.langsmith_client = None
        self.logfire_configured = False
        
        # Token tracking (production-ready cost tracking)
        self.token_tracker = TokenTracker()
        
        # Optional: Initialize LangSmith if API key provided
        # For general telemetry and LLM tracing
        if langsmith_api_key:
            try:
                self.langsmith_client = LangSmithClient(api_key=langsmith_api_key)
            except Exception as e:
                print(f"Warning: Could not initialize LangSmith: {e}")
                print("Telemetry will continue with local storage only.")
        
        # Optional: Initialize Logfire if API key provided
        # For Pydantic model validation and structured output evaluation
        if logfire_api_key:
            try:
                logfire.configure(
                    token=logfire_api_key,
                    service_name="ghosteye-smishing-sim",
                    service_version="1.0.0",
                )
                self.logfire_configured = True
                print("✅ Logfire configured for Pydantic model validation")
            except Exception as e:
                print(f"Warning: Could not initialize Logfire: {e}")
                print("Pydantic validation will continue without Logfire.")
        else:
            # Try to configure from environment variable
            try:
                logfire.configure(
                    service_name="ghosteye-smishing-sim",
                    service_version="1.0.0",
                )
                self.logfire_configured = True
                print("✅ Logfire configured (using environment or default)")
            except Exception:
                # Logfire works without explicit configuration (local mode)
                pass
    
    def record_metric(self, metric_name: str, value: Any):
        """Record a metric."""
        self.metrics[metric_name] = value
    
    def increment_metric(self, metric_name: str, amount: int = 1):
        """Increment a metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += amount
    
    def record_typing_time(self, typing_time: float):
        """Record typing time for average calculation."""
        self.metrics["total_typing_time"] += typing_time
        self.metrics["typing_time_count"] += 1
        self.metrics["average_typing_time"] = (
            self.metrics["total_typing_time"] / self.metrics["typing_time_count"]
        )
    
    def record_delay(self, delay: float):
        """Record inter-message delay for average calculation."""
        self.metrics["total_inter_message_delays"] += delay
        self.metrics["delay_count"] += 1
        self.metrics["average_inter_message_delay"] = (
            self.metrics["total_inter_message_delays"] / self.metrics["delay_count"]
        )
    
    def add_trace(self, trace_data: Dict[str, Any]):
        """Add a trace entry."""
        trace_data["timestamp"] = datetime.now().isoformat()
        self.traces.append(trace_data)
        
        # Send to LangSmith if available (for general telemetry)
        # Note: LangSmith automatically traces LangChain calls via environment variables
        # Manual tracing here is optional and may conflict with automatic tracing
        # We'll rely on automatic LangSmith tracing instead
        pass
        
        # Send to Logfire if available (for detailed tracing)
        if self.logfire_configured:
            try:
                logfire.info(
                    trace_data.get("name", "trace"),
                    **trace_data
                )
            except Exception as e:
                print(f"Warning: Could not send trace to Logfire: {e}")
    
    def validate_pydantic_model(self, model_class: type[BaseModel], data: Dict[str, Any]) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate data against a Pydantic model using Logfire.
        
        Args:
            model_class: Pydantic model class
            data: Data to validate
        
        Returns:
            Tuple of (is_valid, validated_model_or_none, error_message_or_none)
        """
        try:
            # Validate with Pydantic
            validated = model_class(**data)
            
            # Log success to Logfire (automatic validation tracking)
            if self.logfire_configured:
                with logfire.span("pydantic_validation", model=model_class.__name__):
                    logfire.info(
                        "Pydantic validation successful",
                        model=model_class.__name__,
                        data=data,
                        validated=validated.model_dump(),
                    )
            
            self.increment_metric("pydantic_validation_successes")
            return True, validated, None
            
        except Exception as e:
            error_msg = str(e)
            
            # Log failure to Logfire (automatic validation tracking)
            if self.logfire_configured:
                with logfire.span("pydantic_validation_error", model=model_class.__name__):
                    logfire.error(
                        "Pydantic validation failed",
                        model=model_class.__name__,
                        data=data,
                        error=error_msg,
                    )
            
            self.increment_metric("pydantic_validation_errors")
            return False, None, error_msg
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics including token usage."""
        metrics = self.metrics.copy()
        # Add token usage summary
        token_summary = self.token_tracker.get_summary()
        metrics["token_usage"] = {
            "total_tokens": token_summary["total_tokens"],
            "total_cost_usd": token_summary["total_cost_usd"],
            "total_api_calls": token_summary["total_api_calls"],
        }
        return metrics
    
    def get_traces(self) -> List[Dict[str, Any]]:
        """Get all traces."""
        return self.traces.copy()


# Tool definitions using LangChain v1 @tool decorator
# Create tool functions (not methods) for LangChain v1
def create_jitter_tools(jitter_algorithm: JitterAlgorithm, event_bus: EventBus):
    """Create jitter algorithm tools for the agent."""
    
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
    
    return [schedule_message, schedule_batch, analyze_pattern]


class SMSAgent:
    """
    Event-driven AI agent that orchestrates SMS sending with human-realistic timing.
    
    Uses LangChain v1 create_agent with:
    - OpenRouter (GPT-4o-mini) for LLM
    - LangSmith for telemetry
    - Structured output with Pydantic
    - Event-driven architecture
    """
    
    def __init__(self,
                 openrouter_api_key: Optional[str] = None,
                 langsmith_api_key: Optional[str] = None,
                 langsmith_project: Optional[str] = None,
                 logfire_api_key: Optional[str] = None):
        """
        Initialize the SMS Agent.
        
        Args:
            openrouter_api_key: OpenRouter API key for LLM
            langsmith_api_key: LangSmith API key for telemetry (optional)
            langsmith_project: LangSmith project name (optional)
            logfire_api_key: Logfire API key for Pydantic validation (optional)
        """
        # Initialize components
        self.jitter_algorithm = JitterAlgorithm()
        self.event_bus = EventBus()
        
        # Get API keys from environment if not provided
        langsmith_key = langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
        logfire_key = logfire_api_key or os.getenv("LOGFIRE_API_KEY")
        
        self.telemetry = TelemetryCollector(
            langsmith_api_key=langsmith_key,
            logfire_api_key=logfire_key
        )
        
        # Get API keys from environment if not provided
        openrouter_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY environment variable.")
        
        # Set up LangSmith tracing (must be done before creating LLM)
        langsmith_key = langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
        if langsmith_key:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGSMITH_API_KEY"] = langsmith_key
            os.environ["LANGSMITH_PROJECT"] = langsmith_project or os.getenv("LANGSMITH_PROJECT", "ghosteye-smishing-sim")
        
        # Initialize token tracking callback for cost tracking
        model_name = "openai/gpt-4o-mini"
        self.token_callback = TokenTrackingCallback(
            token_tracker=self.telemetry.token_tracker,
            model=model_name
        )
        
        # Initialize LLM via OpenRouter
        # OpenRouter uses OpenAI-compatible API
        # Model format: "openai/gpt-4o-mini" for OpenRouter
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            callbacks=[self.token_callback],  # Add token tracking callback
        )
        
        # Logfire is already configured in TelemetryCollector if API key provided
        
        # Create jitter tools
        self.tools = create_jitter_tools(self.jitter_algorithm, self.event_bus)
        
        # Create agent with LangChain v1 create_agent
        # create_agent(model, tools, system_prompt) returns an agent runnable
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
        )
        
        # Agent memory (stores conversation history and context)
        self.memory: List[Dict[str, Any]] = []
        
        # Set up event handlers
        self._setup_event_handlers()
        
        print("✅ SMS Agent initialized with LangChain v1 create_agent")
        print(f"   Model: openai/gpt-4o-mini (via OpenRouter)")
        print(f"   Tools: {len(self.tools)} jitter algorithm tools")
        print(f"   Telemetry: LangSmith={bool(self.telemetry.langsmith_client)}, Logfire={self.telemetry.logfire_configured}")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are an AI agent managing SMS phishing simulation campaigns for GhostEye.

Your responsibilities:
1. Schedule SMS messages using the jitter algorithm tools to ensure human-realistic timing
2. Monitor events and adjust schedules when needed
3. Handle replies from recipients appropriately
4. Maintain awareness of timing patterns to avoid detection

Available tools:
- schedule_message: Schedule a single message with human-realistic timing
- schedule_batch: Schedule multiple messages at once
- analyze_pattern: Analyze detected patterns and provide recommendations

Key principles:
- Always use the jitter algorithm tools for scheduling (never schedule manually)
- Consider context when scheduling (time of day, recipient history, etc.)
- If a recipient replies, adjust future messages accordingly (respond within 30s-2min, then resume normal pacing)
- Maintain natural conversation flow
- Avoid patterns that look robotic
- When patterns are detected, analyze and adjust automatically

When scheduling messages:
- Use schedule_message for individual messages
- Use schedule_batch for multiple related messages
- Always explain your reasoning"""
    
    def _setup_event_handlers(self):
        """Set up event handlers for the event bus."""
        
        def handle_message_queued(event: Event):
            """Handle message queued event."""
            self.telemetry.increment_metric("messages_queued")
            self.telemetry.add_trace({
                "name": "message_queued",
                "run_type": "event",
                "inputs": event.data,
                "outputs": {},
            })
        
        def handle_message_scheduled(event: Event):
            """Handle message scheduled event."""
            self.telemetry.increment_metric("messages_scheduled")
            typing_duration = event.data.get("typing_duration", 0)
            self.telemetry.record_typing_time(typing_duration)
            self.telemetry.add_trace({
                "name": "message_scheduled",
                "run_type": "chain",
                "inputs": event.data,
                "outputs": {"status": "scheduled"},
            })
        
        def handle_reply_received(event: Event):
            """Handle reply received event."""
            self.telemetry.increment_metric("replies_received")
            # Agent should react to replies
            self._handle_reply(event.data)
        
        def handle_pattern_detected(event: Event):
            """Handle pattern detection event."""
            self.telemetry.increment_metric("pattern_violations")
            # Agent should analyze and adjust
            self._handle_pattern(event.data)
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.MESSAGE_QUEUED, handle_message_queued)
        self.event_bus.subscribe(EventType.MESSAGE_SCHEDULED, handle_message_scheduled)
        self.event_bus.subscribe(EventType.REPLY_RECEIVED, handle_reply_received)
        self.event_bus.subscribe(EventType.PATTERN_DETECTED, handle_pattern_detected)
    
    def _handle_reply(self, reply_data: Dict[str, Any]):
        """Handle a reply from a recipient."""
        # Store in memory
        self.memory.append({
            "type": "reply",
            "timestamp": datetime.now().isoformat(),
            "data": reply_data
        })
        
        # Agent can use this context in future decisions
        # In production, this would trigger agent to reschedule remaining messages
    
    def _handle_pattern(self, pattern_data: Dict[str, Any]):
        """Handle a detected pattern."""
        # Store in memory
        self.memory.append({
            "type": "pattern",
            "timestamp": datetime.now().isoformat(),
            "data": pattern_data
        })
        
        # Agent should analyze and adjust schedule
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process a user request using the AI agent.
        
        Args:
            user_request: User's request/instruction
        
        Returns:
            Response from the agent with validated outputs
        """
        # Instrument with Logfire for tracing
        context_manager = logfire.span("agent_process_request") if self.telemetry.logfire_configured else nullcontext()
        
        with context_manager:
            # Build input for LangChain v1 create_agent format
            # create_agent expects input as a dict with a "messages" key containing list of message dicts
            messages = []
            
            # Add memory context as system message if available
            if self.memory:
                memory_context = "\n".join([
                    f"- {m.get('type', 'unknown')}: {json.dumps(m.get('data', {}))}"
                    for m in self.memory[-5:]  # Last 5 memory entries
                ])
                messages.append(HumanMessage(content=f"Recent context:\n{memory_context}"))
            
            # Add user request as HumanMessage
            messages.append(HumanMessage(content=user_request))
            
            # Call agent (LangChain v1 create_agent uses invoke with messages list)
            try:
                result = self.agent.invoke({"messages": messages})
                
                # Extract response from result
                response_text = ""
                if isinstance(result, dict):
                    if "messages" in result and result["messages"]:
                        last_message = result["messages"][-1]
                        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    elif "output" in result:
                        response_text = result["output"]
                    else:
                        response_text = str(result)
                else:
                    response_text = str(result)
                
                # Validate structured outputs if present (using Logfire)
                validated_outputs = {}
                
                # Store in memory
                self.memory.append({
                    "type": "request",
                    "timestamp": datetime.now().isoformat(),
                    "request": user_request,
                    "response": response_text,
                    "validated_outputs": validated_outputs
                })
                
                return {
                    "response": result,
                    "response_text": response_text,
                    "validated_outputs": validated_outputs,
                    "metrics": self.telemetry.get_metrics(),
                    "traces": self.telemetry.get_traces()[-5:]  # Last 5 traces
                }
            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                print(f"❌ {error_msg}")
                self.telemetry.add_trace({
                    "name": "agent_error",
                    "error": str(e),
                    "request": user_request
                })
                return {
                    "error": error_msg,
                    "request": user_request,
                    "metrics": self.telemetry.get_metrics(),
                    "traces": self.telemetry.get_traces()[-5:]
                }
    
    def schedule_messages(self, messages: List[Dict[str, str]]) -> List[ScheduledMessage]:
        """
        Schedule messages using the jitter algorithm.
        This is a direct interface that bypasses the LLM for programmatic use.
        """
        message_objects = [
            Message(
                content=msg["content"],
                recipient=msg["recipient"],
                is_correction=msg.get("is_correction", False)
            )
            for msg in messages
        ]
        
        scheduled = self.jitter_algorithm.schedule_message_queue(message_objects)
        
        # Update telemetry
        self.telemetry.increment_metric("messages_scheduled", len(scheduled))
        
        return scheduled
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get telemetry data including token usage."""
        return {
            "metrics": self.telemetry.get_metrics(),
            "traces": self.telemetry.get_traces(),
            "events": [e.to_dict() for e in self.event_bus.get_history()],
            "token_usage": self.telemetry.token_tracker.get_summary(),
        }
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get detailed token usage and cost breakdown.
        
        Returns:
            Dictionary with token usage summary
        """
        return self.telemetry.token_tracker.get_summary()
    
    def get_token_cost(self) -> float:
        """
        Get total cost in USD for all LLM API calls.
        
        Returns:
            Total cost in USD
        """
        return self.telemetry.token_tracker.total_cost
    
    def export_token_usage(self, filepath: str):
        """
        Export token usage history to JSON file.
        
        Args:
            filepath: Path to save JSON file
        """
        self.telemetry.token_tracker.export_usage(filepath)


# Example usage
if __name__ == "__main__":
    # Initialize agent
    agent = SMSAgent()
    
    # Example: Schedule messages programmatically
    messages = [
        {"content": "Hey, can you check the report?", "recipient": "+1234567890"},
        {"content": "Thanks!", "recipient": "+1234567890"},
    ]
    
    scheduled = agent.schedule_messages(messages)
    
    print("Scheduled Messages:")
    for s in scheduled:
        print(f"  {s.scheduled_time}: {s.message.content}")
    
    print("\nTelemetry:")
    print(json.dumps(agent.get_telemetry()["metrics"], indent=2))

