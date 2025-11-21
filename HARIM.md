# HARIM: Real-Time Human + AI Interaction Risk Monitor

A 48-hour MVP for detecting manipulation, fraud, and social engineering in real-time text communication. Built to demonstrate rapid full-stack execution with LLM-driven threat detection and automated incident response.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [System Architecture](#system-architecture)
  - [Data Flow](#data-flow)
  - [Technology Stack](#technology-stack)
- [Development Phases](#development-phases)
  - [Phase 1: Data Ingestion Pipeline (FastAPI)](#phase-1-data-ingestion-pipeline-fastapi)
  - [Phase 2: Real-Time Threat Classification](#phase-2-real-time-threat-classification)
  - [Phase 3: Automated Incident Response Engine](#phase-3-automated-incident-response-engine)
  - [Phase 4: Semantic Similarity Search (Qdrant)](#phase-4-semantic-similarity-search-qdrant)
  - [Phase 5: Frontend Dashboard (React)](#phase-5-frontend-dashboard-react)
- [Testing Strategy](#testing-strategy)
- [Key Differentiators](#key-differentiators)
- [Repository Structure](#repository-structure)
- [Deployment](#deployment)
- [Future Roadmap](#future-roadmap)

---

## Overview

HARIM (Human + AI Interaction Risk Monitor) is a real-time, full-stack threat detection and automated incident response system designed to analyze text-based communications (SMS, email, chat, or simulated attacker vs. victim scenarios) and flag risky behavior in milliseconds.

### What It Does

- Ingests messages from multiple channels in real-time
- Classifies each message for fraud, manipulation, social engineering, and urgency using LLM + heuristics
- Automatically flags incidents and generates response recommendations
- Stores message embeddings for semantic similarity search across past incidents
- Provides a real-time SOC-style dashboard with live threat visualization

### Why It Matters

Modern attackers increasingly leverage LLM-generated persuasion, tailored phishing, and social engineering scripts. Organizations need real-time, agent-driven, continuous monitoring of communication channels—not static filters or one-off scans.

HARIM solves this by delivering:

- Live streaming of communication events
- Real-time risk scoring
- Automated incident handling
- Semantic search for related past attacks
- Human-in-the-loop interface

### Why This Project

This MVP demonstrates:

- 0→1 product thinking
- Real-time communication risk modeling
- Full-stack execution (FastAPI, React, LLMs)
- LLM-driven threat classification
- Automated response agents
- Semantic memory and similarity search
- Strong architectural tradeoff reasoning
- Production-ready security system design

HARIM represents what DeepTrust does for voice/video—but for text. It illustrates how security risk engines can be designed, deployed, and iterated quickly by a high-autonomy engineer.

---

## Architecture

### System Architecture

```
        ┌─────────────────────────────────┐
        │   Simulation/Channels           │
        │ (email, SMS, chat, smishing)    │
        └──────────────┬──────────────────┘
                       │
                       v
    ┌──────────────────────────────────────────────┐
    │        FastAPI Backend (Core)                │
    │                                              │
    │  Ingestion Layer:                            │
    │    • /ingest   - Stream messages/events      │
    │    • /events   - Live event log              │
    │                                              │
    │  Threat Engine Layer:                        │
    │    • LLM-based risk classifier               │
    │    • Heuristic detectors                     │
    │    • Risk fusion logic                       │
    │                                              │
    │  Response Engine Layer:                      │
    │    • Auto-flagging                           │
    │    • Auto-replies & escalation               │
    │    • Incident tracking                       │
    │                                              │
    │  Memory Layer:                               │
    │    • Embedding generator                     │
    │    • Qdrant vector store                     │
    │    • /incidents  - Detected threats          │
    │    • /similar    - Similarity search          │
    └──────────────────────────────────────────────┘
                       │
                       v
        ┌─────────────────────────────────┐
        │   React Frontend Dashboard      │
        │  • Live message feed            │
        │  • Threat heatmap               │
        │  • Incident timeline            │
        │  • Similarity explorer          │
        │  • System telemetry             │
        └─────────────────────────────────┘
```

### Data Flow

```
MESSAGE INGESTION → CLASSIFICATION → INCIDENT RESPONSE → STORAGE & MEMORY

1. Ingestion:
   Message Event (SMS, email, chat) 
   → FastAPI /ingest endpoint
   → Normalize to standard format

2. Classification:
   Normalized Message
   → Heuristic detector (rules, keywords, patterns)
   → LLM classifier (OpenAI/Anthropic)
   → Risk fusion (combine signals)
   → Risk Score (0-100)

3. Incident Response:
   Risk Score > Threshold?
   → YES: Flag incident, generate action recommendation
   → Auto-respond (block, warn, escalate)
   → Create incident record

4. Memory & Search:
   All messages & incidents
   → Embedding generator (sentence-transformers)
   → Store in Qdrant
   → Enable semantic similarity search

5. Dashboard:
   Events & Incidents
   → React frontend polling /events, /incidents
   → Real-time visualization
   → User can query /similar for related incidents
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI + Python | REST API, real-time ingestion, threat classification |
| **LLM/Reasoning** | OpenAI API / Anthropic | Risk classification, incident reasoning |
| **Vector Storage** | Qdrant | Semantic similarity search, incident memory |
| **Embeddings** | sentence-transformers | Generate embeddings for messages/incidents |
| **Frontend** | React + TypeScript | Real-time SOC dashboard, user controls |
| **Charts** | Recharts / Chart.js | Threat heatmap, system telemetry visualization |
| **HTTP Client** | Axios / Fetch API | Dashboard <→ Backend communication |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | Cloud hosting, serverless scaling |

---

## Development Phases

### Phase 1: Data Ingestion Pipeline (FastAPI)

#### What We Built

- `/ingest` endpoint: Streams messages or simulation events in real-time
- `/events` endpoint: Fetches chronological system events
- Normalized message schema: `{content, channel, timestamp, sender, metadata}`
- Event logging: All ingestion, classification, and response actions tracked

#### Why This Approach

- FastAPI provides async/await for non-blocking I/O and high throughput
- Minimal boilerplate enables rapid iteration
- Clear separation: ingestion → classification → storage → exposure
- Easy to extend to new channels (Slack API, SendGrid webhooks, etc.)

#### Key Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| REST endpoints first | Simpler than WebSockets; can upgrade to streaming later |
| No auth layer in MVP | Faster to prototype; add API keys + RBAC in production |
| In-memory event store | Fast iteration; migrate to PostgreSQL for persistence |
| Synchronous ingestion | Simpler pipeline; move to async queues (Kafka, Redis) at scale |

#### How to Improve

- Add WebSocket support for true push-based event streaming
- Integrate directly with communication APIs (Twilio, SendGrid, Slack RTM)
- Add rate limiting, backpressure, and circuit breakers
- Implement multi-tenant isolation with tenant-scoped event logs
- Add comprehensive audit logging and compliance hooks

---

### Phase 2: Real-Time Threat Classification

#### What We Built

A lightweight but powerful threat classifier that scores messages for:

- **Urgency**: "Act now", "limited time", pressure language
- **Manipulation**: Social engineering cues, emotional triggers
- **Fraudiness**: Financial/credential requests, wire transfer language
- **Harmful Intent**: Threats, coercion, harassment signals
- **Impersonation**: Spoofing executive, support, authority figures
- **AI-Generated Patterns**: Unusual phrasing, repetition, hallucinations

#### Classification Pipeline

```
Message Input
    ↓
Heuristic Layer (Fast, deterministic):
  • Keyword matching (phishing keywords, urgency)
  • Pattern matching (OTP requests, wire transfers)
  • Length/complexity analysis
    ↓
LLM Layer (Accurate, flexible):
  • System prompt: security analyst persona
  • Classification taxonomy (fraud, social eng, spam, legitimate)
  • Confidence scoring
    ↓
Risk Fusion Logic:
  • Combine heuristic + LLM signals
  • Weight by confidence
  • Output: risk_score (0-100), category, reasoning
    ↓
Incident Trigger:
  • If risk_score > threshold: Flag as incident
  • Log reasoning for audit trail
```

#### Why This Approach

- **LLM provides generalization**: Not locked into static rule sets; can reason about novel attacks
- **Heuristics enforce determinism**: Fast deterministic signals reduce false negatives
- **Together = balanced speed + accuracy**: Heuristics catch obvious threats; LLM handles nuanced social engineering
- **Explainability**: Reasoning trail is valuable for security analysts

#### Key Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| Lightweight LLM (gpt-3.5, Claude) | Faster, cheaper → less accurate than largest models |
| Hybrid rules + LLM | More interpretable; requires tuning for your domain |
| Synchronous classification | Simpler pipeline; not fully parallelized |
| Single-pass scoring | Fast; misses multi-message context/sequences |

#### How to Improve

- Add streaming LLM classification for token-by-token risk changes
- Implement ensemble models (multiple LLMs, voting)
- Add user-personalized risk baselines (reduce false positives)
- Fine-tune embeddings on domain-specific phishing/fraud data
- Add temporal context (classify message sequences, not isolated messages)

---

### Phase 3: Automated Incident Response Engine

#### What We Built

When a threat is detected, the system automatically:

- **Flags the incident**: Creates incident record with metadata
- **Categorizes severity**: Critical, High, Medium, Low based on risk score
- **Generates recommendations**: Suggested actions (block, warn user, escalate to security team)
- **Executes auto-responses**: Optional automatic actions (send warning reply, log to SIEM)
- **Tracks workflow**: Incident state transitions (new → analyzed → responded → resolved)

#### Incident Response Workflow

```
High-Risk Message Detected
    ↓
Create Incident Record:
  • timestamp, sender, content, risk_score, reasoning
  • category (phishing, fraud, social eng, etc.)
    ↓
Determine Severity:
  • risk_score > 85: CRITICAL
  • risk_score 70-85: HIGH
  • risk_score 50-70: MEDIUM
  • risk_score < 50: LOW
    ↓
Generate Recommendations:
  • Heuristic rules: IF (OTP request + urgent) → recommend BLOCK
  • LLM reasoning: "This looks like executive impersonation, recommend escalate to security"
    ↓
Optional Auto-Response:
  • Send warning to user: "This message appears suspicious"
  • Log to security queue: Create ticket in incident management system
  • Block sender: Add to blocklist
    ↓
Store Incident:
  • incident_id, severity, recommendation, response_action
  • Full audit trail for compliance
```

#### Why This Matters

- **Speed**: Millisecond detection vs. manual review (hours/days)
- **Consistency**: Rules applied uniformly across all messages
- **Scalability**: Automated response frees security team for investigation

#### Key Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| Rule-based auto-response | Predictable, fast; not adaptive to novel attacks |
| LLM-generated guidance | Contextually aware; can hallucinate or suggest wrong actions |
| Stateless actions | Simpler to implement; misses long-term patterns |
| Immediate response | Catches threats fast; can cause false-positive cascades |

#### How to Improve

- Add stateful session tracking (detect multi-message social engineering)
- Implement human-in-the-loop approval for auto-responses
- Add multi-agent negotiation (attacker AI vs. defender AI)
- Build workflow engine for SOC teams (custom escalation policies)
- Integrate with enterprise tools (PagerDuty, Slack, Splunk, CrowdStrike)

---

### Phase 4: Semantic Similarity Search (Qdrant)

#### What We Built

For every message and incident, we generate embeddings and store them in Qdrant vector database.

Enables:

- "Show me similar past incidents to this one"
- Attack clustering (group related phishing campaigns)
- Pattern detection (emerging threat types)
- Prototype matching ("Is this like previous executive impersonation attempts?")
- Historical context for incident triage

#### Embedding Pipeline

```
Message / Incident Input
    ↓
Embedding Generation:
  • Use sentence-transformers (e.g., all-MiniLM-L6-v2)
  • Convert text to 384-dim vector
  • Captures semantic meaning
    ↓
Store in Qdrant:
  • Vector ID, embedding, metadata (sender, timestamp, risk_score, category)
  • Indexed for fast retrieval
    ↓
Query Interface:
  • User provides incident of interest
  • Generate embedding for query
  • Cosine similarity search: find top-K similar incidents
  • Return ranked list with similarity scores
    ↓
Dashboard Display:
  • Show similar incidents with context
  • Highlight common patterns (keywords, sender domains, etc.)
```

#### Why This Matters

This turns the system from a simple **classifier** into a **learning system**.

- Threats evolve; static detection fails
- Embedding search creates continuous intelligence
- Security analysts gain context ("We've seen 47 similar attacks in the past 3 months")
- Early warning for trending attack vectors

#### Key Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| sentence-transformers | Fast and simple; weaker for domain-specific fraud |
| Qdrant local mode | Lightweight; not distributed for multi-region deployments |
| Store embeddings per message | High granularity; large memory footprint at scale |
| Cosine similarity | Fast retrieval; other metrics may be more semantically appropriate |

#### How to Improve

- Fine-tune domain-specific embeddings on phishing + fraud data
- Add temporal/spatial clustering (detect campaigns vs. isolated attacks)
- Implement graph analytics (link analysis, sender domain networks)
- Add anomaly detection over embedding space
- Scale to distributed vector store (Milvus, Weaviate) for multi-region

---

### Phase 5: Frontend Dashboard (React)

#### What We Built

A clean, real-time React dashboard featuring:

**Core Panels:**

- **Live Message Feed**: Real-time stream of ingested messages with risk badges
- **Threat Heatmap**: Visual distribution of risk scores (color-coded by severity)
- **Incident Timeline**: Chronological view of detected threats and responses
- **Similarity Explorer**: Query interface for finding related past incidents
- **System Telemetry**: Message processing rate, classification latency, incident count

**Controls:**

- Start/stop simulation
- Filter by risk score, category, channel, time range
- Export incidents as JSON
- Search messages by keyword
- Drill-down into incident details

#### Dashboard Architecture

```
React Frontend (Vercel)
    ↓
API Layer (Axios):
  • Poll /events (5s interval)
  • Poll /incidents (10s interval)
  • POST /similar (on user query)
    ↓
State Management:
  • useEffect hooks for fetching
  • useState for UI state
  • useMemo for expensive computations
    ↓
Components:
  • MessageFeed (renders events)
  • ThreatHeatmap (Chart.js or Recharts)
  • IncidentTimeline (vertical timeline with badges)
  • SimilarityExplorer (search results, ranked)
  • Telemetry (KPI cards, sparklines)
    ↓
Real-Time Updates:
  • Polling backend for new events
  • WebSocket (optional upgrade)
  • Background updates without blocking UI
```

#### Why It Matters

DeepTrust evaluates candidates on:

- UI/UX sense: Can you translate ML signals into actionable interfaces?
- Communication clarity: Does the dashboard tell a clear story?
- Real-time visualization: Can you handle streaming data in React?
- Product thinking: Does the UI reduce cognitive load for security analysts?

#### Key Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| React (web) over Electron | Faster to build; desktop app requires more work |
| Polling REST vs. WebSockets | More stable; less real-time (5-10s latency) |
| Minimal styling | Fast iteration; less polished visuals |
| Local state management | Simple; not suitable for complex multi-user scenarios |

#### How to Improve

- Upgrade to WebSockets for sub-second event updates
- Convert to Electron desktop app for cross-platform distribution
- Add timeline scrubber (play/pause incident timeline)
- Add configurable alert rules and automated policies
- Add user feedback loop (mark false positives, improve model)
- Add dark mode and accessibility features
- Implement role-based access control (analyst vs. manager views)

---

## Testing Strategy

### Functional Testing

- **Happy path**: Legitimate message (no risk) → passes through, no incident
- **Obvious threat**: "Click this link to verify your account" → flagged as phishing
- **Edge cases**: Empty message, very long message, unusual encodings

### Adversarial Testing

- **LLM-generated phishing**: Use an LLM to generate realistic phishing messages; verify detection
- **Rephrased scams**: Paraphrase known phishing to test robustness
- **Social drills**: "Pretend your CEO asks for a wire transfer" → test classification

### System Testing

- **End-to-end**: Message ingestion → classification → incident response → dashboard display
- **Concurrent messages**: Verify system handles multiple parallel message streams
- **Similarity search**: Verify embeddings are stored and retrieved correctly

---

## Key Differentiators

### What Makes HARIM Stand Out

1. **Full-Stack Execution**: Backend + Frontend + LLM reasoning in 48 hours
2. **Real-Time Risk Detection**: Millisecond latency from message to risk score
3. **Semantic Memory**: Unlike static rule-based systems, learns from past incidents
4. **Automated Response**: Recommends and optionally executes security actions
5. **Production-Grade Design**: Clear architecture, tradeoff reasoning, scalability path
6. **LLM-Native**: Leverages LLMs for reasoning, not just classification
7. **Extensibility**: Clear roadmap to multi-channel, voice, adversarial AI, enterprise integration

### Why This Impresses DeepTrust

- **Alignment**: HARIM is text-based DeepTrust—demonstrates understanding of their domain
- **Founding Engineer Mindset**: Shows tradeoff reasoning, MVP prioritization, shipping
- **Technical Depth**: LLMs, vector databases, real-time systems, full-stack
- **Product Thinking**: Solves a real problem with a clear market
- **Execution**: Rapid prototyping + production-ready design

---

## Repository Structure

```
harim/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration (API keys, model names, thresholds)
│   ├── routers/
│   │   ├── ingest.py              # POST /ingest endpoint
│   │   ├── events.py              # GET /events endpoint
│   │   ├── incidents.py           # GET /incidents endpoint
│   │   └── similar.py             # POST /similar endpoint
│   ├── threat_engine/
│   │   ├── classifier.py          # LLM-based risk classifier
│   │   ├── heuristics.py          # Heuristic rule detector
│   │   ├── fusion.py              # Risk score fusion logic
│   │   └── embeddings.py          # Embedding generation
│   ├── response_engine/
│   │   ├── incident_handler.py    # Incident creation & tracking
│   │   └── auto_response.py       # Auto-response logic
│   ├── storage/
│   │   ├── qdrant_client.py       # Qdrant vector store wrapper
│   │   └── in_memory_store.py     # Event/incident store (MVP)
│   ├── models.py                  # Pydantic models (Message, Incident, Event)
│   ├── schemas.py                 # Request/response schemas
│   └── requirements.txt            # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MessageFeed.tsx
│   │   │   ├── ThreatHeatmap.tsx
│   │   │   ├── IncidentTimeline.tsx
│   │   │   ├── SimilarityExplorer.tsx
│   │   │   └── Telemetry.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── IncidentDetail.tsx
│   │   ├── hooks/
│   │   │   ├── useEvents.ts
│   │   │   └── useIncidents.ts
│   │   ├── api/
│   │   │   └── client.ts          # Axios client for backend
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── docs/
│   ├── ARCHITECTURE.md            # Detailed system design
│   ├── DEPLOYMENT.md              # Deploy to Vercel + Railway
│   └── API.md                     # API endpoint reference
│
├── .gitignore
├── LICENSE
└── README.md                      # This file
```

---

## Deployment

### Backend Deployment (FastAPI)

**Option 1: Railway.app (Recommended)**

- Connect GitHub repo
- Railway auto-detects FastAPI
- Sets environment variables (API keys)
- Deploy with one click
- Built-in database + vector store support

**Option 2: Fly.io**

- Lightweight, no-nonsense PaaS
- Docker containerization
- Global edge deployment
- Competitive pricing

**Option 3: AWS Lambda + API Gateway**

- Serverless scaling
- Pay per request
- Integration with other AWS services
- More operational overhead

### Frontend Deployment (React)

**Vercel (Recommended)**

- Git-connected deployments
- Automatic HTTPS
- Global CDN
- Environment variable management
- Integrates seamlessly with Next.js (if you migrate)

**Steps:**

1. Push code to GitHub
2. Connect Vercel to repo
3. Set environment variables (`REACT_APP_API_URL=<backend-url>`)
4. Deploy
5. Live in 60 seconds

### Vector Store Deployment (Qdrant)

**Option 1: Qdrant Cloud (Recommended for MVP)**

- Managed vector database
- Pay-as-you-go
- REST API out of the box
- No ops overhead

**Option 2: Self-Hosted (Production)**

- Deploy Qdrant container on Railway/Fly.io
- Full control, lower cost at scale
- Requires ops expertise

---

## Future Roadmap

### Phase 6: Multi-Agent Adversarial Simulation

**What:** Deploy two agents:

- **Attacker Agent**: LLM trained to generate increasingly sophisticated phishing/social engineering messages
- **Defender Agent**: HARIM's threat detector, adapting to new attack patterns

**Why:** Shows adversarial AI thinking, highly relevant to security product design

**Timeline:** 1-2 days additional development

### Phase 7: Voice/Call Support

**What:** Extend to voice channels using LiveKit + audio transcription

- Transcribe incoming calls
- Classify for deepfake/spoofing
- Detect social engineering in real-time

**Why:** Aligns with DeepTrust's core (voice is their primary channel)

**Timeline:** 3-5 days

### Phase 8: Enterprise Integration

**What:** SIEM/SOAR connectors

- PagerDuty incident creation
- Slack alerts
- Splunk data ingestion
- CrowdStrike API integration

**Why:** Makes system production-ready for enterprise deployments

**Timeline:** 2-3 days per integration

### Phase 9: User-Specific Risk Baselines

**What:** Learn per-user communication patterns

- "This user never sends urgent messages" → urgent message is higher risk
- "This sender always communicates at 9 AM" → 3 AM message is anomalous

**Why:** Dramatically reduces false positives, improves model personalization

**Timeline:** 2-3 days

### Phase 10: Distributed Inference

**What:** Move threat classification to Modal or AWS Lambda GPU backends

- Scale classification independently from ingestion
- Support millions of concurrent messages
- Pay-per-use compute

**Why:** Production scalability

**Timeline:** 3-5 days

---

## Contributing

This is a portfolio/demo project. For contributions, questions, or discussions:

1. Open an issue describing the feature or bug
2. Discuss approach before implementation
3. Submit PR with clear description and tests

---

## License

MIT License. See LICENSE file for details.

---

## Contact

For questions or opportunities:

- Email: [your email]
- LinkedIn: [your profile]
- GitHub: [your profile]

---

## Acknowledgments

Built as a 48-hour MVP to demonstrate rapid full-stack execution and LLM product thinking for the DeepTrust founding engineer interview. Inspired by production security platforms (DeepTrust, Cloudflare, Proofpoint) but designed from scratch as a learning and interview project.
