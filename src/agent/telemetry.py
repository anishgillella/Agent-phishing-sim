"""
Telemetry Collector

Collects telemetry data for monitoring and evaluation.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from pydantic import BaseModel
import logfire
from langsmith import Client as LangSmithClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """
    Collects telemetry data for monitoring and evaluation.
    
    Three-tier telemetry system:
    1. Local metrics/traces (always available, no API key needed)
    2. LangSmith integration (optional, for LLM tracing and general telemetry)
    3. Logfire integration (optional, for Pydantic model validation and evaluation)
    
    Works without API keys - all telemetry stored locally.
    With API keys - also sends to cloud services for production observability.
    """
    
    def __init__(self, 
                 langsmith_api_key: Optional[str] = None,
                 logfire_api_key: Optional[str] = None):
        # Local metrics storage (no API key needed)
        self.metrics: Dict[str, Any] = {
            "messages_queued": 0,
            "messages_scheduled": 0,
            "messages_sent": 0,
            "replies_received": 0,
            "pattern_violations": 0,
            "schedule_adjustments": 0,
            "average_typing_time": 0.0,
            "average_inter_message_delay": 0.0,
            "total_typing_time": 0.0,
            "total_inter_message_delays": 0.0,
            "typing_time_count": 0,
            "delay_count": 0,
            "pydantic_validation_errors": 0,
            "pydantic_validation_successes": 0,
        }
        self.traces: List[Dict[str, Any]] = []
        self.langsmith_client = None
        self.logfire_configured = False
        
        # Token tracking (production-ready cost tracking)
        self.token_tracker = TokenTracker()
        
        # Optional: Initialize LangSmith if API key provided
        # For general telemetry and LLM tracing
        if langsmith_api_key:
            try:
                self.langsmith_client = LangSmithClient(api_key=langsmith_api_key)
                logger.info("LangSmith client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize LangSmith: {e}. Telemetry will continue with local storage only.")
        
        # Optional: Initialize Logfire if API key provided
        # For Pydantic model validation and structured output evaluation
        if logfire_api_key:
            try:
                logfire.configure(
                    token=logfire_api_key,
                    service_name="ghosteye-smishing-sim",
                    service_version="1.0.0",
                )
                self.logfire_configured = True
                logger.info("Logfire configured for Pydantic model validation")
            except Exception as e:
                logger.warning(f"Could not initialize Logfire: {e}. Telemetry will continue with local storage only.")
        else:
            # Try to configure from environment variable
            try:
                logfire.configure(
                    service_name="ghosteye-smishing-sim",
                    service_version="1.0.0",
                )
                self.logfire_configured = True
                logger.info("Logfire configured (using environment or default)")
            except Exception:
                # Logfire works without explicit configuration (local mode)
                pass
    
    def record_metric(self, metric_name: str, value: Any):
        """Record a metric."""
        self.metrics[metric_name] = value
    
    def increment_metric(self, metric_name: str, amount: int = 1):
        """Increment a metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += amount
    
    def record_typing_time(self, typing_time: float):
        """Record typing time for average calculation."""
        self.metrics["total_typing_time"] += typing_time
        self.metrics["typing_time_count"] += 1
        self.metrics["average_typing_time"] = (
            self.metrics["total_typing_time"] / self.metrics["typing_time_count"]
        )
    
    def record_delay(self, delay: float):
        """Record inter-message delay for average calculation."""
        self.metrics["total_inter_message_delays"] += delay
        self.metrics["delay_count"] += 1
        self.metrics["average_inter_message_delay"] = (
            self.metrics["total_inter_message_delays"] / self.metrics["delay_count"]
        )
    
    def add_trace(self, trace_data: Dict[str, Any]):
        """Add a trace entry."""
        trace_data["timestamp"] = datetime.now().isoformat()
        self.traces.append(trace_data)
        
        # Send to Logfire if available (for detailed tracing)
        # Only log important traces, not every event (to reduce console noise)
        trace_name = trace_data.get("name", "trace")
        important_traces = ["agent_tool_calls", "agent_error", "agent_process_request"]
        
        if self.logfire_configured:
            try:
                # Only log important traces to reduce console verbosity
                if trace_name in important_traces:
                    logfire.info(
                        trace_name,
                        **trace_data
                    )
                # For other traces, use debug level (won't show in console)
                else:
                    logfire.debug(
                        trace_name,
                        **trace_data
                    )
            except Exception as e:
                logger.warning(f"Could not send trace to Logfire: {e}")
    
    def validate_pydantic_model(self, model_class: type[BaseModel], data: Dict[str, Any]) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate data against a Pydantic model using Logfire.
        
        Args:
            model_class: Pydantic model class
            data: Data to validate
        
        Returns:
            Tuple of (is_valid, validated_model_or_none, error_message_or_none)
        """
        try:
            # Validate with Pydantic
            validated = model_class(**data)
            
            # Log success to Logfire (automatic validation tracking)
            if self.logfire_configured:
                with logfire.span("pydantic_validation", model=model_class.__name__):
                    logfire.info(
                        "Pydantic validation successful",
                        model=model_class.__name__,
                        data=data,
                        validated=validated.model_dump(),
                    )
            
            self.increment_metric("pydantic_validation_successes")
            return True, validated, None
            
        except Exception as e:
            error_msg = str(e)
            
            # Log failure to Logfire (automatic validation tracking)
            if self.logfire_configured:
                with logfire.span("pydantic_validation_error", model=model_class.__name__):
                    logfire.error(
                        "Pydantic validation failed",
                        model=model_class.__name__,
                        data=data,
                        error=error_msg,
                    )
            
            self.increment_metric("pydantic_validation_errors")
            return False, None, error_msg
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics including token usage."""
        metrics = self.metrics.copy()
        # Add token usage summary
        token_summary = self.token_tracker.get_summary()
        metrics["token_usage"] = {
            "total_tokens": token_summary["total_tokens"],
            "total_cost_usd": token_summary["total_cost_usd"],
            "total_api_calls": token_summary["total_api_calls"],
        }
        return metrics
    
    def get_traces(self) -> List[Dict[str, Any]]:
        """Get all traces."""
        return self.traces.copy()

