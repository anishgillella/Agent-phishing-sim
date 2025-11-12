"""
SMS Agent Core

Main agent class that orchestrates SMS campaigns with human-realistic timing.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import nullcontext

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
import logfire

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jitter import JitterAlgorithm, Message, ScheduledMessage
from utils.callbacks import TokenTrackingCallback

from .event_bus import EventBus
from .telemetry import TelemetryCollector
from .tools import create_jitter_tools
from .reply_handler import ReplyHandler
from .models import Event, EventType

logger = logging.getLogger(__name__)


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
        
        # Create jitter tools (pass agent instance for reply handling)
        self.tools = create_jitter_tools(self.jitter_algorithm, self.event_bus, agent_instance=self)
        
        # Create agent with LangChain v1 create_agent
        # create_agent(model, tools, system_prompt) returns an agent runnable
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
        )
        
        # Agent memory (stores conversation history and context)
        self.memory: List[Dict[str, Any]] = []
        
        # Track scheduled messages per recipient for reply handling
        # Format: {recipient: [ScheduledMessage, ...]}
        self.scheduled_messages_by_recipient: Dict[str, List[ScheduledMessage]] = {}
        
        # Track paused messages (messages that were paused due to replies)
        # Format: {recipient: [ScheduledMessage, ...]}
        self.paused_messages: Dict[str, List[ScheduledMessage]] = {}
        
        # Track recipient engagement state (engaged = in active conversation)
        # Format: {recipient: {"engaged": bool, "last_reply_time": datetime, "last_message_index": int}}
        self.recipient_engagement: Dict[str, Dict[str, Any]] = {}
        
        # Initialize reply handler
        self.reply_handler = ReplyHandler(
            jitter_algorithm=self.jitter_algorithm,
            event_bus=self.event_bus,
            scheduled_messages_by_recipient=self.scheduled_messages_by_recipient,
            paused_messages=self.paused_messages,
            recipient_engagement=self.recipient_engagement
        )
        
        # Set up event handlers
        self._setup_event_handlers()
        
        logger.info("SMS Agent initialized with LangChain v1 create_agent")
        logger.info(f"Model: openai/gpt-4o-mini (via OpenRouter)")
        logger.info(f"Tools: {len(self.tools)} jitter algorithm tools")
        logger.info(f"Telemetry: LangSmith={bool(self.telemetry.langsmith_client)}, Logfire={self.telemetry.logfire_configured}")
    
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
- handle_reply: Handle a reply from a recipient (pauses remaining messages, sends immediate reply, reschedules)

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
            self.reply_handler.handle_reply(event.data, self.memory)
        
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
                import json
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
                logger.error(error_msg, exc_info=True)
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
    
    def schedule_messages(self, 
                         messages: List[Dict[str, str]],
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         enforce_time_window: bool = False,
                         max_messages_per_hour: Optional[int] = None,
                         distribution_mode: str = "clustered") -> List[ScheduledMessage]:
        """
        Schedule messages using the jitter algorithm.
        This is a direct interface that bypasses the LLM for programmatic use.
        
        Args:
            messages: List of message dictionaries
            start_time: When to start scheduling (defaults to now)
            end_time: Optional end time for time window (required if enforce_time_window=True)
            enforce_time_window: If True, ensure all messages fit within start_time to end_time window
            max_messages_per_hour: Maximum messages per hour for density control (optional)
            distribution_mode: "clustered" (default) or "even" - how to distribute messages
        
        Returns:
            List of ScheduledMessage objects
        """
        import uuid
        message_objects = []
        for msg in messages:
            # Generate message ID if not provided
            msg_id = msg.get("original_message_id") or str(uuid.uuid4())
            message_objects.append(
                Message(
                    content=msg["content"],
                    recipient=msg["recipient"],
                    is_correction=msg.get("is_correction", False),
                    original_message_id=msg_id  # Track original message ID
                )
            )
        
        scheduled = self.jitter_algorithm.schedule_message_queue(
            message_objects,
            start_time=start_time,
            end_time=end_time,
            enforce_time_window=enforce_time_window,
            max_messages_per_hour=max_messages_per_hour,
            distribution_mode=distribution_mode
        )
        
        # Track scheduled messages per recipient for reply handling
        for scheduled_msg in scheduled:
            recipient = scheduled_msg.message.recipient
            if recipient not in self.scheduled_messages_by_recipient:
                self.scheduled_messages_by_recipient[recipient] = []
            self.scheduled_messages_by_recipient[recipient].append(scheduled_msg)
        
        # Update telemetry
        self.telemetry.increment_metric("messages_scheduled", len(scheduled))
        
        return scheduled
    
    def receive_reply(self, recipient: str, reply_content: str, original_message_id: Optional[str] = None):
        """
        Public method to simulate receiving a reply from a recipient.
        This would be called by SMS webhook handler in production.
        
        Args:
            recipient: Phone number of recipient
            reply_content: Content of the reply
            original_message_id: ID of the original message being replied to
        """
        import uuid
        # Publish REPLY_RECEIVED event
        self.event_bus.publish(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.REPLY_RECEIVED,
            timestamp=datetime.now(),
            data={
                "recipient": recipient,
                "reply_content": reply_content,
                "original_message_id": original_message_id
            }
        ))
        
        # Event handler will automatically call reply_handler.handle_reply
    
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

