"""
Mock SMS Sender for simulation with detailed logging.
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .logger import get_logger, log_with_context


logger = get_logger("MockSMS")


@dataclass
class SMSRecord:
    """Record of a sent SMS message."""
    message_id: str
    recipient: str
    content: str
    scheduled_time: datetime
    sent_time: datetime
    typing_delay: float
    status: str  # "pending", "sent", "failed", "delivered"


class MockSMSSender:
    """
    Mock SMS sender that simulates message sending with realistic timing.
    Does NOT actually send SMS - for simulation purposes only.
    """
    
    def __init__(self):
        self.logger = logger
        self.messages_sent = []
        self.message_counter = 0
        self.recipients_contacted = set()
    
    def send_sms(
        self,
        recipient: str,
        content: str,
        scheduled_time: datetime,
        typing_delay: float,
        simulation_mode: bool = True
    ) -> SMSRecord:
        """
        Send (mock) SMS message with realistic timing.
        
        Args:
            recipient: Phone number
            content: Message content
            scheduled_time: When the message should be sent
            typing_delay: Simulated typing time
            simulation_mode: If True, use real time delay; if False, instant
        
        Returns:
            SMSRecord with send details
        """
        self.message_counter += 1
        message_id = f"MSG_{self.message_counter:06d}"
        
        # Calculate delay until scheduled time
        now = datetime.now()
        if scheduled_time > now:
            delay_seconds = (scheduled_time - now).total_seconds()
        else:
            delay_seconds = 0
        
        # Log pre-send status
        log_with_context(
            self.logger,
            "INFO",
            f"📤 Preparing SMS: {message_id}",
            recipient=recipient,
            scheduled_time=scheduled_time.isoformat(),
            delay_seconds=delay_seconds,
            content_preview=content[:50],
            typing_delay=typing_delay,
        )
        
        # In simulation mode, wait for scheduled time
        if simulation_mode and delay_seconds > 0:
            print(f"   ⏳ Waiting {delay_seconds:.1f}s until scheduled time...")
            time.sleep(min(delay_seconds, 0.5))  # Cap at 0.5s for demo
        
        # Simulate typing delay
        if typing_delay > 0:
            print(f"   ⌨️  Simulating typing ({typing_delay:.1f}s)...", end="", flush=True)
            time.sleep(min(typing_delay / 10, 0.2))  # Scale down for demo
            print(" done")
        
        # Actually "send" the message
        sent_time = datetime.now()
        status = "sent"
        
        record = SMSRecord(
            message_id=message_id,
            recipient=recipient,
            content=content,
            scheduled_time=scheduled_time,
            sent_time=sent_time,
            typing_delay=typing_delay,
            status=status,
        )
        
        self.messages_sent.append(record)
        self.recipients_contacted.add(recipient)
        
        # Log successful send
        log_with_context(
            self.logger,
            "INFO",
            f"✅ SMS Sent: {message_id}",
            recipient=recipient,
            scheduled_time=scheduled_time.isoformat(),
            sent_time=sent_time.isoformat(),
            delay_actual=(sent_time - scheduled_time).total_seconds(),
            content_length=len(content),
            typing_delay=typing_delay,
        )
        
        # Print send confirmation
        print(f"   ✅ Message sent!")
        print(f"      Message ID: {message_id}")
        print(f"      To: {recipient}")
        print(f"      Content: {content}")
        print(f"      Sent at: {sent_time.strftime('%H:%M:%S.%f')[:-3]}")
        
        return record
    
    def send_batch(
        self,
        messages: list,
        use_delays: bool = True
    ) -> list:
        """
        Send a batch of messages.
        
        Args:
            messages: List of dicts with recipient, content, scheduled_time, typing_delay
            use_delays: Whether to use realistic delays between sends
        
        Returns:
            List of SMSRecords
        """
        records = []
        for i, msg in enumerate(messages):
            record = self.send_sms(
                recipient=msg["recipient"],
                content=msg["content"],
                scheduled_time=msg.get("scheduled_time", datetime.now()),
                typing_delay=msg.get("typing_delay", 0),
            )
            records.append(record)
            
            # Add brief pause between batch messages
            if use_delays and i < len(messages) - 1:
                time.sleep(0.1)
        
        return records
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all sent messages."""
        return {
            "total_sent": len(self.messages_sent),
            "unique_recipients": len(self.recipients_contacted),
            "recipients": list(self.recipients_contacted),
            "messages": [
                {
                    "message_id": msg.message_id,
                    "recipient": msg.recipient,
                    "content": msg.content,
                    "sent_time": msg.sent_time.isoformat(),
                    "typing_delay": msg.typing_delay,
                }
                for msg in self.messages_sent
            ]
        }
    
    def print_sent_messages(self):
        """Print all sent messages in a formatted table."""
        if not self.messages_sent:
            print("No messages sent yet.")
            return
        
        print("\n" + "="*120)
        print(f"  📨 SENT MESSAGES ({len(self.messages_sent)} total to {len(self.recipients_contacted)} recipients)")
        print("="*120)
        
        print(f"\n{'ID':<12} {'Recipient':<15} {'Sent Time':<15} {'Content':<50}")
        print("-"*120)
        
        for msg in self.messages_sent:
            content_preview = msg.content[:47] + "..." if len(msg.content) > 50 else msg.content
            print(f"{msg.message_id:<12} {msg.recipient:<15} {msg.sent_time.strftime('%H:%M:%S.%f')[:-3]:<15} {content_preview:<50}")

