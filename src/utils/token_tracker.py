"""
Token Tracking and Cost Calculation Utilities

Production-ready token counting and cost tracking for LLM API calls.
Supports OpenRouter pricing models and provides detailed usage analytics.
"""

import json
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class TokenUsage:
    """Represents token usage for a single API call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
        }


@dataclass
class CostBreakdown:
    """Cost breakdown for token usage."""
    prompt_cost: float = 0.0
    completion_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prompt_cost": self.prompt_cost,
            "completion_cost": self.completion_cost,
            "total_cost": self.total_cost,
            "currency": self.currency,
        }


class TokenTracker:
    """
    Production-ready token tracking and cost calculation.
    
    Tracks token usage across all LLM API calls and calculates costs
    based on OpenRouter pricing models.
    """
    
    # OpenRouter pricing per 1M tokens (as of 2025)
    # Source: https://openrouter.ai/models
    PRICING = {
        "openai/gpt-4o-mini": {
            "prompt": 0.15,      # $0.15 per 1M prompt tokens
            "completion": 0.60,  # $0.60 per 1M completion tokens
        },
        "openai/gpt-4o": {
            "prompt": 2.50,
            "completion": 10.00,
        },
        "openai/gpt-4-turbo": {
            "prompt": 10.00,
            "completion": 30.00,
        },
        "anthropic/claude-3-haiku": {
            "prompt": 0.25,
            "completion": 1.25,
        },
        "anthropic/claude-3-sonnet": {
            "prompt": 3.00,
            "completion": 15.00,
        },
        "anthropic/claude-3-opus": {
            "prompt": 15.00,
            "completion": 75.00,
        },
        # Default fallback pricing
        "default": {
            "prompt": 0.15,
            "completion": 0.60,
        },
    }
    
    def __init__(self):
        """Initialize token tracker."""
        self.usage_history: List[TokenUsage] = []
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self.usage_by_model: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        })
    
    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        request_id: Optional[str] = None
    ) -> TokenUsage:
        """
        Record token usage for an API call.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model identifier (e.g., "openai/gpt-4o-mini")
            request_id: Optional request identifier
        
        Returns:
            TokenUsage object
        """
        total_tokens = prompt_tokens + completion_tokens
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            timestamp=datetime.now(),
            request_id=request_id,
        )
        
        # Update totals
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        
        # Update model-specific stats
        self.usage_by_model[model]["prompt_tokens"] += prompt_tokens
        self.usage_by_model[model]["completion_tokens"] += completion_tokens
        self.usage_by_model[model]["total_tokens"] += total_tokens
        self.usage_by_model[model]["calls"] += 1
        
        # Calculate and add cost
        cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
        self.total_cost += cost
        
        # Store usage
        self.usage_history.append(usage)
        
        return usage
    
    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> float:
        """
        Calculate cost for token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model identifier
        
        Returns:
            Cost in USD
        """
        # Get pricing for model or use default
        pricing = self.PRICING.get(model, self.PRICING["default"])
        
        # Calculate costs (pricing is per 1M tokens)
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    def get_cost_breakdown(self, model: str) -> CostBreakdown:
        """
        Get cost breakdown for a specific model.
        
        Args:
            model: Model identifier
        
        Returns:
            CostBreakdown object
        """
        model_usage = self.usage_by_model.get(model, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
        })
        
        pricing = self.PRICING.get(model, self.PRICING["default"])
        
        prompt_cost = (model_usage["prompt_tokens"] / 1_000_000) * pricing["prompt"]
        completion_cost = (model_usage["completion_tokens"] / 1_000_000) * pricing["completion"]
        
        return CostBreakdown(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            currency="USD",
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive usage summary.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "total_api_calls": len(self.usage_history),
            "usage_by_model": {
                model: {
                    **stats,
                    "cost_usd": round(self.get_cost_breakdown(model).total_cost, 6),
                }
                for model, stats in self.usage_by_model.items()
            },
            "recent_usage": [
                usage.to_dict()
                for usage in self.usage_history[-10:]  # Last 10 calls
            ],
        }
    
    def get_model_summary(self, model: str) -> Dict[str, Any]:
        """
        Get usage summary for a specific model.
        
        Args:
            model: Model identifier
        
        Returns:
            Dictionary with model-specific statistics
        """
        model_usage = self.usage_by_model.get(model, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        })
        
        cost_breakdown = self.get_cost_breakdown(model)
        
        return {
            "model": model,
            "prompt_tokens": model_usage["prompt_tokens"],
            "completion_tokens": model_usage["completion_tokens"],
            "total_tokens": model_usage["total_tokens"],
            "api_calls": model_usage["calls"],
            "cost": cost_breakdown.to_dict(),
            "avg_tokens_per_call": (
                model_usage["total_tokens"] / model_usage["calls"]
                if model_usage["calls"] > 0
                else 0
            ),
        }
    
    def reset(self):
        """Reset all tracking data."""
        self.usage_history.clear()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.usage_by_model.clear()
    
    def export_usage(self, filepath: str):
        """
        Export usage history to JSON file.
        
        Args:
            filepath: Path to save JSON file
        """
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "usage_history": [usage.to_dict() for usage in self.usage_history],
        }
        
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)
    
    def print_summary(self):
        """Print formatted usage summary to console."""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("📊 TOKEN USAGE & COST SUMMARY")
        print("="*80)
        
        print(f"\n💰 Total Cost: ${summary['total_cost_usd']:.6f} USD")
        print(f"📈 Total Tokens: {summary['total_tokens']:,}")
        print(f"   - Prompt: {summary['total_prompt_tokens']:,}")
        print(f"   - Completion: {summary['total_completion_tokens']:,}")
        print(f"📞 Total API Calls: {summary['total_api_calls']}")
        
        if summary['usage_by_model']:
            print(f"\n📋 Usage by Model:")
            for model, stats in summary['usage_by_model'].items():
                print(f"\n   Model: {model}")
                print(f"   ├─ API Calls: {stats['calls']}")
                print(f"   ├─ Prompt Tokens: {stats['prompt_tokens']:,}")
                print(f"   ├─ Completion Tokens: {stats['completion_tokens']:,}")
                print(f"   ├─ Total Tokens: {stats['total_tokens']:,}")
                print(f"   └─ Cost: ${stats['cost_usd']:.6f} USD")
        
        print("\n" + "="*80)

