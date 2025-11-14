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
                 logfire_api_key: Optional[str] = None,
                 enable_llm_event_handling: bool = True):
        """
        Initialize the SMS Agent.
        
        Args:
            openrouter_api_key: OpenRouter API key for LLM
            langsmith_api_key: LangSmith API key for telemetry (optional)
            langsmith_project: LangSmith project name (optional)
            logfire_api_key: Logfire API key for Pydantic validation (optional)
            enable_llm_event_handling: If True, LLM agent makes decisions on events (default: True)
        """
        # Initialize components
        self.event_bus = EventBus()
        # Pass event_bus to jitter algorithm so it can fire events during execution
        self.jitter_algorithm = JitterAlgorithm(event_bus=self.event_bus)
        
        # Get API keys from environment if not provided
        langsmith_key = langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
        logfire_key = logfire_api_key or os.getenv("LOGFIRE_API_KEY")
        
        # Enable LLM-driven event handling (can be disabled for direct mode)
        self.enable_llm_event_handling = enable_llm_event_handling
        
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
        
        # Circuit breaker: Track API failures to prevent cascading failures
        self._api_failure_count = 0
        self._api_circuit_open = False
        self._processing_request = False  # Prevent recursive calls
        self._batch_mode = False  # Track if we're in batch scheduling mode
        
        # Queue for events that occur during batch operations (to be processed agent-driven after batch)
        self._deferred_events: List[Event] = []
        
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

CRITICAL MISSION: Design timing patterns that are UNDETECTABLE as phishing. Messages must appear to come from a real human, not a bot.

Your responsibilities:
1. Schedule SMS messages using the jitter algorithm tools to ensure human-realistic timing that avoids detection
2. Reason about anti-detection strategies (what makes timing undetectable?)
3. Monitor events and adjust schedules when needed
4. Handle replies from recipients appropriately
5. Maintain awareness of timing patterns to avoid detection

Available tools:
       - generate_messages: Generate messages for a scenario (decide what messages to send based on requirements)
- schedule_message: Schedule a single message with human-realistic timing
       - schedule_batch: Schedule multiple messages at once (supports time windows, distribution modes, density control)
- analyze_pattern: Analyze detected patterns and provide recommendations
- handle_reply: Handle a reply from a recipient (pauses remaining messages, sends immediate reply, reschedules)

Key principles for UNDETECTABLE timing:
- Always use the jitter algorithm tools for scheduling (never schedule manually)
- Reason about what makes patterns undetectable:
  * Clustered bursts (humans send messages in bursts, not uniformly)
  * Natural variation (delays vary, not fixed intervals)
  * Time-of-day patterns (more activity during work hours)
  * Thinking pauses (humans pause while composing)
  * Hour boundaries (messages cluster around :00, :15, :30, :45)
- Consider context when scheduling (time of day, recipient history, message complexity)
- If a recipient replies, adjust future messages accordingly (respond within 30s-2min, then resume normal pacing)
- Maintain natural conversation flow
- Avoid robotic patterns (uniform intervals, perfect timing, no variation)
- When patterns are detected, analyze why they're detectable and adjust automatically

       When scheduling messages:
       - CRITICAL: This is SMISHING (SMS phishing) simulation - messages MUST be smishing-appropriate
       - Messages must be SMISHING messages: security alerts, verification requests, account issues, urgent actions
       - DO NOT use casual messages like "Got it", "Perfect", "On it" - these are NOT smishing messages
       - Messages must form COHERENT SMISHING CAMPAIGN SEQUENCES, not random standalone messages
       - Design message sequences that form logical smishing campaign flows
       - Each message should make sense given previous messages (e.g., security alert → urgency → verification request)
       - CRITICAL: Use conversation history context provided to you - but NOT every message needs to be a follow-up
       - Mix follow-up messages with new campaign messages for natural variety
       - If a recipient already received messages, SOME messages can be follow-ups (30-40%), but also send NEW campaign messages
       - Example: Send 2-3 follow-ups, then start a new campaign thread, then more follow-ups, etc.
       - This creates realistic variety: not every message is a follow-up, but some build on previous messages
       - CRITICAL: Messages must look NATURAL and CASUAL like real SMS messages
       - Avoid excessive symbols, emojis, or formatting that looks suspicious or alarming
       - Use natural SMS formatting: simple text, minimal punctuation, casual tone
       - Avoid: excessive exclamation marks (!!!), all caps (URGENT!!!), suspicious formatting, emojis
       - Keep messages looking like they come from a real person, not a bot
       - Think: "What sequence would a real SMISHING campaign use?"
       - Use generate_messages tool to create SMISHING messages, ensuring they form coherent campaign sequences
       - When calling generate_messages, provide previous_messages_context parameter with conversation history
       - Use schedule_message for individual messages
       - Use schedule_batch for multiple related messages - MUST actually call the tool, don't just describe
       - MUST schedule the FULL number of messages requested (e.g., if asked for 50 messages, schedule all 50)
       - Reason about distribution strategy (clustered vs even) based on anti-detection goals
       - Calculate realistic messages/hour rates (consider total messages / time window)
       - Always explain your reasoning for smishing message sequence design and anti-detection strategy
       - Never hardcode messages - always use generate_messages tool or decide message content yourself
       - Never send random or casual messages - always design coherent SMISHING campaign sequences"""
    
    def _setup_event_handlers(self):
        """Set up event handlers for the event bus."""
        
        def handle_message_queued(event: Event):
            """Handle message queued event - agent analyzes complexity."""
            self.telemetry.increment_metric("messages_queued")
            self.telemetry.add_trace({
                "name": "message_queued",
                "run_type": "event",
                "inputs": event.data,
                "outputs": {},
            })
            
            # Agent analyzes message complexity
            if self.enable_llm_event_handling and not self._api_circuit_open:
                self._agent_analyze_complexity(event)
        
        def handle_typing_started(event: Event):
            """Handle typing started event - agent analyzes typing metrics."""
            typing_duration = event.data.get("typing_duration", 0)
            typing_explanation = event.data.get("typing_explanation", "")
            self.telemetry.record_typing_time(typing_duration)
            self.telemetry.add_trace({
                "name": "typing_started",
                "run_type": "event",
                "inputs": event.data,
                "outputs": {"typing_duration": typing_duration},
            })
            
            # Agent analyzes typing metrics
            if self.enable_llm_event_handling and not self._api_circuit_open:
                self._agent_analyze_typing(event)
        
        def handle_message_scheduled(event: Event):
            """Handle message scheduled event - agent analyzes every message."""
            self.telemetry.increment_metric("messages_scheduled")
            typing_duration = event.data.get("typing_duration", 0)
            self.telemetry.record_typing_time(typing_duration)
            self.telemetry.add_trace({
                "name": "message_scheduled",
                "run_type": "chain",
                "inputs": event.data,
                "outputs": {"status": "scheduled"},
            })
            
            # Agent MUST analyze jitter metrics for EVERY scheduled message
            # This is critical for displaying agent reasoning in output
            # Use lightweight analysis (no LLM calls) - just categorize and reason
            if self.enable_llm_event_handling and not self._api_circuit_open:
                # Always analyze, even during batch (lightweight operation)
                self._agent_analyze_scheduled_metrics(event)
        
        def handle_reply_received(event: Event):
            """Handle reply received event - LLM agent makes decisions."""
            self.telemetry.increment_metric("replies_received")
            
            # CRITICAL: Check circuit breaker before LLM calls to prevent infinite loops
            if self.enable_llm_event_handling and not self._api_circuit_open:
                # LLM agent analyzes reply and decides on action
                self._agent_handle_reply(event)
            else:
                # Direct mode: use hardcoded logic (fallback when circuit breaker is open)
                self.reply_handler.handle_reply(event.data, self.memory)
        
        def handle_pattern_detected(event: Event):
            """Handle pattern detection event - LLM agent analyzes and adjusts."""
            self.telemetry.increment_metric("pattern_violations")
            
            # If we're in batch mode, defer the event to be processed agent-driven after batch completes
            if self._batch_mode:
                self._deferred_events.append(event)
                logger.info(f"Pattern detected during batch - deferred for agent-driven processing (queue size: {len(self._deferred_events)})")
                return
            
            # CRITICAL: Check circuit breaker before LLM calls to prevent infinite loops
            if self.enable_llm_event_handling and not self._api_circuit_open:
                # LLM agent analyzes pattern and decides on adjustments
                self._agent_handle_pattern(event)
            else:
                # Direct mode: just store pattern (fallback when circuit breaker is open)
                self._handle_pattern(event.data)
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.MESSAGE_QUEUED, handle_message_queued)
        self.event_bus.subscribe(EventType.TYPING_STARTED, handle_typing_started)
        self.event_bus.subscribe(EventType.MESSAGE_SCHEDULED, handle_message_scheduled)
        self.event_bus.subscribe(EventType.REPLY_RECEIVED, handle_reply_received)
        self.event_bus.subscribe(EventType.PATTERN_DETECTED, handle_pattern_detected)
    
    def _handle_pattern(self, pattern_data: Dict[str, Any]):
        """Handle a detected pattern (direct mode - no LLM)."""
        # Store in memory
        self.memory.append({
            "type": "pattern",
            "timestamp": datetime.now().isoformat(),
            "data": pattern_data
        })
        
    def _agent_handle_reply(self, event: Event):
        """
        LLM agent handles reply received event.
        Agent analyzes the reply and decides on appropriate response strategy.
        CRITICAL: Always calls reply_handler.handle_reply() to execute the workflow.
        """
        # CRITICAL: Check circuit breaker FIRST - prevent infinite loops
        if self._api_circuit_open or not self.enable_llm_event_handling:
            logger.warning("Circuit breaker open or LLM disabled - using direct handler for reply")
            self.reply_handler.handle_reply(event.data, self.memory)
            return
        
        reply_data = event.data
        recipient = reply_data.get("recipient")
        reply_content = reply_data.get("reply_content", "")
        
        # Build context for LLM agent
        context = {
            "event_type": "REPLY_RECEIVED",
            "recipient": recipient,
            "reply_content": reply_content,
            "scheduled_messages_count": len(self.scheduled_messages_by_recipient.get(recipient, [])),
            "paused_messages_count": len(self.paused_messages.get(recipient, [])),
            "is_engaged": self.recipient_engagement.get(recipient, {}).get("engaged", False),
        }
        
        # Create prompt for agent decision
        prompt = f"""A recipient ({recipient}) just replied to one of our SMS messages.

Reply content: "{reply_content}"

Current state:
- Scheduled messages for this recipient: {context['scheduled_messages_count']}
- Paused messages: {context['paused_messages_count']}
- Currently engaged: {context['is_engaged']}

You need to decide how to handle this reply. Use the handle_reply tool to:
1. Pause remaining messages for this recipient
2. Send an immediate response (within 30-120 seconds)
3. Reschedule remaining messages with appropriate delays

Consider:
- The tone and content of the reply
- Whether this is a positive response, question, or rejection
- How to maintain natural conversation flow
- Timing adjustments needed for remaining messages

Use the handle_reply tool with appropriate parameters."""
        
        try:
            # Agent makes decision using LLM
            result = self.process_request(prompt)
            
            # Check if result contains error (circuit breaker might have opened)
            if result.get("error") or result.get("api_circuit_open"):
                logger.warning("API call failed in reply handler - falling back to direct handler")
                self.reply_handler.handle_reply(reply_data, self.memory)
                return
            
            # CRITICAL: ALWAYS execute the reply workflow via reply_handler
            # This ensures messages are paused, reply sent, and messages rescheduled
            # The agent decision is stored, but the actual workflow execution is essential
            self.reply_handler.handle_reply(reply_data, self.memory)
            
            # Store agent decision in memory
            self.memory.append({
                "type": "agent_reply_decision",
                "timestamp": datetime.now().isoformat(),
                "event_id": event.event_id,
                "context": context,
                "agent_response": result.get("response_text", ""),
                "decision_made": True,
                "workflow_executed": "reply_handler called and completed"
            })
            
            logger.info(f"Agent processed reply from {recipient} and executed reply workflow: {result.get('response_text', '')[:100]}")
            
        except Exception as e:
            logger.error(f"Agent failed to handle reply, falling back to direct handler: {e}")
            # Fallback to direct handler
            self.reply_handler.handle_reply(reply_data, self.memory)
    
    def _agent_handle_pattern(self, event: Event):
        """
        LLM agent handles pattern detection event.
        Agent analyzes the pattern and decides on schedule adjustments.
        """
        # CRITICAL: Check circuit breaker FIRST - prevent infinite loops
        if self._api_circuit_open or not self.enable_llm_event_handling:
            logger.warning("Circuit breaker open or LLM disabled - using direct handler for pattern")
            self._handle_pattern(event.data)
            return
        
        # If we're already processing a request, defer this event for agent-driven processing later
        if self._processing_request:
            logger.info("Deferring pattern event - request already in progress (will process agent-driven after)")
            self._deferred_events.append(event)
            return
        
        pattern_data = event.data
        
        # Build context for LLM agent
        recent_schedules = []
        if self.scheduled_messages_by_recipient:
            for recipient, messages in list(self.scheduled_messages_by_recipient.items())[:3]:
                if messages:
                    recent_schedules.append({
                        "recipient": recipient,
                        "count": len(messages),
                        "last_time": messages[-1].scheduled_time.isoformat() if messages else None
                    })
        
        context = {
            "event_type": "PATTERN_DETECTED",
            "pattern_data": pattern_data,
            "recent_schedules": recent_schedules,
            "total_scheduled": sum(len(msgs) for msgs in self.scheduled_messages_by_recipient.values()),
        }
        
        # Create prompt for agent decision
        prompt = f"""A timing pattern violation was detected in our SMS scheduling.

Pattern details: {pattern_data}

Current scheduling state:
- Total scheduled messages: {context['total_scheduled']}
- Recent schedules: {recent_schedules}

This pattern could make our messages look robotic and get flagged as spam.

You need to analyze this pattern and decide on adjustments. Use the analyze_pattern tool to:
1. Understand what pattern was detected
2. Determine why it's problematic
3. Recommend schedule adjustments

Then, if needed, you can use schedule_batch to reschedule messages with better timing.

Analyze the pattern and provide recommendations."""
        
        try:
            # Agent makes decision using LLM
            result = self.process_request(prompt)
            
            # Check if result contains error (circuit breaker might have opened)
            if result.get("error") or result.get("api_circuit_open"):
                logger.warning("API call failed in pattern handler - falling back to direct handler")
                self._handle_pattern(pattern_data)
                return
            
            # Store agent decision in memory
            self.memory.append({
                "type": "agent_pattern_decision",
                "timestamp": datetime.now().isoformat(),
                "event_id": event.event_id,
                "pattern_data": pattern_data,
                "agent_response": result.get("response_text", ""),
                "decision_made": True
            })
            
            logger.info(f"Agent analyzed pattern: {result.get('response_text', '')[:100]}")
            
            # Agent could also proactively adjust schedule here
            # For now, we store the decision and let manual rescheduling happen
            
        except Exception as e:
            logger.error(f"Agent failed to handle pattern, falling back to direct handler: {e}")
            # Fallback to direct handler
            self._handle_pattern(pattern_data)
    
    def _agent_analyze_complexity(self, event: Event):
        """
        Agent analyzes message complexity determined by jitter algorithm.
        Logs analysis of complexity factors.
        """
        if self._api_circuit_open or not self.enable_llm_event_handling:
            return
        
        event_data = event.data
        message_content = event_data.get("message_content", "")
        complexity = event_data.get("complexity", "unknown")
        recipient = event_data.get("recipient", "")
        
        # Analyze complexity
        word_count = len(message_content.split()) if message_content else 0
        
        analysis = f"""🤖 Agent Analysis - Message Complexity:
   Message: "{message_content[:50]}{'...' if len(message_content) > 50 else ''}"
   Word Count: {word_count} words
   Complexity Level: {complexity.upper()}
   Analysis: """
        
        if complexity == "simple":
            analysis += f"Short message ({word_count} words) - SIMPLE complexity. Fast typing expected (35-50 WPM)."
        elif complexity == "medium":
            analysis += f"Standard message ({word_count} words) - MEDIUM complexity. Moderate typing speed (30-45 WPM)."
        elif complexity == "complex":
            analysis += f"Long message ({word_count} words) - COMPLEX complexity. Slower typing expected (25-40 WPM)."
        elif complexity == "correction":
            analysis += f"Follow-up/correction message - CORRECTION complexity. Fast typing expected (40-60 WPM)."
        else:
            analysis += f"Complexity determined: {complexity}"
        
        logger.info(analysis)
        
        # Store in memory
        self.memory.append({
            "type": "complexity_analysis",
            "timestamp": event.timestamp.isoformat(),
            "complexity": complexity,
            "word_count": word_count,
            "analysis": analysis
        })
    
    def _agent_analyze_typing(self, event: Event):
        """
        Agent analyzes typing metrics from jitter algorithm.
        Logs analysis of typing speed, duration, and factors.
        """
        if self._api_circuit_open or not self.enable_llm_event_handling:
            return
        
        event_data = event.data
        typing_duration = event_data.get("typing_duration", 0)
        typing_explanation = event_data.get("typing_explanation", "")
        message_content = event_data.get("message_content", "")
        recipient = event_data.get("recipient", "")
        
        # Parse typing explanation to extract metrics
        word_count = len(message_content.split()) if message_content else 0
        
        analysis = f"""🤖 Agent Analysis - Typing Metrics:
   Message: "{message_content[:50]}{'...' if len(message_content) > 50 else ''}"
   Typing Duration: {typing_duration:.2f} seconds
   Typing Explanation: {typing_explanation}
   Analysis: """
        
        # Extract WPM from explanation if available
        if "WPM" in typing_explanation:
            # Try to extract WPM value
            import re
            wpm_match = re.search(r'~(\d+) WPM', typing_explanation)
            if wpm_match:
                wpm = int(wpm_match.group(1))
                analysis += f"Typing speed: ~{wpm} WPM. "
                
                if wpm >= 50:
                    analysis += "Fast typist - likely simple message or experienced user."
                elif wpm >= 35:
                    analysis += "Average typing speed - natural human pace."
                elif wpm >= 25:
                    analysis += "Slower typing - complex message or careful composition."
                else:
                    analysis += "Very slow typing - may indicate complexity or distraction."
        
        if "thinking pause" in typing_explanation.lower():
            analysis += " Includes thinking pause - realistic human behavior (pausing to think while composing)."
        
        if typing_duration < 5:
            analysis += " Quick response - likely short message or correction."
        elif typing_duration < 15:
            analysis += " Normal typing duration - standard message composition."
        elif typing_duration < 30:
            analysis += " Longer typing duration - complex message or careful composition."
        else:
            analysis += " Extended typing duration - very complex message or multiple pauses."
        
        logger.info(analysis)
        
        # Store in memory
        self.memory.append({
            "type": "typing_analysis",
            "timestamp": event.timestamp.isoformat(),
            "typing_duration": typing_duration,
            "typing_explanation": typing_explanation,
            "analysis": analysis
        })
    
    def _agent_analyze_scheduled_metrics(self, event: Event):
        """
        Agent analyzes jitter metrics for a scheduled message.
        Determines campaign phase and stores reasoning (LLM-driven analysis).
        """
        scheduled_data = event.data
        scheduled_time = scheduled_data.get("scheduled_time")
        explanation = scheduled_data.get("explanation", "")
        typing_duration = scheduled_data.get("typing_duration", 0)
        recipient = scheduled_data.get("recipient", "")
        message_content = scheduled_data.get("message_content", "").lower() if scheduled_data.get("message_content") else ""
        
        # Extract jitter metrics from explanation
        import re
        complexity_match = re.search(r'Complexity:\s*(\w+)', explanation) if explanation else None
        delay_match = re.search(r'Delay:\s*([\d.]+)\s*(min|sec)', explanation) if explanation else None
        wpm_match = re.search(r'~(\d+) WPM', explanation) if explanation else None
        
        # Build comprehensive analysis
        analysis = f"""🤖 Agent Analysis - Jitter Metrics for Scheduled Message:
   Scheduled Time: {scheduled_time}
   Recipient: {recipient}
   Typing Duration: {typing_duration:.2f} seconds"""
        
        if complexity_match:
            complexity = complexity_match.group(1)
            analysis += f"\n   Complexity: {complexity.upper()}"
            if complexity.lower() == "simple":
                analysis += " - Short message, fast typing expected (35-50 WPM)"
            elif complexity.lower() == "medium":
                analysis += " - Standard message, moderate typing (30-45 WPM)"
            elif complexity.lower() == "complex":
                analysis += " - Long message, slower typing (25-40 WPM)"
            elif complexity.lower() == "correction":
                analysis += " - Follow-up/correction, fast typing (40-60 WPM)"
        
        if wpm_match:
            wpm = int(wpm_match.group(1))
            analysis += f"\n   Typing Speed: ~{wpm} WPM"
            if wpm >= 50:
                analysis += " (Fast typist)"
            elif wpm >= 35:
                analysis += " (Average speed)"
            elif wpm >= 25:
                analysis += " (Slower, complex message)"
            else:
                analysis += " (Very slow, may include pauses)"
        
        if delay_match:
            delay_val = delay_match.group(1)
            delay_unit = delay_match.group(2)
            analysis += f"\n   Inter-message Delay: {delay_val} {delay_unit}"
            if delay_unit == "min":
                delay_sec = float(delay_val) * 60
            else:
                delay_sec = float(delay_val)
            
            if delay_sec < 60:
                analysis += " (Quick follow-up)"
            elif delay_sec < 300:
                analysis += " (Normal interval)"
            elif delay_sec < 600:
                analysis += " (Extended delay)"
            else:
                analysis += " (Long delay, natural break)"
        
        if "thinking pause" in explanation.lower():
            analysis += "\n   Thinking Pause: Included (realistic human behavior)"
        
        analysis += f"\n   Full Explanation: {explanation}"
        
        logger.info(analysis)
        
        # Determine campaign phase from message content (Agent's semantic analysis)
        campaign_phase = "Unknown Phase"
        if message_content:
            if any(word in message_content for word in ["alert", "detected", "unusual", "suspicious"]):
                campaign_phase = "Initial Alert Phase"
            elif any(word in message_content for word in ["urgent", "immediate", "24 hours", "12 hours"]):
                campaign_phase = "Urgency Building Phase"
            elif any(word in message_content for word in ["verify", "verification", "identity"]):
                campaign_phase = "Verification Request Phase"
            elif any(word in message_content for word in ["locked", "suspended", "restricted", "final"]):
                campaign_phase = "Deadline Pressure Phase"
            else:
                campaign_phase = "Follow-up Phase"
        
        # Generate agent reasoning for this specific message's timing
        agent_reasoning = ""
        if "Inter-message delay:" in explanation:
            delay_info = explanation.split("Inter-message delay:")[1].split("(adjusted")[0].strip() if "(adjusted" in explanation else ""
            
            if "clustered: True" in explanation:
                agent_reasoning = f"Strategic clustering. Delay {delay_info} creates natural message burst during engagement peak."
            elif "pattern avoidance applied" in explanation:
                agent_reasoning = f"Pattern avoidance active. Delay {delay_info} breaks robotic uniform intervals for anti-detection."
            else:
                agent_reasoning = f"Natural inter-message spacing. Delay {delay_info} maintains realistic pacing."
        else:
            agent_reasoning = "Initial message with realistic startup delay."
        
        # Store in memory
        self.memory.append({
            "type": "jitter_metrics_analysis",
            "timestamp": datetime.now().isoformat(),
            "scheduled_time": scheduled_time,
            "typing_duration": typing_duration,
            "complexity": complexity_match.group(1) if complexity_match else None,
            "wpm": int(wpm_match.group(1)) if wpm_match else None,
            "delay": delay_match.group(1) + ' ' + delay_match.group(2) if delay_match else None,
            "explanation": explanation,
            "analysis": analysis
        })
        
        # Store campaign phase analysis separately for display
        self.memory.append({
            "type": "message_campaign_phase",
            "timestamp": datetime.now().isoformat(),
            "scheduled_time": scheduled_time,
            "recipient": recipient,
            "campaign_phase": campaign_phase,
            "agent_reasoning": agent_reasoning,
            "message_preview": message_content[:60] if message_content else "N/A"
        })
    
    def _agent_review_schedule(self, event: Event):
        """
        LLM agent reviews scheduled message and analyzes all jitter metrics.
        Called periodically to ensure scheduling quality.
        """
        # CRITICAL: Check circuit breaker FIRST - prevent infinite loops
        if self._api_circuit_open or not self.enable_llm_event_handling:
            logger.debug("Circuit breaker open or LLM disabled - skipping schedule review")
            return  # Just skip review, scheduling already happened
        
        scheduled_data = event.data
        scheduled_time = scheduled_data.get("scheduled_time")
        explanation = scheduled_data.get("explanation", "")
        typing_duration = scheduled_data.get("typing_duration", 0)
        recipient = scheduled_data.get("recipient", "")
        
        # Extract jitter metrics from explanation
        complexity_match = None
        delay_match = None
        if explanation:
            import re
            complexity_match = re.search(r'Complexity:\s*(\w+)', explanation)
            delay_match = re.search(r'Delay:\s*([\d.]+)\s*(min|sec)', explanation)
        
        # Get recent scheduling history
        recent_times = []
        for r, messages in list(self.scheduled_messages_by_recipient.items())[:5]:
            if messages:
                recent_times.extend([msg.scheduled_time.isoformat() for msg in messages[-3:]])
        
        # Build comprehensive analysis prompt
        prompt = f"""A message was just scheduled using the jitter algorithm. Analyze all the jitter metrics:

Scheduled Time: {scheduled_time}
Typing Duration: {typing_duration:.2f} seconds
Explanation: {explanation}

Jitter Algorithm Metrics:
- Message Complexity: {complexity_match.group(1) if complexity_match else "Not specified"}
- Inter-message Delay: {delay_match.group(1) + ' ' + delay_match.group(2) if delay_match else "Calculated by jitter"}
- Typing Time: {typing_duration:.2f}s (calculated from complexity and word count)

Recent scheduling history:
{recent_times[-10:] if recent_times else "No previous schedules"}

Analyze these jitter metrics:
1. Message Complexity: Is the complexity level appropriate for the message content?
2. Typing Speed: Does the typing duration match the complexity and word count?
3. Inter-message Delay: Is the delay between messages natural and human-like?
4. Overall Timing: Does the scheduled time look realistic considering all factors?

Provide a brief analysis of how well the jitter algorithm calculated these metrics."""
        
        try:
            result = self.process_request(prompt)
            
            # Extract analysis from result
            analysis_text = result.get("response_text", "")
            
            # Log comprehensive analysis
            logger.info(f"""🤖 Agent Analysis - Jitter Metrics Review:
   Scheduled Time: {scheduled_time}
   Typing Duration: {typing_duration:.2f}s
   Complexity: {complexity_match.group(1) if complexity_match else "N/A"}
   Delay: {delay_match.group(1) + ' ' + delay_match.group(2) if delay_match else "N/A"}
   Agent Analysis: {analysis_text[:200]}{'...' if len(analysis_text) > 200 else ''}""")
            
            # Store in memory
            self.memory.append({
                "type": "jitter_metrics_review",
                "timestamp": datetime.now().isoformat(),
                "scheduled_time": scheduled_time,
                "typing_duration": typing_duration,
                "explanation": explanation,
                "agent_analysis": analysis_text
            })
            
            # Check if result contains error (circuit breaker might have opened)
            if result.get("error") or result.get("api_circuit_open"):
                logger.debug("API call failed in schedule review - skipping (non-critical)")
                return  # Non-critical, just skip
            
            # Store review in memory
            self.memory.append({
                "type": "agent_schedule_review",
                "timestamp": datetime.now().isoformat(),
                "event_id": event.event_id,
                "scheduled_time": scheduled_time,
                "agent_response": result.get("response_text", ""),
            })
            
            logger.debug(f"Agent reviewed schedule: {result.get('response_text', '')[:100]}")
            
        except Exception as e:
            logger.debug(f"Agent schedule review failed (non-critical): {e}")
            # Non-critical, don't fallback
    
    def get_conversation_history(self, recipient: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get conversation history for recipients.
        
        Args:
            recipient: Optional recipient to filter by. If None, returns all recipients.
        
        Returns:
            Dictionary mapping recipient -> list of previous messages with content and scheduled_time
        """
        history = {}
        
        for rec, scheduled_list in self.scheduled_messages_by_recipient.items():
            if recipient and rec != recipient:
                continue
            
            history[rec] = []
            for scheduled_msg in scheduled_list:
                history[rec].append({
                    "content": scheduled_msg.message.content,
                    "scheduled_time": scheduled_msg.scheduled_time.isoformat(),
                    "message_id": scheduled_msg.message.original_message_id
                })
        
        return history
    
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
            
            # Add conversation history context
            conversation_history = self.get_conversation_history()
            if conversation_history:
                import json
                history_context = "CONVERSATION HISTORY (Previous messages sent to recipients):\n"
                for rec, msg_list in conversation_history.items():
                    history_context += f"\nRecipient {rec} ({len(msg_list)} previous messages):\n"
                    for i, msg in enumerate(msg_list[-5:], 1):  # Last 5 messages per recipient
                        history_context += f"  {i}. [{msg['scheduled_time']}] {msg['content'][:100]}...\n"
                
                messages.append(HumanMessage(content=history_context))
            
            # Add memory context as system message if available
            if self.memory:
                import json
                memory_context = "\n".join([
                    f"- {m.get('type', 'unknown')}: {json.dumps(m.get('data', {}))}"
                    for m in self.memory[-5:]  # Last 5 memory entries
                ])
                messages.append(HumanMessage(content=f"Recent agent memory:\n{memory_context}"))
            
            # Add user request as HumanMessage
            messages.append(HumanMessage(content=user_request))
            
            # Check circuit breaker - if API is failing, don't make more calls
            if self._api_circuit_open:
                error_msg = "API circuit breaker is open - too many failures. Refill credits or check API key."
                logger.error(error_msg)
                return {
                    "error": error_msg,
                    "request": user_request,
                    "metrics": self.telemetry.get_metrics(),
                    "traces": self.telemetry.get_traces()[-5:]
                }
            
            # Prevent recursive calls
            if self._processing_request:
                error_msg = "Already processing a request - preventing recursive call"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "request": user_request,
                    "metrics": self.telemetry.get_metrics(),
                    "traces": self.telemetry.get_traces()[-5:]
                }
            
            self._processing_request = True
            
            # Call agent (LangChain v1 create_agent uses invoke with messages list)
            try:
                result = self.agent.invoke({"messages": messages})
                
                # Reset failure count on success
                self._api_failure_count = 0
                self._api_circuit_open = False
                
                # Check if tools were called by examining the result
                tool_calls_made = []
                if isinstance(result, dict):
                    if "messages" in result and result["messages"]:
                        # Check all messages for tool calls
                        for msg in result["messages"]:
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_calls_made.extend(msg.tool_calls)
                            elif hasattr(msg, 'tool_call_id'):
                                tool_calls_made.append(msg.tool_call_id)
                
                if tool_calls_made:
                    logger.info(f"Agent made {len(tool_calls_made)} tool call(s)")
                    self.telemetry.add_trace({
                        "name": "agent_tool_calls",
                        "tool_calls": len(tool_calls_made),
                        "request": user_request[:100]
                    })
                else:
                    logger.warning("Agent did not call any tools - may have responded with text only")
                
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
                
                # Check if it's an API credit/authentication error
                error_str = str(e).lower()
                if "402" in error_str or "insufficient credits" in error_str or "401" in error_str:
                    self._api_failure_count += 1
                    # Open circuit breaker after 3 consecutive failures
                    if self._api_failure_count >= 3:
                        self._api_circuit_open = True
                        logger.error(f"API circuit breaker OPENED after {self._api_failure_count} failures. "
                                   f"Disabling LLM event handling to prevent cascading failures.")
                        # Disable LLM event handling to prevent more API calls
                        self.enable_llm_event_handling = False
                
                self.telemetry.add_trace({
                    "name": "agent_error",
                    "error": str(e),
                    "request": user_request,
                    "api_failure_count": self._api_failure_count,
                    "circuit_open": self._api_circuit_open
                })
                return {
                    "error": error_msg,
                    "request": user_request,
                    "metrics": self.telemetry.get_metrics(),
                    "traces": self.telemetry.get_traces()[-5:],
                    "api_circuit_open": self._api_circuit_open
                }
            finally:
                self._processing_request = False
                # Process any deferred events agent-driven now that request is complete
                if self._deferred_events:
                    logger.info(f"Processing {len(self._deferred_events)} deferred events agent-driven after request completion...")
                    deferred = self._deferred_events.copy()
                    self._deferred_events.clear()
                    for event in deferred:
                        if event.event_type == EventType.PATTERN_DETECTED:
                            if self.enable_llm_event_handling and not self._api_circuit_open:
                                self._agent_handle_pattern(event)
                            else:
                                self._handle_pattern(event.data)
    
    def reset_circuit_breaker(self):
        """
        Reset the API circuit breaker.
        Call this after refilling API credits to re-enable LLM event handling.
        """
        self._api_failure_count = 0
        self._api_circuit_open = False
        self.enable_llm_event_handling = True
        logger.info("Circuit breaker reset - LLM event handling re-enabled")
    
    def schedule_messages(self, 
                         messages: List[Dict[str, str]],
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         enforce_time_window: bool = False,
                         max_messages_per_hour: Optional[int] = None,
                         distribution_mode: str = "clustered") -> List[ScheduledMessage]:
        """
        Schedule messages using the jitter algorithm.
        
        ⚠️ DEPRECATED: This method bypasses the agent. Use agent.process_request() with 
        schedule_batch tool instead for agent-driven, event-driven scheduling.
        
        This method is kept for backward compatibility but should not be used in new code.
        All scheduling should go through the agent tools (schedule_batch) to ensure:
        - Event-driven architecture (events fired during jitter execution)
        - Agent analysis of jitter metrics
        - Agent decision-making and reasoning
        
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
        import warnings
        warnings.warn(
            "schedule_messages() bypasses the agent. Use agent.process_request() with schedule_batch tool instead.",
            DeprecationWarning,
            stacklevel=2
        )
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
        # Publish MESSAGE_SCHEDULED events (event-driven architecture)
        for scheduled_msg in scheduled:
            recipient = scheduled_msg.message.recipient
            if recipient not in self.scheduled_messages_by_recipient:
                self.scheduled_messages_by_recipient[recipient] = []
            self.scheduled_messages_by_recipient[recipient].append(scheduled_msg)
            
            # Publish MESSAGE_SCHEDULED event (event-driven)
            self.event_bus.publish(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.MESSAGE_SCHEDULED,
                timestamp=datetime.now(),
                data={
                    "recipient": scheduled_msg.message.recipient,
                    "scheduled_time": scheduled_msg.scheduled_time.isoformat(),
                    "typing_duration": scheduled_msg.typing_duration,
                    "explanation": scheduled_msg.explanation,
                }
            ))
        
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

