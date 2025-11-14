# GhostEye SMS Phishing Simulator

A complete system for scheduling SMS messages with human-realistic timing patterns, orchestrated by an event-driven AI agent.

## Overview

This implementation fully complies with the GhostEye SMS Phishing Simulator assessment requirements:

- **Part 1**: Jitter algorithm that models realistic human SMS behavior
- **Part 2**: Event-driven AI agent that packages the jitter algorithm as tools

## Features

### Part 1: Jitter Algorithm
-  Human typing speed modeling (WPM-based, varies by complexity: SIMPLE, MEDIUM, COMPLEX)
-  Thinking pauses during message composition
-  Time-of-day pattern clustering (work hours, peak times)
-  Pattern avoidance (prevents robotic timing patterns)
-  Realistic randomness (exponential distribution, not uniform)
-  Comprehensive explanations for each scheduled time

### Part 2: AI Agent Orchestration
-  **Event-driven AI agent** (fires events DURING algorithm execution, not after)
-  **4 specialized tools**: generate_messages, schedule_batch, handle_reply, and internal jitter calls
-  **LLM-driven decision making**: Agent uses GPT-4o-mini to analyze context and make decisions
-  **Workflow automation**: Reply handling with automatic looping support
-  **Full message traceability**: Unique IDs track messages through entire system
-  **Production-ready**: LangSmith telemetry, token tracking, cost monitoring
-  **Agent memory**: Stores conversation history and decision reasoning
-  **Structured tools**: LangChain v1 create_agent with Pydantic validation

## Project Structure

```
.
├── problem.md              # Assessment problem statement
├── README.md               # This file
├── ARCHITECTURE.md         # Detailed architecture diagrams (REFER HERE FOR ARCHITECTURE)
├── requirements.txt        # Python dependencies
├── run_simulation.py       # Main simulation runner with scenarios
├── src/
│   ├── jitter/
│   │   ├── __init__.py
│   │   ├── jitter_algorithm.py   # Part 1: Jitter algorithm
│   │   └── models.py              # Message and complexity models
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── sms_agent_core.py      # Part 2: AI agent core (LangChain v1)
│   │   ├── sms_agent.py           # Backward compatibility wrapper
│   │   ├── tools.py               # 4 LangChain tools
│   │   ├── event_bus.py           # Event-driven architecture
│   │   ├── reply_handler.py       # Reply handling workflow (2-call jitter pattern)
│   │   ├── telemetry.py           # Telemetry and token tracking
│   │   └── models.py              # Event and data models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Structured logging
│       ├── mock_sms.py            # Mock SMS sender
│       └── employee_simulator.py  # LLM-based employee simulator
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

**Note:** Part 1 works without any API keys. Part 2 requires OpenRouter API key.

## Usage

### Running Simulations

```bash
# Run all scenarios (default)
python run_simulation.py

# Run specific scenarios
python run_simulation.py --few-messages              # 3 messages to test
python run_simulation.py --multiple-users            # 50 messages across 3 users
python run_simulation.py --reply-handling            # Handle employee reply
python run_simulation.py --conversation-simulation   # Dynamic conversation

# Save to log file
python run_simulation.py > simulation_logs.txt 2>&1
```

### Scenario Details

#### Scenario 1: Few Messages
- Tests jitter algorithm with 3 messages of varying complexity
- Shows agent reasoning and jitter explanations

#### Scenario 2: Multiple Users (Part 3 Q1)
- 50 messages across 3 recipients over 6-hour workday
- Demonstrates clustered distribution strategy
- Shows agent analysis of timing for each message

#### Scenario 3: Reply Handling (Part 3 Q2)
- 50 messages scheduled, employee replies to message #12
- Agent pauses remaining messages
- Agent sends immediate reply (jitter-adjusted timing)
- Agent reschedules remaining 38 messages with extended delays

#### Scenario 4: Conversation Simulation (Part 3 Q2)
- 20 initial messages with LLM employee simulator
- Shows dynamic conversation adaptation
- Demonstrates reply handling workflow looping

### Message Complexity Levels

- **SIMPLE** (< 20 words): Fast typing, "Hey, verify account?"
- **MEDIUM** (20-50 words): Standard messages with more detail
- **COMPLEX** (> 50 words): Long messages with detailed explanations

### Direct API Usage

#### Part 1: Direct Jitter Algorithm

```python
from src.jitter import JitterAlgorithm, Message

jitter = JitterAlgorithm()
messages = [
    Message(content="Hey verify?", recipient="+1234567890"),
    Message(content="Thanks!", recipient="+1234567890"),
]

scheduled = jitter.schedule_message_queue(messages)
for s in scheduled:
    print(f"{s.scheduled_time}: {s.message.content}")
    print(f"Explanation: {s.explanation}")
```

#### Part 2: AI Agent Usage

```python
from src.agent import SMSAgent

# Initialize agent
agent = SMSAgent()

# Process request
result = agent.process_request(
    "Schedule a message saying 'Hello' to +1234567890"
)
print(result["response_text"])

# Get token usage and costs
token_usage = agent.get_token_usage()
print(f"Total tokens: {token_usage['total_tokens']:,}")
print(f"Total cost: ${token_usage['total_cost_usd']:.6f} USD")
```

## Event-Driven Agent Architecture

### How It Works

For detailed architecture diagrams, event flows, and system design, see **`ARCHITECTURE.md`**.

### 4 Tools Available to Agent

1. **generate_messages**: Generate message content via LLM
2. **schedule_batch**: Schedule messages using jitter algorithm
3. **handle_reply**: Handle recipient replies with 2-call jitter pattern
4. **(internal) jitter algorithm calls**: Abstracted within tools

### Reply Handling Workflow

The `handle_reply` tool uses a **2-call pattern**:

**CALL 1**: `jitter.schedule_message()` - Send immediate reply
- Generates reply content (via LLM or heuristics)
- Schedules with realistic timing (30-120 seconds)
- Jitter handles all timing calculations

**CALL 2**: `jitter.schedule_message_queue()` - Reschedule remaining messages
- Takes 38 remaining messages
- Applies extended delays (engagement multiplier)
- Ensures natural continuation of conversation

If another reply comes → Workflow loops automatically.

### Event Types

Events fire DURING jitter algorithm execution:

- `MESSAGE_QUEUED` - Message added to queue
- `TYPING_STARTED` - Typing simulation begins
- `MESSAGE_SCHEDULED` - Jitter scheduling complete
- `PATTERN_DETECTED` - Robotic pattern detected (optional)
- `REPLY_RECEIVED` - Employee replied (triggers reply workflow)
- `SCHEDULE_ADJUSTED` - Schedule modified
- `ERROR_OCCURRED` - Error occurred

### Message Tracking

Each message gets a unique `original_message_id` (UUID) that is tracked through:
- Event data
- Agent memory
- Reply handling (identifies which message was replied to)

## Telemetry & Observability

**Metrics Collected:**
- Messages queued, scheduled, sent
- Replies received
- Pattern violations detected
- Average typing time & inter-message delays

**Token & Cost Tracking:**
-  Automatic token counting for all LLM calls
-  Cost calculation based on OpenRouter pricing
-  Per-model usage breakdown
-  Export to JSON for analysis

**LangSmith Integration:**
- Full execution traces with context
- All agent decisions tracked
- Quality evaluators for decisions

## Key Design Decisions

### Why LangChain v1?
- Modern `create_agent` API
- Built-in tool calling support
- LangSmith integration for production telemetry

### Why OpenRouter?
- Unified API for multiple LLM providers
- Cost-effective (GPT-4o-mini)
- Easy to switch models

### Why Event-Driven?
- Loose coupling between jitter and agent
- Easy to extend with new event handlers
- Natural fit for workflow automation

### Why Unique Message IDs?
- Complete traceability through system
- Enables reliable reply matching
- Supports message state tracking

## Architecture Highlights

### Clean Abstraction
- Agent doesn't know jitter algorithm internals
- Tools call jitter algorithm (abstracted from agent)
- EventBus decouples components

### Message Tracking
- Unique `original_message_id` UUID per message
- Tracked through: scheduling, events, replies
- Enables accurate reply handling

### Workflow Automation
- Reply handling loops automatically
- Supports multiple replies from same recipient
- Engagement tracking for each recipient

### Production-Ready
- Comprehensive error handling
- Full telemetry and logging
- Token usage and cost monitoring
- LangSmith tracing support

## API Keys

### Getting OpenRouter API Key
1. Sign up at https://openrouter.ai
2. Get API key from dashboard
3. Set `OPENROUTER_API_KEY` environment variable

### Getting LangSmith API Key (Optional)
1. Sign up at https://smith.langchain.com
2. Get API key from settings
3. Set `LANGSMITH_API_KEY` environment variable

## For Detailed Architecture

**See `ARCHITECTURE.md` for:**
- Complete system architecture diagrams
- Event flow visualizations
- Jitter algorithm execution steps
- Reply handling workflow details
- Message tracking system
- Agent memory management
- Tool architecture breakdown

---

**Note:** This README provides quick-start information. For comprehensive technical architecture, refer to `ARCHITECTURE.md`.
