# GhostEye SMS Phishing Simulator - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│  GHOSTEYE SMS PHISHING SIMULATOR - HIGH-LEVEL ARCHITECTURE                        │
│                                                                                     │
│  Part 1: Human-Realistic Timing (Jitter Algorithm)                                │
│  Part 2: AI Agent Orchestration & Event-Driven Workflows                          │
│  Part 3: Multi-User Campaign Management & Reply Handling                           │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Component Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│                      SMS AGENT (Event-Driven Orchestrator)                   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ LLM Layer (OpenAI/GPT-4o-mini via OpenRouter)                      │    │
│  │  - LangChain v1 create_agent API                                   │    │
│  │  - Makes decisions based on events and context                     │    │
│  │  - Uses structured tools with Pydantic validation                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│         ▲                                  ▲                                   │
│         │ Decisions                       │ Events (Fire During Execution)    │
│         │                                 │                                   │
│  ┌──────┴──────┐              ┌───────────┴──────────┐                        │
│  │  Tools      │              │   Event Bus          │                        │
│  │  ────────   │              │   ──────────         │                        │
│  │ • schedule_ │              │ • MESSAGE_QUEUED    │                        │
│  │   message   │              │ • TYPING_STARTED    │                        │
│  │ • schedule_ │              │ • MESSAGE_SCHEDULED │                        │
│  │   batch     │              │ • REPLY_RECEIVED    │                        │
│  │ • handle_   │              │ • PATTERN_DETECTED  │                        │
│  │   reply     │              │ • ERROR_OCCURRED    │                        │
│  │ • generate_ │              │ • SCHEDULE_ADJUSTED │                        │
│  │   messages  │              └──────────────────────┘                        │
│  └──────┬──────┘                     ▲                                        │
│         │                            │                                        │
│         │ Uses                       │ Fires Events                           │
│         ▼                            │                                        │
│  ┌─────────────────────────────────┘                                         │
│  │                                                                             │
│  │    JITTER ALGORITHM (Part 1: Human-Realistic Timing)                      │
│  │    ──────────────────────────────────────────────────                     │
│  │                                                                             │
│  │    ┌─ Message Complexity Analysis ─┐                                      │
│  │    │ (SIMPLE/MEDIUM/COMPLEX)        │                                     │
│  │    │ - Word count analysis          │                                     │
│  │    │ - Reading time calculation     │                                     │
│  │    └────────────────────────────────┘                                     │
│  │                ▼                                                           │
│  │    ┌─ Typing Speed Simulation ─┐                                          │
│  │    │ WPM-based typing          │                                          │
│  │    │ - Base WPM: 40-60         │                                          │
│  │    │ - Complexity multiplier   │                                          │
│  │    │ - Thinking pauses (30%)   │                                          │
│  │    └───────────────────────────┘                                          │
│  │                ▼                                                           │
│  │    ┌─ Inter-Message Delays ─┐                                             │
│  │    │ - Exponential distribution  │                                        │
│  │    │ - Time-of-day clustering   │                                         │
│  │    │ - Work hour clustering     │                                         │
│  │    └────────────────────────────┘                                         │
│  │                ▼                                                           │
│  │    ┌─ Pattern Avoidance ─┐                                                │
│  │    │ - Prevents robotic patterns  │                                       │
│  │    │ - Detects sequence violations │                                      │
│  │    │ - Adjusts timing dynamically │                                       │
│  │    └──────────────────────────────┘                                       │
│  │                ▼                                                           │
│  │    Returns: ScheduledMessage                                              │
│  │    - Original message content                                             │
│  │    - Scheduled timestamp                                                  │
│  │    - Typing duration                                                      │
│  │    - Full explanation (for agent analysis)                                │
│  │                                                                             │
│  └─────────────────────────────────────────────────────────────────────────┘
│
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow: From User Request to Message Scheduling

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USER REQUEST                                                                 │
│ "Schedule 50 messages to multiple users with realistic timing"              │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ AGENT RECEIVES REQUEST                                                       │
│ - Analyzes requirements (context from LLM)                                   │
│ - Checks memory for context (previous messages, decisions)                   │
│ - Understands goals (undetectable phishing simulation)                       │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ AGENT MAKES DECISION (LLM Reasoning)                                         │
│ - Calls appropriate tool: generate_messages or schedule_batch                │
│ - Decides on distribution strategy (clustered vs even)                       │
│ - Provides parameters:                                                        │
│   • Message content (SMISHING-themed via LLM)                                │
│   • Recipients (distribute across users)                                     │
│   • Time window (e.g., 6-hour workday)                                       │
│   • Distribution mode (clustered for human-like appearance)                  │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
    ┌─────────────┐      ┌──────────────┐      ┌────────────────┐
    │ Tool 1:     │      │ Tool 2:      │      │ Tool 3:        │
    │ generate    │      │ schedule     │      │ handle_reply   │
    │ _messages   │      │ _batch       │      │ (if triggered) │
    │             │      │              │      │                │
    │ Generates   │      │ Schedules    │      │ Handles reply: │
    │ message     │      │ messages     │      │ - Pauses msgs  │
    │ content     │      │ using jitter │      │ - Sends reply  │
    │ via LLM     │      │ algorithm    │      │ - Reschedules  │
    └────────┬────┘      └──────┬───────┘      └────────┬───────┘
             │                  │                       │
             └──────────────────┼───────────────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │ JITTER ALGORITHM       │
                   │ Processes each message:│
                   │                        │
                   │ 1. Complexity analysis │
                   │ 2. Typing duration     │
                   │ 3. Inter-message delay │
                   │ 4. Pattern avoidance   │
                   │ 5. Schedule validation │
                   └────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │ EVENTS PUBLISHED TO EVENT BUS │
            │                               │
            │ For each message:             │
            │ • MESSAGE_QUEUED           │
            │ • TYPING_STARTED           │
            │ • MESSAGE_SCHEDULED        │
            │                               │
            │ (Optional, if triggered:)    │
            │ • PATTERN_DETECTED         │
            └────────┬──────────────────────┘
                     │
                     ▼
            ┌─────────────────────────┐
            │ AGENT RECEIVES EVENTS   │
            │                         │
            │ Agent analyzes:         │
            │ • Message complexity    │
            │ • Typing behavior       │
            │ • Pattern implications  │
            │ • Schedule implications │
            │                         │
            │ Stores in memory        │
            └─────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────────┐
        │ AGENT RESPONSE TO USER          │
        │                                 │
        │  X messages scheduled         │
        │  Strategy explanation         │
        │  Timing statistics            │
        │  Full jitter reasoning        │
        │  Telemetry & cost tracking    │
        └─────────────────────────────────┘
```

---

## 3. Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVENT BUS (Central Event Dispatcher)                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  Events fire DURING jitter algorithm execution (not after):                 │
│                                                                             │
│  1. MESSAGE_QUEUED                                                        │
│     └─ When: Message added to processing queue                              │
│     └─ Data: Message content, recipient, timestamp                          │
│     └─ Agent: Analyzes message complexity and content urgency               │
│                                                                             │
│  2. TYPING_STARTED                                                        │
│     └─ When: Typing simulation begins                                       │
│     └─ Data: Typing duration, WPM, complexity factor                        │
│     └─ Agent: Analyzes typing behavior plausibility                         │
│                                                                             │
│  3. MESSAGE_SCHEDULED                                                     │
│     └─ When: Jitter algorithm completes, message scheduled                  │
│     └─ Data: All jitter metrics (complexity, delay, timing, clustering)     │
│     └─ Agent: Analyzes full timing decision, stores in memory               │
│                                                                             │
│  4. PATTERN_DETECTED  (Optional)                                          │
│     └─ When: Robotic timing pattern detected in sequence                    │
│     └─ Data: Pattern type, messages involved, violation severity             │
│     └─ Agent: Analyzes why pattern is problematic → adjusts schedule         │
│                                                                             │
│  5. REPLY_RECEIVED  (Triggered by recipient reply)                        │
│     └─ When: Employee replies to message                                    │
│     └─ Data: Reply content, original message, timing                        │
│     └─ Agent: Analyzes reply → decides on response strategy → executes      │
│                                                                             │
│  6. SCHEDULE_ADJUSTED                                                     │
│     └─ When: Schedule modified (e.g., after reply, pattern fix)             │
│     └─ Data: Messages affected, new timing, reason                          │
│     └─ Agent: Logs decision, stores in memory                               │
│                                                                             │
│  7. ERROR_OCCURRED                                                        │
│     └─ When: Error happens during execution                                 │
│     └─ Data: Error message, affected component                              │
│     └─ Agent: Logs error, attempts recovery or escalation                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              ▲                           ▼
              │                    Event Handler Chain
              │                           │
      ┌───────┴────────┐        ┌────────┴──────────┐
      │ Jitter         │        │  Agent (LLM)      │
      │ Algorithm      │        │                   │
      │ Fires Events   │        │  Makes Decisions  │
      │ DURING         │        │  Calls Tools      │
      │ Execution      │        │  Stores Memory    │
      └────────────────┘        └───────────────────┘
```

---

## 4. Reply Handling Workflow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ EMPLOYEE REPLIES TO MESSAGE #12                                              │
│ "Yes, I'll verify now"                                                       │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ EVENT: REPLY_RECEIVED                                                      │
│ - Reply content: "Yes, I'll verify now"                                      │
│ - Original message: #12 (with original_message_id for tracking)              │
│ - Reply time: 09:23 AM (18 minutes after message sent)                       │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ AGENT ANALYZES REPLY (LLM Decision-Making)                                   │
│                                                                               │
│ Agent asks itself:                                                            │
│  "Is this a positive reply? YES - 'I'll verify now' = compliance"          │
│  "Should we pause remaining messages? YES - prevent multiple alerts"        │
│  "Should we send immediate reply? YES - acknowledge and confirm"            │
│  "When should we reschedule? LATER - with extended delays (engagement)"     │
│                                                                               │
│ Agent decision: "Use handle_reply tool to execute reply workflow"            │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
    ┌─────────────┐      ┌──────────────┐      ┌────────────────┐
    │ PHASE 1:    │      │ PHASE 2:     │      │ PHASE 3:       │
    │ PAUSE       │      │ SEND REPLY   │      │ RESCHEDULE     │
    │ MESSAGES    │      │ IMMEDIATELY  │      │ REMAINING      │
    ├─────────────┤      ├──────────────┤      ├────────────────┤
    │ Take 38     │      │ Generate     │      │ Pause →        │
    │ remaining   │      │ reply using  │      │ then reschedule│
    │ messages    │      │ LLM or       │      │ remaining 38   │
    │ (from #13   │      │ heuristics   │      │ messages       │
    │ onwards)    │      │              │      │                │
    │             │      │ Example:     │      │ For each:      │
    │ Move to     │      │ "Great!      │      │ - Call jitter  │
    │ paused      │      │ Account      │      │   algorithm    │
    │ queue       │      │ verified"    │      │ - Extended     │
    │             │      │              │      │   delays       │
    │ State:      │      │ Schedule at: │      │ - Account for  │
    │ 12 sent,    │      │ 09:24 AM     │      │   engagement   │
    │ 38 paused   │      │ (CALL 1 to   │      │                │
    │             │      │ jitter)      │      │ Fire events:   │
    │             │      │              │      │ MESSAGE_RESC.  │
    │             │      │ Fire: REPLY_ │      │ for each msg   │
    │             │      │ SENT event   │      │                │
    │             │      │              │      │ State: 14      │
    │             │      │ State: 13    │      │ sent, 36 new   │
    │             │      │ sent, 37     │      │ scheduled      │
    │             │      │ scheduled    │      │                │
    └─────┬───────┘      └──────┬───────┘      └────────┬───────┘
          │                     │                       │
          │ Jitter Calls:       │ Jitter Calls:       │ Jitter Calls:
          │ (implicit via       │ schedule_message()  │ schedule_message_queue()
          │  messaging)         │ (CALL 1)            │ (CALL 2)
          │                     │                     │
          └─────────────────────┴─────────────────────┘
                                │
                                ▼
                   ┌────────────────────────────┐
                   │ WORKFLOW COMPLETE          │
                   │                            │
                   │ State AFTER reply handling:│
                   │ - Sent: 13                 │
                   │ - Scheduled: 36            │
                   │ - Paused: 0                │
                   │                            │
                   │ If another reply comes:    │
                   │ → Same workflow loops      │
                   └────────────────────────────┘
```

---

## 5. Tool Architecture (4 Core Tools)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOLS AVAILABLE TO AGENT (LangChain v1)                                     │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ TOOL 1: generate_messages(scenario, num_messages)                  │    │
│ │ ───────────────────────────────────────────────────────────────    │    │
│ │ Purpose: Generate message content using LLM                        │    │
│ │ Input: Scenario description, number of messages                    │    │
│ │ Output: List of Message objects with content ready to schedule     │    │
│ │ Jitter Call:  No (uses LLM, not jitter)                         │    │
│ │                                                                     │    │
│ │ Example:                                                            │    │
│ │   generate_messages(                                               │    │
│ │     scenario="bank phishing",                                      │    │
│ │     num_messages=50                                                │    │
│ │   ) → [Message(...), Message(...), ...]                           │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ TOOL 2: schedule_batch(messages, recipients, time_window, mode)   │    │
│ │ ───────────────────────────────────────────────────────────────    │    │
│ │ Purpose: Schedule multiple messages with jitter algorithm         │    │
│ │ Input: Message list, recipient list, time window, mode            │    │
│ │ Output: ScheduledMessage objects with timing and explanations     │    │
│ │ Jitter Call:  YES - Calls jitter.schedule_message_queue()     │    │
│ │                                                                     │    │
│ │ Example:                                                            │    │
│ │   schedule_batch(                                                  │    │
│ │     messages=[50 Message objects],                                 │    │
│ │     recipients=["+1234567890", "+0987654321", ...],              │    │
│ │     start_time="09:00 AM",                                        │    │
│ │     end_time="15:00 (6 hours)",                                  │    │
│ │     mode="clustered"                                              │    │
│ │   ) → [ScheduledMessage(...), ...]                               │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ TOOL 3: handle_reply(recipient, reply_content, message_id)        │    │
│ │ ───────────────────────────────────────────────────────────────    │    │
│ │ Purpose: Handle recipient reply with 2-call jitter pattern        │    │
│ │ Input: Recipient, reply content, original message ID              │    │
│ │ Output: Status dict with action summary                           │    │
│ │ Jitter Calls:  YES (2 calls)                                    │    │
│ │   - CALL 1: jitter.schedule_message() for immediate reply        │    │
│ │   - CALL 2: jitter.schedule_message_queue() for rescheduled msgs │    │
│ │                                                                     │    │
│ │ Flow (from reply_handler.py):                                     │    │
│ │ 1. Pause remaining messages                                        │    │
│ │ 2. Generate immediate reply (LLM or heuristics)                   │    │
│ │ 3. Schedule immediate reply (CALL 1 to jitter)                    │    │
│ │ 4. Reschedule remaining messages (CALL 2 to jitter)              │    │
│ │ 5. If another reply comes → loop back to step 1                   │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ REMOVED: analyze_pattern                                                  │
│ Reason: Pattern analysis already built into jitter algorithm               │
│         (via PatternAvoidance class and PATTERN_DETECTED event)            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Message Tracking System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MESSAGE TRACKING VIA UNIQUE IDs                                             │
│                                                                             │
│ Each message gets a unique identifier when created:                         │
│                                                                             │
│ Message Object:                                                             │
│   content: "Hi verify your account..."                                     │
│   recipient: "+1234567890"                                                 │
│   original_message_id: "msg-abc123-def456..." ← UNIQUE UUID               │
│   complexity: MEDIUM                                                       │
│   is_correction: False                                                     │
│                                                                             │
│ Tracking Flow:                                                              │
│                                                                             │
│ 1. Message created:                                                        │
│    msg_id = "msg-abc123-def456..."                                         │
│                                                                             │
│ 2. Scheduled (jitter calculates timing):                                   │
│    ScheduledMessage {                                                      │
│      message_id: "msg-abc123-def456...",                                   │
│      scheduled_time: 09:15:45,                                             │
│      typing_duration: 38 seconds,                                          │
│      ...                                                                    │
│    }                                                                        │
│                                                                             │
│ 3. Event fired (agent receives):                                           │
│    MESSAGE_SCHEDULED event {                                               │
│      event_data: {                                                         │
│        original_message_id: "msg-abc123-def456...",  ← SAME ID            │
│        recipient: "+1234567890",                                           │
│        scheduled_time: 09:15:45,                                           │
│        ...                                                                  │
│      }                                                                      │
│    }                                                                        │
│                                                                             │
│ 4. Agent stores in memory:                                                 │
│    agent.scheduled_messages_by_recipient["+1234567890"] = [               │
│      ScheduledMessage(message_id="msg-abc123-def456...", ...)            │
│    ]                                                                        │
│                                                                             │
│ 5. If employee replies to "msg-abc123-def456...":                          │
│    reply_handler.handle_reply(                                             │
│      recipient="+1234567890",                                              │
│      original_message_id="msg-abc123-def456..."  ← IDENTIFIES WHICH       │
│    )                                                                        │
│    → System knows exactly which message was replied to                     │
│    → Can find remaining messages and reschedule them                       │
│                                                                             │
│ Result: Complete traceability through entire system                         │
│         from message creation → scheduling → reply handling                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Event-Driven Jitter Algorithm Execution (Example)

```
INPUT: Message = "Hi verify..." (15 words)
       Current time = 09:00:00 AM
       Previous message = 09:00:45 AM

┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Analyze Complexity                                 │
│ ─────────────────────────────                              │
│ Word count: 15 words → SIMPLE (< 20 words)                │
│ Fire EVENT: MESSAGE_QUEUED                               │
│ Agent receives event and analyzes message                  │
└─────────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Calculate Typing Duration                          │
│ ────────────────────────────────────                        │
│ Base WPM: 45 (humans typing fast messages)                 │
│ Complexity multiplier: 0.9 (SIMPLE is faster)              │
│ Adjusted WPM: 40.5 words/min                               │
│ Typing time: 15 words ÷ 40.5 = 22.2 seconds               │
│ Thinking pauses: +3 seconds (30% probability)              │
│ Total: 25 seconds                                          │
│ Fire EVENT: TYPING_STARTED                               │
│ Agent receives and validates typing duration               │
└─────────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Calculate Inter-Message Delay                      │
│ ─────────────────────────────────────                       │
│ Time-of-day: 09:00 (morning peak hour)                     │
│ Recent sequence: [09:00:45, ...previous msg]               │
│ Delay from previous: 09:00:45 + 2:45 = 09:03:30           │
│ BUT pattern avoidance check (next step) may adjust this    │
└─────────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Pattern Avoidance Check                            │
│ ──────────────────────────────                             │
│ Last 5 messages intervals:                                 │
│   [3:00, 2:55, 3:00, 3:05, 2:45] ← Very uniform!          │
│ Verdict: ROBOTIC PATTERN DETECTED                        │
│ Fire EVENT: PATTERN_DETECTED                             │
│ Agent receives and analyzes pattern violation              │
│ Adjustment: Change to 4:30 (break the pattern)             │
│ New scheduled time: 09:00:45 + 4:30 = 09:05:15             │
└─────────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Final Validation & Return                          │
│ ──────────────────────────────────                          │
│ ScheduledMessage {                                          │
│   scheduled_time: 09:05:15,                                │
│   typing_duration: 25 seconds,                             │
│   explanation: "SIMPLE message (15 words) at 09:05:15.     │
│                 Typing: 25 sec (45 WPM × 0.9). Delay:     │
│                 4:30 (pattern avoidance applied)."         │
│ }                                                           │
│ Fire EVENT: MESSAGE_SCHEDULED                            │
│ Agent receives full jitter metrics and analyzes            │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Agent Memory & Context Management

```
Memory Structure (List of Dicts):
─────────────────────────────────

[
  {
    "type": "user_request",
    "content": "Schedule 50 messages to 3 recipients...",
    "timestamp": "2025-11-13T09:00:00"
  },
  
  {
    "type": "agent_decision",
    "decision": "Clustered distribution strategy",
    "reasoning": "Humans send in clusters around work boundaries",
    "parameters": {...}
  },
  
  {
    "type": "jitter_metrics_analysis",
    "scheduled_time": "2025-11-13T09:08:50",
    "complexity": "SIMPLE",
    "typing_duration": 24,
    "pattern_analysis": "Detected 3-min uniform interval, adjusted",
    "natural_rating": "Human-like"
  },
  
  {
    "type": "agent_reply_decision",
    "reply_content": "Yes, I'll verify now",
    "decision": "Pause remaining messages and reschedule",
    "actions_taken": ["Paused 38", "Generated reply", "Rescheduled"]
  },
  
  ... more entries ...
]

Memory Usage:
─────────────
1. Context: Agent understands what's been done previously
2. Decision-making: Consistent with past decisions
3. Transparency: Full reasoning trail
```

---

## 9. System Strengths & Design Patterns

### Event-Driven Architecture
- **Real-time reactions**: Events fire DURING algorithm execution
- **Loose coupling**: Jitter and Agent don't know about each other's internals
- **Extensible**: Can add new event handlers without modifying core code

### Clean Tool Design
- **Tool composition**: Multiple specialized tools, not one monolithic tool
- **Single responsibility**: Each tool does one thing well
- **Jitter abstraction**: Tools call jitter algorithm internally (hidden from agent)

### Message Tracking
- **Unique IDs**: Every message has `original_message_id` UUID
- **Event data includes ID**: Full traceability through system
- **Reply matching**: Can identify which message was replied to

### Reply Handling Workflow
- **2-call pattern**: Immediate reply (CALL 1) + batch reschedule (CALL 2)
- **Loop support**: If another reply comes, workflow repeats automatically
- **Engagement tracking**: Records which recipients are actively responding

---

## 10. Removed Redundancy

```
BEFORE (Redundant):
───────────────────
Tool 5: analyze_pattern 
  • Duplicate of pattern detection built into jitter algorithm
  • PatternAvoidance class already handles detection
  • PATTERN_DETECTED event already fires with full context
  • Removed to simplify architecture and reduce code

Result: 5 tools → 4 tools (no functionality loss)
```

---

## Summary

Your architecture is a **production-ready, event-driven AI agent system** that:

1. **Receives requests** from users
2. **Makes intelligent decisions** using LLM
3. **Orchestrates 4 specialized tools** (generate_messages, schedule_batch, handle_reply, and internal jitter calls)
4. **Fires events** at key points during jitter algorithm execution
5. **Reacts to events** with LLM-driven analysis and decisions
6. **Manages complex workflows** for reply handling with automatic looping
7. **Maintains full traceability** via unique message IDs
8. **Stores rich context** in agent memory
9. **Adapts dynamically** when employees reply or patterns are detected
10. **Provides observability** via telemetry and LangSmith integration
