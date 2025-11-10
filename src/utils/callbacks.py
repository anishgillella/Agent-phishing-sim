"""
LangChain Callback Handler for Token Tracking

Captures token usage from LangChain LLM calls and integrates with TokenTracker.
"""

from typing import Any, Dict, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .token_tracker import TokenTracker


class TokenTrackingCallback(BaseCallbackHandler):
    """
    LangChain callback handler that tracks token usage.
    
    Integrates with TokenTracker to capture token counts from LLM API calls.
    """
    
    def __init__(self, token_tracker: TokenTracker, model: str = "openai/gpt-4o-mini"):
        """
        Initialize callback handler.
        
        Args:
            token_tracker: TokenTracker instance to record usage
            model: Model identifier for cost calculation
        """
        super().__init__()
        self.token_tracker = token_tracker
        self.model = model
        self.current_request_id: Optional[str] = None
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when LLM finishes generating response.
        
        Extracts token usage from response and records it.
        Supports both LangChain v0.3.x and v1 response formats.
        """
        # Extract token usage from LLM response
        # LangChain v1 and v0.3.x may have different formats
        prompt_tokens = 0
        completion_tokens = 0
        
        # Try to extract from llm_output (LangChain v0.3.x)
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
        
        # Try to extract from response_metadata (LangChain v1)
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata or {}
            if "token_usage" in metadata:
                token_usage = metadata["token_usage"]
                prompt_tokens = token_usage.get("prompt_tokens", prompt_tokens)
                completion_tokens = token_usage.get("completion_tokens", completion_tokens)
        
        # Try to extract from kwargs
        if "token_usage" in kwargs:
            token_usage = kwargs["token_usage"]
            prompt_tokens = token_usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = token_usage.get("completion_tokens", completion_tokens)
        
        # Record usage if tokens are present
        if prompt_tokens > 0 or completion_tokens > 0:
            self.token_tracker.record_usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=self.model,
                request_id=self.current_request_id,
            )
    
    def set_request_id(self, request_id: str):
        """Set request ID for current call."""
        self.current_request_id = request_id

