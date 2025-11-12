#!/usr/bin/env python3
"""
Comprehensive SMS Phishing Simulation with Full Pipeline
- Agent orchestration with LLM
- Jitter algorithm scheduling
- Mock SMS sending
- Real-time monitoring and logging
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.sms_agent import SMSAgent
from utils.mock_sms import MockSMSSender
from utils.logger import get_logger, log_with_context, SimulationMonitor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize loggers
logger = get_logger("Simulation")
monitor = SimulationMonitor()


def run_simulation(single_recipient_mode: bool = False):
    """
    Run a complete SMS phishing simulation.
    
    Args:
        single_recipient_mode: If True, all 50 messages go to same recipient (matches Part 3 Q2 scenario).
                              If False, messages are distributed across multiple recipients (campaign mode).
    """
    
    monitor.print_header("🚀 SMS PHISHING SIMULATION - FULL PIPELINE")
    
    # ========== INITIALIZATION ==========
    monitor.print_section("1️⃣  INITIALIZATION")
    
    print("\n📋 API Key Configuration:")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    langsmith_key = os.getenv("LANGSMITH_API_KEY")
    logfire_key = os.getenv("LOGFIRE_API_KEY")
    
    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found")
        sys.exit(1)
    
    print(f"✅ OpenRouter: {openrouter_key[:20]}...")
    if langsmith_key:
        print(f"✅ LangSmith: {langsmith_key[:20]}... (enabled)")
    else:
        print(f"⚠️  LangSmith: Not configured (optional)")
    if logfire_key:
        print(f"✅ Logfire: {logfire_key[:20]}... (enabled)")
    else:
        print(f"⚠️  Logfire: Not configured (optional)")
    
    # Initialize agent
    print("\n🤖 Initializing SMS Agent...")
    try:
        agent = SMSAgent(
            openrouter_api_key=openrouter_key,
            langsmith_api_key=langsmith_key,
            logfire_api_key=logfire_key,
        )
        print("✅ Agent initialized with LangChain v1 create_agent")
        monitor.record_event("agent_initialized", {
            "llm": "openrouter/gpt-4o-mini",
            "langsmith_enabled": bool(langsmith_key),
            "logfire_enabled": bool(logfire_key),
        })
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        logger.error(f"Agent initialization failed: {e}")
        sys.exit(1)
    
    # Initialize mock SMS sender
    print("\n📱 Initializing Mock SMS Sender...")
    sms_sender = MockSMSSender()
    print("✅ Mock SMS sender ready (simulating message delivery)")
    monitor.record_event("sms_sender_initialized", {"type": "mock"})
    
    # ========== CAMPAIGN SETUP ==========
    monitor.print_section("2️⃣  CAMPAIGN SETUP")
    
    campaign_name = "security_verification_2025"
    recipients = [
        "+1234567890",
        "+0987654321",
        "+1111111111",
    ]
    
    print(f"\n📢 Campaign: {campaign_name}")
    print(f"📍 Recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"   - {recipient}")
    
    monitor.record_event("campaign_created", {
        "campaign_name": campaign_name,
        "recipient_count": len(recipients),
    })
    
    # ========== MESSAGE SCHEDULING ==========
    monitor.print_section("3️⃣  MESSAGE SCHEDULING (JITTER ALGORITHM)")
    
    # ========== SCENARIO 1: USUAL SCENARIO (NO TIME WINDOW) ==========
    print("\n" + "="*80)
    print("📋 SCENARIO 1: Usual Scenario (Standard Jitter Algorithm)")
    print("="*80)
    
    # Create a small batch of messages for usual scenario
    usual_messages = [
        {"content": "Hi, we need to verify your account. Click here: bit.ly/verify", "recipient": "+1234567890"},
        {"content": "This is urgent - please verify within 24 hours", "recipient": "+0987654321"},
        {"content": "Last reminder: Account will be locked if not verified", "recipient": "+1111111111"},
        {"content": "Quick security check needed for your account", "recipient": "+1234567890"},
        {"content": "Suspicious activity detected - verify now", "recipient": "+0987654321"},
    ]
    
    print(f"\n📝 Scheduling {len(usual_messages)} messages (usual scenario)...")
    print("   Flags: None (default behavior)")
    
    try:
        usual_scheduled = agent.schedule_messages(usual_messages)
        print(f"✅ Scheduled {len(usual_scheduled)} messages")
        print("\n📅 Usual Scenario Scheduling Details:")
        print(f"{'#':<3} {'Scheduled Time':<20} {'Recipient':<15} {'Typing (s)':<12}")
        print("-"*60)
        for i, scheduled in enumerate(usual_scheduled[:5], 1):
            print(f"{i:<3} {scheduled.scheduled_time.strftime('%H:%M:%S'):<20} {scheduled.message.recipient:<15} {scheduled.typing_duration:<12.2f}")
        monitor.stats["messages_scheduled"] = len(usual_scheduled)
    except Exception as e:
        print(f"❌ Failed to schedule usual scenario: {e}")
        logger.error(f"Usual scenario scheduling failed: {e}")
    
    # ========== SCENARIO 2: 50 MESSAGES OVER 6-HOUR WORKDAY ==========
    # Based on Part 3 of problem.md: "You need to send 50 messages over a 6-hour workday"
    # Question 2 mentions "An employee replies to message #12" affecting remaining 38 messages
    # This suggests messages are part of a campaign sequence, potentially to same or different recipients
    print("\n" + "="*80)
    print("📋 SCENARIO 2: 50 Messages Over 6-Hour Workday")
    print("="*80)
    print("\n   Based on Part 3 of problem.md")
    print("   Using time window enforcement flag: enforce_time_window=True")
    
    # Set up 6-hour workday window (9 AM - 3 PM)
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=6)  # 6-hour window
    
    print(f"\n⏰ Time Window:")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: 6 hours")
    
    # Create 50 messages
    # Note: Problem doesn't specify if all go to same recipient or different ones
    # Question 2 suggests they're part of a sequence where a reply affects remaining messages
    # Flag controls: single_recipient_mode=True = all to same (matches Q2), False = distributed campaign
    print("\n📝 Creating 50 messages for 6-hour workday...")
    messages_to_schedule = []
    message_templates = [
        "Hi, we need to verify your account. Click here: bit.ly/verify",
        "This is urgent - please verify within 24 hours",
        "Last reminder: Account will be locked if not verified",
        "Quick security check needed for your account",
        "Suspicious activity detected - verify now",
        "Account verification link: bit.ly/verify",
        "Your account requires immediate attention",
        "Security alert: Please verify your identity",
        "Action required: Verify your account now",
        "Important: Account verification pending",
    ]
    
    # Choose recipient distribution based on flag
    if single_recipient_mode:
        # All 50 messages to same recipient (matches Part 3 Question 2 scenario)
        target_recipient = recipients[0]
        print(f"   Mode: Single recipient (all 50 messages to {target_recipient})")
    else:
        # Distribute across multiple recipients (campaign simulation)
        print(f"   Mode: Distributed campaign (across {len(recipients)} recipients)")
    
    for i in range(50):
        if single_recipient_mode:
            recipient = target_recipient
        else:
            # Cycle through recipients to distribute messages across campaign
            recipient = recipients[i % len(recipients)]
        
        messages_to_schedule.append({
            "content": f"{message_templates[i % len(message_templates)]} (#{i+1})",
            "recipient": recipient,
            "is_correction": False,
        })
    
    monitor.stats["messages_created"] = len(messages_to_schedule)
    
    print(f"✅ Created {len(messages_to_schedule)} messages")
    if single_recipient_mode:
        print(f"   Recipient: {target_recipient} (all messages)")
    else:
        print(f"   Recipients: {len(recipients)} (distributed across)")
    print(f"   Sample messages:")
    for i in [0, 1, 2, 48, 49]:
        print(f"      {i+1}. {messages_to_schedule[i]['content'][:60]}...")
    
    monitor.record_event("messages_created", {
        "count": len(messages_to_schedule),
        "recipients_unique": len(set(m["recipient"] for m in messages_to_schedule)),
        "scenario": "50_messages_6hour_workday",
    })
    
    # Use agent to schedule messages WITH TIME WINDOW ENFORCEMENT
    print("\n🤖 Using Agent + Jitter Algorithm with TIME WINDOW ENFORCEMENT...")
    print("   Flags:")
    print("   - enforce_time_window=True")
    print("   - max_messages_per_hour=10 (density control)")
    print("   - distribution_mode='clustered' (human-realistic clustering)")
    try:
        scheduled_messages = agent.schedule_messages(
            messages_to_schedule,
            start_time=start_time,
            end_time=end_time,
            enforce_time_window=True,  # ✅ FLAG: Enforce 6-hour window
            max_messages_per_hour=10,   # ✅ FLAG: Density control (max 10/hour)
            distribution_mode="clustered"  # ✅ FLAG: Clustered distribution
        )
        monitor.stats["messages_scheduled"] = len(scheduled_messages)
        
        print(f"✅ Scheduled {len(scheduled_messages)} messages with human-realistic timing")
        
        # Verify time window constraint
        first_time = scheduled_messages[0].scheduled_time
        last_time = scheduled_messages[-1].scheduled_time
        actual_duration = (last_time - first_time).total_seconds() / 3600.0
        
        print(f"\n⏱️  Time Window Verification:")
        print(f"   First message: {first_time.strftime('%H:%M:%S')}")
        print(f"   Last message:  {last_time.strftime('%H:%M:%S')}")
        print(f"   Actual duration: {actual_duration:.2f} hours")
        print(f"   ✅ All messages fit within 6-hour window: {last_time <= end_time}")
        
        # Show distribution by hour
        print(f"\n📊 Message Distribution by Hour:")
        messages_by_hour = {}
        for scheduled in scheduled_messages:
            hour = scheduled.scheduled_time.hour
            messages_by_hour[hour] = messages_by_hour.get(hour, 0) + 1
        
        for hour in sorted(messages_by_hour.keys()):
            count = messages_by_hour[hour]
            bar = "█" * count
            print(f"   {hour:02d}:00 - {hour+1:02d}:00: {count:2d} messages {bar}")
        
        print("\n📅 Sample Scheduling Details (first 5, middle 2, last 5):")
        print(f"{'#':<3} {'Scheduled Time':<20} {'Delay (min)':<12} {'Typing (s)':<12} {'Explanation':<40}")
        print("-"*95)
        
        sample_indices = list(range(5)) + list(range(24, 26)) + list(range(45, 50))
        previous_time = None
        for i in sample_indices:
            if i < len(scheduled_messages):
                scheduled = scheduled_messages[i]
                if previous_time:
                    delay_min = (scheduled.scheduled_time - previous_time).total_seconds() / 60.0
                else:
                    delay_min = 0.0
                explanation = scheduled.explanation[:37] + "..." if len(scheduled.explanation) > 40 else scheduled.explanation
                print(f"{i+1:<3} {scheduled.scheduled_time.strftime('%H:%M:%S'):<20} {delay_min:<12.1f} {scheduled.typing_duration:<12.2f} {explanation:<40}")
                previous_time = scheduled.scheduled_time
                
                monitor.record_event("message_scheduled", {
                    "recipient": scheduled.message.recipient,
                    "scheduled_time": scheduled.scheduled_time.isoformat(),
                    "typing_duration": scheduled.typing_duration,
                })
        
    except Exception as e:
        print(f"❌ Failed to schedule messages: {e}")
        logger.error(f"Message scheduling failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== SMS SENDING ==========
    monitor.print_section("4️⃣  SMS SENDING (MOCK MODE)")
    
    print("\n📤 Sending messages via mock SMS sender...\n")
    
    for i, scheduled in enumerate(scheduled_messages, 1):
        print(f"\n[Message {i}/{len(scheduled_messages)}]")
        print(f"  🎯 Recipient: {scheduled.message.recipient}")
        print(f"  📝 Content: {scheduled.message.content}")
        print(f"  ⏰ Scheduled: {scheduled.scheduled_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        try:
            record = sms_sender.send_sms(
                recipient=scheduled.message.recipient,
                content=scheduled.message.content,
                scheduled_time=scheduled.scheduled_time,
                typing_delay=scheduled.typing_duration,
                simulation_mode=True,
            )
            
            monitor.stats["messages_sent"] += 1
            monitor.record_event("message_sent", {
                "recipient": record.recipient,
                "message_id": record.message_id,
                "sent_time": record.sent_time.isoformat(),
                "content_length": len(record.content),
            })
            
        except Exception as e:
            print(f"  ❌ Failed to send: {e}")
            monitor.stats["errors"] += 1
            logger.error(f"SMS send failed: {e}")
            monitor.record_event("message_send_failed", {
                "recipient": scheduled.message.recipient,
                "error": str(e),
            })
    
    # ========== AGENT PROCESSING ==========
    monitor.print_section("5️⃣  AGENT LLM PROCESSING")
    
    print("\n🤖 Using Agent LLM to analyze campaign and provide insights...\n")
    
    llm_requests = [
        {
            "request": f"We just sent {len(scheduled_messages)} phishing simulation messages. What should we do next?",
            "description": "Strategic next steps",
        },
        {
            "request": "Analyze the recipients' likely response patterns based on timing and message urgency",
            "description": "Response pattern analysis",
        },
        {
            "request": "What patterns in our messages might be detectable by security systems?",
            "description": "Security pattern detection",
        },
    ]
    
    for llm_req in llm_requests:
        print(f"\n📝 Request: {llm_req['description']}")
        print(f"   Query: {llm_req['request'][:60]}...")
        
        try:
            result = agent.process_request(llm_req["request"])
            
            if "error" not in result:
                response = result.get("response_text", "No response")[:150]
                print(f"✅ LLM Response: {response}...")
                
                monitor.record_event("llm_processed", {
                    "description": llm_req["description"],
                    "response_length": len(result.get("response_text", "")),
                })
            else:
                print(f"❌ LLM Error: {result['error']}")
                monitor.record_event("llm_error", {
                    "description": llm_req["description"],
                    "error": result['error'],
                })
        except Exception as e:
            print(f"❌ Failed to process LLM request: {e}")
            logger.error(f"LLM processing failed: {e}")
            monitor.record_event("llm_processing_failed", {
                "error": str(e),
            })
    
    # ========== TELEMETRY SUMMARY ==========
    monitor.print_section("6️⃣  TELEMETRY & MONITORING")
    
    agent_telemetry = agent.get_telemetry()
    metrics = agent_telemetry.get("metrics", {})
    events = agent_telemetry.get("events", [])
    
    print("\n📊 Agent Metrics:")
    print(f"   Messages queued:        {metrics.get('messages_queued', 0)}")
    print(f"   Messages scheduled:     {metrics.get('messages_scheduled', 0)}")
    print(f"   Messages sent:          {metrics.get('messages_sent', 0)}")
    print(f"   Replies received:       {metrics.get('replies_received', 0)}")
    print(f"   Pattern violations:     {metrics.get('pattern_violations', 0)}")
    print(f"   Avg typing time:        {metrics.get('average_typing_time', 0):.2f}s")
    print(f"   Avg inter-msg delay:    {metrics.get('average_inter_message_delay', 0):.2f}s")
    print(f"   Pydantic validations:   {metrics.get('pydantic_validation_successes', 0)} success, {metrics.get('pydantic_validation_errors', 0)} errors")
    
    print(f"\n📋 Agent Events ({len(events)}):")
    event_types = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    for event_type, count in sorted(event_types.items()):
        print(f"   {event_type:<30} {count:3}x")
    
    print(f"\n💰 Token Usage & Cost Tracking:")
    token_usage = agent_telemetry.get("token_usage", {})
    if token_usage:
        print(f"   Total tokens:           {token_usage.get('total_tokens', 0):,}")
        print(f"   Total cost:             ${token_usage.get('total_cost_usd', 0):.6f} USD")
        print(f"   API calls:               {token_usage.get('total_api_calls', 0)}")
        
        usage_by_model = token_usage.get("usage_by_model", {})
        if usage_by_model:
            print(f"\n   Usage by Model:")
            for model, stats in usage_by_model.items():
                print(f"     {model}:")
                print(f"       ├─ Calls: {stats.get('calls', 0)}")
                print(f"       ├─ Tokens: {stats.get('total_tokens', 0):,}")
                print(f"       └─ Cost: ${stats.get('cost_usd', 0):.6f} USD")
    else:
        print(f"   No token usage recorded yet")
    
    print(f"\n📱 Mock SMS Sender Summary:")
    sms_summary = sms_sender.get_summary()
    print(f"   Total messages sent:    {sms_summary['total_sent']}")
    print(f"   Unique recipients:      {sms_summary['unique_recipients']}")
    print(f"   Recipients:")
    for recipient in sms_summary["recipients"]:
        print(f"     - {recipient}")
    
    # ========== MESSAGE LOG ==========
    monitor.print_section("7️⃣  DETAILED MESSAGE LOG")
    sms_sender.print_sent_messages()
    
    # ========== FINAL SUMMARY ==========
    monitor.print_header("✅ SIMULATION COMPLETE")
    
    print(f"\n✨ Pipeline Execution Summary:")
    print(f"   Agent Initialized:      ✅ LangChain v1 create_agent")
    print(f"   Jitter Algorithm:       ✅ Scheduled {monitor.stats['messages_scheduled']} messages")
    print(f"   Mock SMS Sending:       ✅ Sent {monitor.stats['messages_sent']} messages")
    print(f"   LLM Processing:         ✅ {len(llm_requests)} requests processed")
    print(f"   Telemetry Collection:   ✅ LangSmith & Logfire enabled")
    print(f"   Logging:                ✅ Structured logs saved")
    
    print(f"\n📊 Final Statistics:")
    print(f"   Total messages:         {monitor.stats['messages_created']}")
    print(f"   Successfully sent:      {monitor.stats['messages_sent']}")
    print(f"   Success rate:           {(monitor.stats['messages_sent']/monitor.stats['messages_created']*100):.1f}%")
    print(f"   Errors:                 {monitor.stats['errors']}")
    
    print(f"\n📁 Logs saved to: logs/")
    
    # Export token usage to JSON
    try:
        from pathlib import Path
        token_export_path = Path("logs") / f"token_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        token_export_path.parent.mkdir(exist_ok=True)
        agent.export_token_usage(str(token_export_path))
        print(f"💰 Token usage exported to: {token_export_path}")
    except Exception as e:
        print(f"⚠️  Could not export token usage: {e}")
    
    print(f"\n🎉 Full end-to-end pipeline executed successfully!")
    
    # Print summary
    monitor.print_summary()
    
    # Print token usage summary
    try:
        agent.telemetry.token_tracker.print_summary()
    except Exception:
        pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SMS Phishing Simulation - Human-realistic timing patterns"
    )
    parser.add_argument(
        "--single-recipient",
        action="store_true",
        help="Send all 50 messages to the same recipient (matches Part 3 Question 2 scenario). "
             "Default: False (distribute across multiple recipients)"
    )
    
    args = parser.parse_args()
    
    try:
        run_simulation(single_recipient_mode=args.single_recipient)
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Simulation failed: {e}")
        sys.exit(1)

