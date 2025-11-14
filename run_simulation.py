#!/usr/bin/env python3
"""
SMS Phishing Simulation - Scenarios from problem.md Part 3

Runs different scenarios using Agent + Jitter algorithm:
- Part 3 Question 1: 50 messages to MULTIPLE users over 6-hour workday
- Part 3 Question 2: Reply handling and conversation simulation

Note: All scenarios use Agent + Jitter algorithm by default.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.sms_agent import SMSAgent
from utils.mock_sms import MockSMSSender
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("Simulation")


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_section(title: str):
    """Print a formatted section."""
    print("\n" + "-"*80)
    print(f"  {title}")
    print("-"*80)


def display_jitter_factors(scheduled_msg):
    """Display all 5 jitter algorithm factors for a message."""
    s = scheduled_msg
    if not s.jitter_details:
        return
    
    details = s.jitter_details
    
    # Factor 1: Complexity
    print(f"\n   ✓ Factor 1: MESSAGE COMPLEXITY")
    print(f"      Level: {details['complexity'].upper()}")
    
    # Factor 2: Typing Time with Thinking Pauses
    print(f"\n   ✓ Factor 2: TYPING TIME (with mid-message breaks)")
    typing_m = details.get('typing_metrics', {})
    print(f"      Words: {typing_m.get('word_count')} | WPM: {typing_m.get('actual_wpm', 0):.1f} | Pause: {'YES' if typing_m.get('has_thinking_pause') else 'NO'}")
    
    # Factor 3: Inter-message Delay
    print(f"\n   ✓ Factor 3: INTER-MESSAGE DELAY")
    delay_info = details.get('inter_message_delay', {})
    if delay_info.get('base_delay_minutes'):
        print(f"      Base: {delay_info['base_delay_minutes']:.2f}m → Actual: {delay_info['actual_delay_minutes']:.2f}m | Cluster: {delay_info['cluster_factor']:.2f}x")
    else:
        print(f"      First message - no previous delay")
    
    # Factor 4: Time Clustering
    print(f"\n   ✓ Factor 4: TIME CLUSTERING (peak hours)")
    print(f"      Applied: {delay_info.get('cluster_factor', 'N/A')} | Clustered: {'YES' if delay_info.get('is_clustered') else 'NO'}")
    
    # Factor 5: Pattern Avoidance
    print(f"\n   ✓ Factor 5: PATTERN AVOIDANCE (exponential randomness)")
    pattern_info = details.get('pattern_avoidance', {})
    print(f"      Violation: {pattern_info.get('violation_detected')} | Adjustments: {pattern_info.get('adjustment_attempts', 0)}")


def run_few_messages_scenario(agent: SMSAgent):
    """Send a few messages to test jitter algorithm with agent reasoning."""
    print_header("FEW MESSAGES SCENARIO (AGENT + JITTER)")
    recipients = ["+1234567890", "+0987654321"]
    
    # Agent decides what messages to send and schedules them
    prompt = f"""You need to send 3 SMISHING (SMS phishing) simulation messages to test the jitter algorithm.

Scenario: Send 3 SMISHING messages to test human-realistic timing patterns
Recipients: {recipients}

CRITICAL REQUIREMENTS:
1. Messages MUST be SMISHING messages (SMS phishing: security alerts, verification requests, account issues)
2. Messages must form a COHERENT SMISHING CAMPAIGN SEQUENCE
3. You MUST CALL schedule_batch tool with actual messages - do not just describe what you would do

YOUR TASK:
1. Design a coherent SMISHING message sequence:
   - Example: Initial security alert → Urgency building → Verification request
   - Messages should progress logically in a smishing campaign
   - Use SMISHING-appropriate content (security alerts, account verification, urgent actions)
   - DO NOT use casual messages like "Got it", "Perfect", "On it" - these are NOT smishing messages
2. CALL schedule_batch tool with the messages you designed
   - Pass messages as a list: [{{"content": "...", "recipient": "..."}}, ...]
   - Do NOT just describe the sequence - actually schedule the messages

SMISHING MESSAGE REQUIREMENTS:
- Must be SMISHING messages: security alerts, verification requests, account issues, urgent actions
- Must form a logical smishing campaign flow
- Each message should build on previous messages
- CRITICAL: Messages must look NATURAL and CASUAL like real SMS messages
- Avoid excessive symbols, emojis, or formatting that looks suspicious or alarming
- Use natural SMS formatting: simple text, minimal punctuation, casual tone
- Avoid: excessive exclamation marks (!!!), all caps (URGENT!!!), suspicious formatting, emojis
- Examples: "Hi, we need to verify your account. Click here: bit.ly/verify"
- NOT casual: "Got it", "Perfect", "Hey! How's it going?"
- NOT alarming: "URGENT!!!", "⚠️ VERIFY NOW!!!", excessive symbols

EXAMPLE SMISHING SEQUENCE:
1. "Hi, we need to verify your account. Click here: bit.ly/verify This is important for security."
2. "This is urgent - please verify within 24 hours. Your account has been flagged for suspicious activity."
3. "Last reminder: Account will be locked if not verified. Complete verification now."

Now design your 3-message SMISHING sequence and CALL schedule_batch tool to schedule them."""
    
    result = agent.process_request(prompt)
    
    # Extract scheduled messages from agent's scheduled_messages_by_recipient
    all_scheduled = []
    for recipient, scheduled_list in agent.scheduled_messages_by_recipient.items():
        all_scheduled.extend(scheduled_list)
    
    # Sort by scheduled time
    all_scheduled.sort(key=lambda x: x.scheduled_time)
    
    print(f"\n✅ Scheduled: {len(all_scheduled)} messages")
    print(f"\n{'='*120}")
    print("MESSAGE DETAILS WITH JITTER FACTORS")
    print(f"{'='*120}")
    
    for i, s in enumerate(all_scheduled, 1):
        print(f"\nMessage #{i} → {s.message.recipient}")
        print(f"  📩 {s.message.content}")
        print(f"  ⏰ {s.scheduled_time.strftime('%H:%M:%S')} | ⌨️ {s.typing_duration:.1f}s")
        print(f"  📊 {s.explanation}")
        display_jitter_factors(s)
    
    return all_scheduled


def run_realistic_timing_scenario(agent: SMSAgent):
    """Demonstrate realistic SMS timing patterns - focus on JITTER QUALITY not message count."""
    print_header("REALISTIC TIMING PATTERNS (8-12 MESSAGES, 2 RECIPIENTS)")
    
    recipients = ["+1234567890", "+0987654321"]
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=6)
    
    start_time_iso = start_time.isoformat()
    end_time_iso = end_time.isoformat()
    
    prompt = f"""Design a REALISTIC phishing SMS campaign that demonstrates HUMAN-LIKE TIMING PATTERNS.

FOCUS: Show quality of timing variation, NOT quantity of messages. Smaller is better to show natural patterns.

Recipients: {recipients}

CRITICAL REQUIREMENTS:
1. Send EXACTLY 8-12 messages TOTAL (not 50, not 25 - STRICT LIMIT for this demo)
2. Distribute across 2 recipients with MAXIMUM 5 messages per person (HARD LIMIT):
   - Option A: 6 messages to first, 4-6 to second = 10-12 total
   - Option B: 5 messages to each = 10 total
   - Option C: 4 messages to first, 4-5 to second = 8-9 total
   - MUST NOT EXCEED 6 per recipient
3. Messages MUST be SMISHING: security alerts, verification requests, account threats
4. ONE COHERENT CAMPAIGN THREAD per recipient - Alert → Urgency → Verification

JITTER ALGORITHM CHALLENGE - Show realistic human patterns:
✓ TYPING TIME VARIATION:
  - Simple messages (short) = fast typing (15-30 seconds)
  - Complex messages (long) = slow typing (60-120 seconds)
  - Some messages have pauses mid-typing (human distraction)
  
✓ INTER-MESSAGE TIMING:
  - NOT uniform intervals (that's robotic)
  - Burst pattern: 2-3 quick replies in 5-10 minutes (human thinking fast)
  - Then silence: 15-30 minute gap (human doing other things)
  - Then another burst
  
✓ TIME-OF-DAY CLUSTERING:
  - Morning cluster (9-11 AM): intense activity
  - Midday lull (11 AM-1 PM): fewer messages
  - Afternoon burst (1-3 PM): renewed urgency

✓ PSYCHOLOGICAL PATTERNS:
  - Start gentle (Alert)
  - Escalate urgency (Follow-up)
  - Add deadline pressure (Final notice)
  - Create FOMO (last chance message)

YOUR TASK:
1. Use generate_messages tool to create 8-12 SMISHING messages:
   - Distribute as 4-6 per recipient (YOUR CHOICE - not uniform)
   - Ensure coherent campaign flow per recipient
   - Include typing complexity variation
   
2. Use schedule_batch to schedule with natural timing:
   - Show burst + silence patterns
   - Vary typing times based on complexity
   - Cluster around morning/afternoon peaks
   
3. EXPLAIN your reasoning for:
   - Why specific messages have specific typing times
   - Why inter-message gaps vary (burst vs silence)
   - How this timing pattern mimics human behavior
   - Why this would NOT be detected as bot activity

VALIDATION CHECKLIST (MUST COMPLETE BEFORE RETURNING):
✓ Total messages: 8-12 (NOT 25, NOT 50)
✓ Recipient 1: Maximum 6 messages (HARD LIMIT)
✓ Recipient 2: Maximum 6 messages (HARD LIMIT)
✓ Each recipient gets ONE coherent campaign thread
✓ Typing times vary: Simple (15-30s), Complex (60-120s)
✓ Inter-message gaps vary: Bursts (2-3 in 5-10 min), Silence (15-30 min)
✓ Time clustering: Morning peak, midday lull, afternoon peak

The goal: Demonstrate that SMALL campaigns with GREAT timing > LARGE campaigns with uniform timing."""
    
    result = agent.process_request(prompt)
    
    # Extract scheduled messages
    all_scheduled = []
    for r in recipients:
        scheduled_list = agent.scheduled_messages_by_recipient.get(r, [])
        all_scheduled.extend(scheduled_list)
    all_scheduled.sort(key=lambda x: x.scheduled_time)
    
    print(f"\n✅ Total: {len(all_scheduled)} messages")
    for r in recipients:
        count = len(agent.scheduled_messages_by_recipient.get(r, []))
        print(f"   {r}: {count} messages")
    
    print(f"\n{'='*120}")
    print("CAMPAIGN TIMELINE WITH JITTER FACTORS")
    print(f"{'='*120}")
    
    prev_time = None
    prev_recipient = None
    
    for i, s in enumerate(all_scheduled, 1):
        gap_str = "NEW" if not prev_time or prev_recipient != s.message.recipient else f"{(s.scheduled_time - prev_time).total_seconds()/60:.1f}m"
        print(f"\n[{i:2d}] {s.scheduled_time.strftime('%H:%M')} → {s.message.recipient} | Gap: {gap_str} | Type: {s.typing_duration:.0f}s")
        print(f"     {s.message.content}")
        display_jitter_factors(s)
        
        prev_time = s.scheduled_time
        prev_recipient = s.message.recipient
    
    # Pattern analysis
    print(f"\n{'='*120}")
    print("PATTERN ANALYSIS")
    print(f"{'='*120}")
    
    bursts = []
    current_burst = [all_scheduled[0]]
    for i in range(1, len(all_scheduled)):
        gap = (all_scheduled[i].scheduled_time - all_scheduled[i-1].scheduled_time).total_seconds() / 60
        if gap < 15 and all_scheduled[i].message.recipient == all_scheduled[i-1].message.recipient:
            current_burst.append(all_scheduled[i])
        else:
            bursts.append(current_burst)
            current_burst = [all_scheduled[i]]
    bursts.append(current_burst)
    
    typing_times = [s.typing_duration for s in all_scheduled]
    total_duration = (all_scheduled[-1].scheduled_time - all_scheduled[0].scheduled_time).total_seconds() / 60
    
    print(f"\nBurst Clusters: {len(bursts)}")
    for idx, burst in enumerate(bursts, 1):
        duration = (burst[-1].scheduled_time - burst[0].scheduled_time).total_seconds() / 60
        print(f"  Burst {idx}: {len(burst)} messages in {duration:.1f}m")
    
    print(f"\nTyping Variation: {min(typing_times):.0f}s → {max(typing_times):.0f}s (Avg: {sum(typing_times)/len(typing_times):.0f}s)")
    print(f"Total Duration: {total_duration:.1f} minutes")
    print(f"\n✓ Human-realistic: Bursts + silence + varied typing + non-uniform gaps")
    
    return all_scheduled


def run_multiple_users_scenario(agent: SMSAgent):
    """Part 3 Question 1: 50 messages to MULTIPLE users (12 recipients, max 5 messages each)."""
    print_header("50 MESSAGES TO 12 RECIPIENTS (CLUSTERED DISTRIBUTION)")
    
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=6)
    recipients = [
        "+1111111111", "+2222222222", "+3333333333", "+4444444444", "+5555555555",
        "+6666666666", "+7777777777", "+8888888888", "+9999999999", "+1010101010",
        "+1111121111", "+1212121212"
    ]
    
    print(f"\n⏰ {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} | 👥 {len(recipients)} recipients")
    start_time_iso = start_time.isoformat()
    end_time_iso = end_time.isoformat()
    
    prompt = f"""You need to send EXACTLY 50 phishing simulation messages over a 6-hour workday window (9 AM to 3 PM).

CRITICAL GOAL: Design timing patterns that are UNDETECTABLE as phishing AND ensure sender is NOT flagged.

Recipients: {recipients}

CRITICAL ANTI-DETECTION STRATEGY:
- 12 DIFFERENT PHONE NUMBERS (avoid concentrating on 3 recipients - that flags as smishing source)
- MAXIMUM 5 messages PER RECIPIENT - HARD LIMIT (agent decides 3-5 per recipient - some get 3, some get 5-6)
- Varied timing per recipient (no synchronized patterns across numbers)
- Different content per recipient (not mass-sent template copies)
- VALIDATE: No recipient should exceed 5 messages

CRITICAL REQUIREMENTS:
1. Messages MUST be SMISHING messages (SMS phishing with psychological manipulation)
2. ONE COHERENT CAMPAIGN THREAD per recipient (not 5 different angles to same person)
3. Messages must create natural flow: Alert → Urgency → Verification → Deadline → Follow-up
4. Complexity: 20% SIMPLE (10 messages), 60% MEDIUM (30 messages), 20% COMPLEX (10 messages)
5. MUST generate and schedule EXACTLY 50 messages total (distributed variably: 3-5 per recipient as agent decides)
6. Include realistic links (bit.ly/verify, verify-account-now.com) and timestamps
7. Psychological tactics: scarcity (24-hour window), urgency (act NOW), authority (security team), fear (account lock)
8. CRITICAL: Ensure sender NOT flagged as smishing - vary content, timing, and avoid mass patterns

YOUR TASK:
1. Use generate_messages tool to create EXACTLY 50 messages:
   - One coherent campaign thread per recipient
   - Natural progression per recipient (not random)
   - Complexity distribution: 10 simple, 30 medium, 10 complex
   - Realistic phishing links and timestamps
   - Psychologically manipulative language
   
2. CALL schedule_batch tool to schedule ALL 50 messages with strategic time window reasoning
   - Do NOT schedule fewer than 50 - validate count before scheduling

TIME WINDOW STRATEGY (6-hour workday 9 AM - 3 PM):

Mathematical Analysis:
- Total: 50 messages across 6 hours and 12 recipients
- Per recipient: 3-6 messages (agent decides - varies to avoid pattern)
- Average: ~4.5 messages/recipient, ~8.3 messages/hour total
- KEY: Distribute across recipients to avoid sender fingerprinting

Anti-Detection Strategy (Why spreading across 11 numbers is critical):
1. SENDER ANONYMIZATION:
   - 11 different phone numbers ≠ single smishing source
   - Monitoring tools can't correlate messages to one attacker
   - Each recipient sees independent campaign (not mass-broadcast)

2. MESSAGE DISTRIBUTION (3-5 per recipient, agent decides):
   - Recipient A: 5 messages spread 10:00-14:30 (morning + afternoon)
   - Recipient B: 3 messages spread 09:15-13:45 (shorter campaign)
   - Recipient C: 6 messages spread 09:30-14:50 (longer campaign)
   - Each recipient gets DIFFERENT timing profile (not synchronized)

3. TIMING VARIATION PER RECIPIENT (Prevents clustering detection):
   - Not all recipients get morning cluster
   - Not all recipients get afternoon cluster
   - Some get midday messages, others don't
   - Creates illusion of independent, human-like campaigns

Time Window Reasoning for Anti-Detection:
✓ Clustered distribution (NOT uniform) = looks human (humans cluster around natural work rhythms)
✓ Two peaks (9-11 AM, 1-3 PM) = mimics human attention patterns
✓ Valley at midday = respects natural break times
✓ Varied delays within clusters = prevents robotic patterns
✓ Total in 6-hour window = fits natural work hours

Why "Even Distribution" Would Be DETECTED as Bot:
✗ Perfect intervals (e.g., every 7 minutes) = robotic
✗ Same messages per hour = unnatural
✗ No clustering = no human work rhythm
✗ Would raise immediate red flag for security tools

GENERATE MESSAGES with:
- SMISHING focus: security alerts, verification requests, account threats
- ONE thread per recipient: Alert → Build urgency → Request verification → Deadline → Follow-up
- Realistic context: Timestamps (2025-11-13 14:32 UTC), locations (Shanghai, Moscow, Lagos), links
- Psychological techniques: Scarcity ("24 hours"), Urgency ("NOW"), Authority ("Security Team"), Fear ("Account locked")
- Natural language: NO emojis in security alerts, realistic corporate tone

SCHEDULE MESSAGES with parameters:
- start_time: "{start_time_iso}" (9 AM)
- end_time: "{end_time_iso}" (3 PM)
- enforce_time_window: true
- distribution_mode: "clustered"
- max_messages_per_hour: 10 (allows natural clustering: 3-5 in valley, 15+ in peaks)

YOUR EXPLANATION MUST INCLUDE:
1. ✓ Exact count: 50 messages confirmed
2. ✓ Distribution by hour showing clusters at 9-11 AM and 1-3 PM
3. ✓ Time window reasoning: Why clustering at these specific times mimics human behavior
4. ✓ Anti-detection strategy: Why "clustered" is better than "even"
5. ✓ Messages per hour reasoning: Why max_messages_per_hour=10 is realistic
6. ✓ Psychological techniques used in messages
7. ✓ Campaign flow per recipient: Alert → Urgency → Verification → Deadline → Follow-up

FINAL VALIDATION:
- Total messages scheduled: MUST be 50 (not 28, not 40, EXACTLY 50)
- Per-recipient MAX: NO recipient should have more than 6 messages (HARD LIMIT - VALIDATE THIS!)
- Distribution: Morning cluster + midday valley + afternoon cluster
- Per recipient: One coherent thread, not random messages
- Complexity: ~10 simple, ~30 medium, ~10 complex
- Timing: All within 9 AM - 3 PM window
- Messages: Realistic links, timestamps, psychological manipulation

The jitter algorithm will provide timing explanations. Review and confirm anti-detection strategy accounts for clustering, complexity, and psychological manipulation."""
    
    result = agent.process_request(prompt)
    
    # Extract scheduled messages
    all_scheduled = []
    for recipient, scheduled_list in agent.scheduled_messages_by_recipient.items():
        all_scheduled.extend(scheduled_list)
    all_scheduled.sort(key=lambda x: x.scheduled_time)
    
    print(f"\n✅ Scheduled: {len(all_scheduled)} messages")
    
    # Show distribution by hour
    messages_by_hour = {}
    for s in all_scheduled:
        messages_by_hour[s.scheduled_time.hour] = messages_by_hour.get(s.scheduled_time.hour, 0) + 1
    print(f"📊 Distribution: {' | '.join([f'{h:02d}:00 ({messages_by_hour[h]})' for h in sorted(messages_by_hour.keys())])}")
    
    print(f"\n{'='*120}")
    print("MESSAGES BY RECIPIENT")
    print(f"{'='*120}")
    
    # Group messages by recipient
    messages_by_recipient = {}
    for s in all_scheduled:
        recipient = s.message.recipient
        if recipient not in messages_by_recipient:
            messages_by_recipient[recipient] = []
        messages_by_recipient[recipient].append(s)
    
    # Sort messages within each recipient group by scheduled time
    for recipient in messages_by_recipient:
        messages_by_recipient[recipient].sort(key=lambda x: x.scheduled_time)
    
    # Display grouped by recipient
    for recipient in sorted(messages_by_recipient.keys()):
        recipient_messages = messages_by_recipient[recipient]
        print(f"\n{'='*120}")
        print(f"👤 RECIPIENT: {recipient} ({len(recipient_messages)} messages)")
        print(f"{'='*120}")
        
        prev_time = None
        for i, s in enumerate(recipient_messages, 1):
            gap_str = "NEW" if not prev_time else f"{(s.scheduled_time - prev_time).total_seconds()/60:.1f}m"
            print(f"\n[{i}] {s.scheduled_time.strftime('%H:%M')} | Gap: {gap_str} | Type: {s.typing_duration:.0f}s")
            print(f"    {s.message.content}")
            display_jitter_factors(s)
            prev_time = s.scheduled_time
    
    return all_scheduled


def run_reply_handling_scenario(agent: SMSAgent):
    """Reply handling: 50 messages to 1 recipient, reply at message #12."""
    print_header("REPLY HANDLING (50 MESSAGES, PAUSE & RESCHEDULE AT #12)")
    
    recipient = "+1234567890"
    print(f"\n👤 Recipient: {recipient}")
    
    prompt = f"""You need to schedule EXACTLY 50 phishing simulation messages to a single recipient: {recipient}

CRITICAL REQUIREMENTS:
1. Messages MUST be SMISHING messages (SMS phishing: security alerts, verification requests, account issues)
2. Messages must form a COHERENT SMISHING CAMPAIGN SEQUENCE
3. You MUST call schedule_batch tool - do not just describe what you would do

YOUR TASK:
1. Check conversation history context provided - see what messages were already sent to this recipient
2. Design a coherent 50-message SMISHING campaign sequence:
   - IMPORTANT: NOT every message should be a follow-up - mix follow-ups with NEW campaign messages
   - Example: Send 2-3 follow-up messages, then start a NEW campaign thread, then more follow-ups, etc.
   - This creates natural variety: some messages build on previous ones, others start new campaign threads
   - Messages should progress logically: Initial security alert → Follow-up → NEW campaign (account lock) → Follow-up → NEW campaign (verification)
   - Each message should make sense, but not every message needs to reference previous ones
   - Think: "What sequence would a real SMISHING campaign use? Multiple campaign threads, not just one continuous follow-up chain"
3. Use generate_messages tool to create SMISHING messages:
   - Provide previous_messages_context parameter with conversation history for this recipient
   - The tool will automatically mix follow-ups (30%) with new campaign messages (70%)
   - Ensure messages form coherent campaign sequences with variety
   - MUST generate exactly 50 messages
4. CALL schedule_batch tool to schedule ALL 50 messages with natural timing patterns
   - Do NOT schedule only a few messages - schedule the FULL 50 messages requested

SMISHING MESSAGE REQUIREMENTS:
- Must be SMISHING messages: security alerts, account verification, urgent actions
- Messages must form a logical smishing campaign flow (not random standalone messages)
- Each message should build on previous messages or advance the smishing campaign
- Avoid casual messages like "Got it", "Perfect", "On it" - these are NOT smishing messages
- Consider: Opening security alert → Urgency → Verification request → Follow-up → Escalation
- CRITICAL: Messages must look NATURAL and CASUAL like real SMS messages
- Avoid excessive symbols, emojis, or formatting that looks suspicious or alarming
- Use natural SMS formatting: simple text, minimal punctuation, casual tone
- Avoid: excessive exclamation marks (!!!), all caps (URGENT!!!), suspicious formatting, emojis
- Keep messages looking like they come from a real person, not a bot

All messages go to the same recipient. Use natural timing patterns - vary delays between messages, consider message complexity for typing time, and ensure timing looks human-realistic. Avoid patterns that look robotic.

Explain your reasoning for:
- What message sequence you designed and why it's coherent
- How messages progress to form a phishing campaign narrative
- The timing strategy for scheduling them"""
    
    result = agent.process_request(prompt)
    
    # Extract scheduled messages
    all_scheduled = []
    for r, scheduled_list in agent.scheduled_messages_by_recipient.items():
        if r == recipient:
            all_scheduled.extend(scheduled_list)
    all_scheduled.sort(key=lambda x: x.scheduled_time)
    
    print(f"\n✅ Scheduled: {len(all_scheduled)} messages")
    
    # Show first 12 messages before reply
    print(f"\n{'='*120}")
    print("FIRST 12 MESSAGES (BEFORE REPLY)")
    print(f"{'='*120}")
    
    prev_time = None
    for i, s in enumerate(all_scheduled[:12], 1):
        gap_str = "NEW" if not prev_time else f"{(s.scheduled_time - prev_time).total_seconds()/60:.1f}m"
        print(f"\n[{i:2d}] {s.scheduled_time.strftime('%H:%M')} | Gap: {gap_str}")
        print(f"     {s.message.content}")
        display_jitter_factors(s)
        prev_time = s.scheduled_time
    
    # Simulate reply
    print(f"\n{'='*120}")
    print("EMPLOYEE REPLY RECEIVED AT MESSAGE #12")
    print(f"{'='*120}")
    
    remaining_before = len(all_scheduled) - 12  # Total messages minus 12 already sent
    print(f"\nState BEFORE: 12 sent, {remaining_before} remaining scheduled")
    print(f"Reply: 'Yes, I'll verify now' at {datetime.now().strftime('%H:%M:%S')}")
    
    # Trigger reply handling
    agent.receive_reply(
        recipient=recipient,
        reply_content="Yes, I'll verify now",
        original_message_id=all_scheduled[11].message.original_message_id
    )
    
    # Show state after reply
    remaining_messages = agent.scheduled_messages_by_recipient.get(recipient, [])
    rescheduled_count = remaining_before  # All remaining messages get rescheduled
    
    print(f"\n{'='*120}")
    print("STATE AFTER REPLY HANDLING")
    print(f"{'='*120}")
    print(f"\n✅ Actions:")
    print(f"   • Paused: {rescheduled_count} messages")
    print(f"   • Immediate reply: 1 message scheduled")
    print(f"   • Rescheduled: {rescheduled_count} messages with extended delays")
    
    print(f"\n📊 Stats: 50 total | 12 sent | {rescheduled_count} paused & rescheduled")
    
    # Show first 10 rescheduled messages
    if len(remaining_messages) > 0:
        print(f"\n{'='*120}")
        print(f"RESCHEDULED MESSAGES (First 10 of {len(remaining_messages)})")
        print(f"{'='*120}")
        
        prev_time = None
        for i, s in enumerate(remaining_messages[:10], 13):
            gap_str = "NEW" if not prev_time else f"{(s.scheduled_time - prev_time).total_seconds()/60:.1f}m"
            print(f"\n[{i:2d}] {s.scheduled_time.strftime('%H:%M')} | Gap: {gap_str}")
            print(f"     {s.message.content}")
            display_jitter_factors(s)
            prev_time = s.scheduled_time
        
        if len(remaining_messages) > 10:
            print(f"\n... and {len(remaining_messages) - 10} more")
    
    return all_scheduled




def main():
    """Run selected scenarios from problem.md based on command-line flags."""
    parser = argparse.ArgumentParser(
        description="GhostEye SMS Phishing Simulator - Run specific scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_simulation.py --all                    # Run all scenarios (default)
  python run_simulation.py --few-messages           # Send a few messages
  python run_simulation.py --multiple-users        # 50 messages to multiple users
  python run_simulation.py --reply-handling        # Handle reply from employee
  python run_simulation.py --conversation-simulation  # Simulate conversation with LLM employee
  
Note: All scenarios use Agent + Jitter algorithm. Agent provides reasoning for each message timing decision.
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios (default if no flags specified)"
    )
    parser.add_argument(
        "--few-messages",
        action="store_true",
        dest="few",
        help="Send a few messages to test jitter algorithm"
    )
    parser.add_argument(
        "--multiple-users",
        action="store_true",
        dest="multiple",
        help="Part 3 Q1: 50 messages to MULTIPLE users over 6-hour workday"
    )
    parser.add_argument(
        "--reply-handling",
        action="store_true",
        dest="reply",
        help="Part 3 Q2: Handle reply from employee (pause, respond, reschedule)"
    )
    parser.add_argument(
        "--realistic-timing",
        action="store_true",
        dest="timing",
        help="Demo: Realistic SMS timing patterns (8-12 messages to 2 recipients)"
    )
    
    args = parser.parse_args()
    
    # Determine which scenarios to run
    # If no flags specified, default to --all
    run_all = args.all or not any([args.few, args.multiple, args.reply, args.timing])
    
    scenarios_to_run = {
        "few": run_all or args.few,
        "multiple": run_all or args.multiple,
        "reply": run_all or args.reply,
        "timing": run_all or args.timing,
    }
    
    print_header("GHOSTEYE SMS PHISHING SIMULATOR")
    
    # Show which scenarios will run
    selected = [name for name, run in scenarios_to_run.items() if run]
    print(f"\n📋 Selected scenarios: {', '.join(selected) if selected else 'None'}")
    if not selected:
        print("❌ No scenarios selected. Use --help to see available options.")
        sys.exit(1)
    
    # Initialize
    print_section("INITIALIZATION")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found")
        print("   Set it in .env file or environment variable")
        sys.exit(1)
    
    print(f"✅ OpenRouter API key configured")
    
    # Initialize agent with LLM event handling enabled
    print("\n🤖 Initializing SMS Agent...")
    try:
        agent = SMSAgent(
            openrouter_api_key=openrouter_key,
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            logfire_api_key=os.getenv("LOGFIRE_API_KEY"),
            enable_llm_event_handling=True
        )
        print("✅ Agent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        logger.error(f"Agent initialization failed: {e}")
        sys.exit(1)
    
    # Initialize mock SMS sender
    sms_sender = MockSMSSender()
    print("✅ Mock SMS sender initialized")
    
    # Run selected scenarios
    try:
        few_scheduled = None
        multiple_scheduled = None
        reply_scheduled = None
        timing_scheduled = None
        
        if scenarios_to_run["few"]:
            few_scheduled = run_few_messages_scenario(agent)
        
        if scenarios_to_run["timing"]:
            timing_scheduled = run_realistic_timing_scenario(agent)
        
        if scenarios_to_run["multiple"]:
            multiple_scheduled = run_multiple_users_scenario(agent)
        
        if scenarios_to_run["reply"]:
            reply_scheduled = run_reply_handling_scenario(agent)
        
        # Summary
        print_header("SIMULATION COMPLETE")
        
        print("\n📊 Summary:")
        if few_scheduled is not None:
            print(f"   Few Messages: {len(few_scheduled)} messages scheduled")
        if timing_scheduled is not None:
            print(f"   Realistic Timing: {len(timing_scheduled)} messages with human-like patterns")
        if multiple_scheduled is not None:
            print(f"   Multiple Users (50 messages): {len(multiple_scheduled)} messages scheduled")
        if reply_scheduled is not None:
            print(f"   Reply Handling: Handled reply and rescheduled remaining messages")
        
        # Telemetry
        telemetry = agent.get_telemetry()
        metrics = telemetry.get("metrics", {})
        
        print(f"\n📈 Telemetry:")
        print(f"   Messages queued: {metrics.get('messages_queued', 0)}")
        print(f"   Messages scheduled: {metrics.get('messages_scheduled', 0)}")
        print(f"   Pattern violations detected: {metrics.get('pattern_violations', 0)}")
        print(f"   Agent decisions made: {len([m for m in agent.memory if m.get('type', '').startswith('agent_')])}")
        
        token_usage = telemetry.get("token_usage", {})
        if token_usage:
            print(f"\n💰 Token Usage:")
            print(f"   Total tokens: {token_usage.get('total_tokens', 0):,}")
            print(f"   Total cost: ${token_usage.get('total_cost_usd', 0):.6f} USD")
        
        print("\n✅ All scenarios completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Simulation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
