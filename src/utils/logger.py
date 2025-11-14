"""
Structured logging for the SMS Agent and Jitter Algorithm.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with context."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "component": record.name.split(".")[-1],
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Pretty formatter for console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Build the message
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level = f"{color}{record.levelname:8}{self.RESET}"
        component = f"{record.name.split('.')[-1]:15}"
        message = record.getMessage()
        
        log_line = f"[{timestamp}] {level} {component} | {message}"
        
        # Add extra data if present
        if hasattr(record, "extra_data"):
            extra_str = " | " + json.dumps(record.extra_data)
            log_line += extra_str
        
        return log_line


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with structured formatting."""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Suppress verbose logs - only show INFO and above
        logger.setLevel(logging.INFO)
        
        # Console handler (pretty format) - only INFO and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)
        
        # File handler (JSON format for structured analysis) - DEBUG level for file
        file_handler = logging.FileHandler(
            LOGS_DIR / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """Log with extra context data."""
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level),
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = context
    logger.handle(record)


class SimulationMonitor:
    """Real-time monitoring dashboard for simulations."""
    
    def __init__(self):
        self.logger = get_logger("SimulationMonitor")
        self.stats = {
            "messages_created": 0,
            "messages_scheduled": 0,
            "messages_sent": 0,
            "total_time": 0.0,
            "errors": 0,
            "start_time": datetime.now(),
        }
        self.events = []
    
    def record_event(self, event_type: str, details: Dict[str, Any]):
        """Record an event in the simulation."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details
        }
        self.events.append(event)
        
        # Log with context
        log_with_context(
            self.logger,
            "INFO",
            f"Event: {event_type}",
            **details
        )
    
    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
    
    def print_section(self, title: str):
        """Print a formatted section."""
        print("\n" + "-"*80)
        print(f"  {title}")
        print("-"*80)
    
    def print_summary(self):
        """Print simulation summary."""
        elapsed = datetime.now() - self.stats["start_time"]
        
        self.print_header("📊 SIMULATION SUMMARY")
        print(f"\n✅ Completed in {elapsed.total_seconds():.2f}s")
        print(f"\n📈 Statistics:")
        print(f"   Messages created:   {self.stats['messages_created']}")
        print(f"   Messages scheduled: {self.stats['messages_scheduled']}")
        print(f"   Messages sent:      {self.stats['messages_sent']}")
        print(f"   Errors:             {self.stats['errors']}")
        
        success_rate = (
            (self.stats['messages_sent'] / self.stats['messages_created'] * 100)
            if self.stats['messages_created'] > 0
            else 0
        )
        print(f"   Success rate:       {success_rate:.1f}%")
        
        # Event breakdown
        event_types = {}
        for event in self.events:
            event_type = event["type"]
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if event_types:
            print(f"\n📋 Event Breakdown:")
            for event_type, count in sorted(event_types.items()):
                print(f"   {event_type:30} {count:3}x")

