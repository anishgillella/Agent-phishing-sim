# Part 1 & 2: Jitter Algorithm + AI Agent

A complete system for scheduling SMS messages with human-realistic timing patterns, orchestrated by an event-driven AI agent.

## Overview

This implementation demonstrates Parts 1 and 2 of the GhostEye SMS Phishing Simulator assessment:

- **Part 1**: Jitter algorithm that models realistic human SMS behavior
- **Part 2**: Event-driven AI agent that packages the jitter algorithm as a tool

## Features

### Part 1: Jitter Algorithm
- ✅ Human typing speed modeling (WPM-based, varies by complexity)
- ✅ Thinking pauses during message composition
- ✅ Time-of-day pattern clustering (work hours, peak times)
- ✅ Pattern avoidance (prevents robotic timing patterns)
- ✅ Realistic randomness (exponential distribution, not uniform)
- ✅ Explanations for each scheduled time

### Part 2: AI Agent
- ✅ Event-driven architecture (EventBus)
- ✅ LangChain v1 with `create_agent`
- ✅ OpenRouter integration (GPT-4o-mini)
- ✅ LangSmith telemetry and tracing (LLM calls)
- ✅ Logfire integration (Pydantic model validation)
- ✅ Tool calling with structured output (Pydantic)
- ✅ Agent memory and context engineering
- ✅ Comprehensive metrics and event tracking

## Project Structure

```
.
├── problem.md              # Assessment problem statement
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── run_simulation.py       # Main simulation runner
├── src/
│   ├── jitter/
│   │   ├── __init__.py
│   │   └── jitter_algo.py   # Part 1: Jitter algorithm
│   ├── agent/
│   │   ├── __init__.py
│   │   └── sms_agent.py     # Part 2: AI agent (LangChain v1)
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # Structured logging
│       └── mock_sms.py      # Mock SMS sender
└── logs/                   # Generated simulation logs (JSON)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# REQUIRED - For Part 2 AI Agent
OPENROUTER_API_KEY=your_openrouter_api_key_here

# OPTIONAL - Telemetry & Observability
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=ghosteye-smishing-sim
LOGFIRE_API_KEY=your_logfire_api_key_here
```

**Required:**
- `OPENROUTER_API_KEY` - Required for Part 2 (LLM access)

**Optional:**
- `LANGSMITH_API_KEY` - For LLM tracing and telemetry
- `LANGSMITH_PROJECT` - LangSmith project name (defaults to "ghosteye-smishing-sim")
- `LOGFIRE_API_KEY` - For Pydantic model validation

**Note:** Part 1 works without any API keys. Part 2 requires OpenRouter API key. Telemetry works locally without LangSmith/Logfire keys.

## Quick Start

### Full End-to-End Simulation

Run the complete pipeline with agent orchestration, jitter scheduling, mock SMS sending, and telemetry:

```bash
python run_simulation.py
```

This will:
1. Initialize the SMS Agent with LangChain v1
2. Create and schedule 6 messages using the jitter algorithm
3. Send messages via mock SMS sender
4. Process LLM requests for strategic analysis
5. Collect and display comprehensive telemetry
6. Save structured logs to `logs/` directory

## Usage

### Part 1: Direct Jitter Algorithm Usage

```python
from src.jitter import JitterAlgorithm, Message

jitter = JitterAlgorithm()
messages = [
    Message(content="Hey, can you check the report?", recipient="+1234567890"),
    Message(content="Thanks!", recipient="+1234567890"),
]

scheduled = jitter.schedule_message_queue(messages)
for s in scheduled:
    print(f"{s.scheduled_time}: {s.message.content}")
```

### Part 2: AI Agent Usage

```python
from src.agent import SMSAgent

# Initialize agent with API keys
agent = SMSAgent()

# Option 1: Use agent with LLM
result = agent.process_request(
    "Schedule a message saying 'Hello' to +1234567890"
)
print(result["response_text"])

# Option 2: Programmatic scheduling (no LLM)
scheduled = agent.schedule_messages([
    {"content": "Hello", "recipient": "+1234567890"}
])

# Get telemetry
telemetry = agent.get_telemetry()
print(telemetry["metrics"])

# Get token usage and costs
token_usage = agent.get_token_usage()
print(f"Total tokens: {token_usage['total_tokens']:,}")
print(f"Total cost: ${token_usage['total_cost_usd']:.6f} USD")

# Export token usage to JSON
agent.export_token_usage("token_usage.json")
```

## Part 2: Event-Driven Architecture

### Events Handled

- `MESSAGE_QUEUED`: When message added to queue
- `MESSAGE_SCHEDULED`: When jitter algorithm schedules message
- `TYPING_STARTED`: When typing simulation begins
- `MESSAGE_SENT`: When message actually sent
- `REPLY_RECEIVED`: When recipient replies (triggers rescheduling)
- `PATTERN_DETECTED`: When pattern violation detected (triggers adjustment)
- `SCHEDULE_ADJUSTED`: When schedule is modified
- `ERROR_OCCURRED`: When errors happen

### Tools Available to Agent

1. **schedule_message**: Schedule single message with jitter algorithm
2. **schedule_batch**: Schedule multiple messages at once
3. **analyze_pattern**: Analyze detected patterns and provide recommendations

### Telemetry Collected

**Metrics:**
- `messages_queued`: Total messages queued
- `messages_scheduled`: Total messages scheduled
- `messages_sent`: Total messages sent
- `replies_received`: Total replies received
- `pattern_violations`: Pattern violations detected
- `schedule_adjustments`: Schedule adjustments made
- `average_typing_time`: Average typing duration
- `average_inter_message_delay`: Average delay between messages

**Traces:**
- All events with full context
- LLM calls (via LangSmith)
- Tool executions
- Timestamps for all operations

**Token Usage & Cost Tracking:**
- ✅ Automatic token counting for all LLM API calls
- ✅ Cost calculation based on OpenRouter pricing models
- ✅ Per-model usage breakdown
- ✅ Export token usage to JSON for analysis
- ✅ Real-time cost tracking (USD)
- ✅ Production-ready cost monitoring

## Design Decisions

### Why LangChain v1?
- Modern `create_agent` API simplifies agent creation
- Built-in tool calling support
- LangSmith integration for production telemetry
- Middleware support for extensibility

### Why OpenRouter?
- Unified API for multiple LLM providers
- Cost-effective (GPT-4o-mini)
- Easy to switch models if needed

### Why Event-Driven?
- Loose coupling between components
- Easy to extend with new event handlers
- Natural fit for workflow automation
- Enables reactive scheduling adjustments

### Why Structured Output (Pydantic)?
- Type-safe tool responses
- Better LLM understanding of expected outputs
- Validation built-in
- Production-ready error handling

## API Keys

### Getting OpenRouter API Key
1. Sign up at https://openrouter.ai
2. Get API key from dashboard
3. Set `OPENROUTER_API_KEY` environment variable

### Getting LangSmith API Key (Optional)
1. Sign up at https://smith.langchain.com
2. Get API key from settings
3. Set `LANGSMITH_API_KEY` environment variable

## Next Steps

- Part 3: Constraints & Trade-offs (strategic questions)
- Production deployment considerations
- Additional event handlers
- More sophisticated workflows
