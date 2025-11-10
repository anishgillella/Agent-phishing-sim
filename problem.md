# Take Home Assessment – Founding Engineer – Applied AI

## Context

GhostEye runs continuous smishing simulations to test employee security awareness. A key challenge: automated SMS messages get flagged as spam if timing patterns look robotic.

Gain access to a Twilio phone number, you will need it to send SMS messages that appear to come from a real human, not a bot. Set it up using a framework that allows you to send SMS messages. If you can't figure this part out, don't let it block you. Design the algorithm and mock the message sending part.

## Challenge

Design a system that sends SMS messages with human-realistic timing patterns.

### The Problem

- Perfect intervals (exactly 5 seconds apart) = obvious bot
- Uniform random delays (random between 1-10 sec) = still detectable pattern
- Burst then silence patterns = suspicious
- No variation in "typing time" before send = fake

Real humans typing and sending texts:

- Take varying time to compose (5-120 seconds depending on message length)
- Sometimes pause mid-message (checking facts, getting distracted)
- Send times cluster around certain patterns (on the hour, after meetings end)
- Have different "typing speeds" (words per minute varies)
- Sometimes send follow-up corrections immediately, sometimes wait

## Part 1: Jitter Algorithm

Design a message scheduling algorithm that models realistic human SMS behavior.

### Input

- Queue of messages to send
- Message content (so you know length/complexity)
- Current time
- Historical send times (to avoid patterns)

### Output

- Scheduled send time for each message
- Explanation of why this timing appears human

Your algorithm should consider:

- How long would a human take to type this message?
- Should there be "thinking pauses"?
- How do you avoid detectable patterns across multiple messages?
- What randomness makes sense vs. what's too uniform?

**Deliverable:** Pseudocode or working code (Python preferred) + brief explanation

## Part 2: AI Agents

Design a small, event-driven AI agent that packages the jitter algorithm as a tool

### Goal

- Make it as production ready as possible, telemetry with traces, evals a plus
- The agent should take actions based on certain events that are fired off at different points of the jitter algorithm
- Build to a point where it is able to automate certain workflows useful in the context of the jitter algorithm problem
- Display agent building, context engineering, agentic memory, workflow design best practices

### Constraints

- You can use any framework, or no framework, entirely up to you
- Can use any tool to write up the functioning prototype
- The point is to be able to walk us through your code and explain to us how it works and why you chose to make it work that way

### Your solution should contain

- Well documented and structured code that is easy to maintain and understand
- Clearly defined mechanism for tool calling.
- As much detail as you can find time adding, does not need to be perfect but whatever you want to show off that can add value

**Deliverable:** Working code (Python preferred) + explanation of design decisions

## Part 3: Constraints & Trade-offs

**Scenario:** You need to send 50 messages over a 6-hour workday, but they need to appear human-realistic.

### Questions

1. What's your strategy? Do you send them evenly distributed, or cluster around certain times? Why?

2. You only have 1 phone number. An employee replies to message #12. Now what? Does this affect how you schedule the remaining 38 messages?

3. What telemetry would you collect to determine if your jitter algorithm is working (i.e., messages aren't being flagged)?

4. What data structure are you using for storing logs of scheduled messages? Why this certain approach? What other approaches did you consider?

5. What services would you stitch together to pull off the scheduling mechanism? Why certain choices vs. others?

6. What is your decision making process when you decide to build in-house vs. using a service provider to to source some of the stack?

