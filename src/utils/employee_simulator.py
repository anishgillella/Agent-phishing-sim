"""
Employee Simulator

Uses LLM to simulate realistic employee responses to phishing messages.
"""

import os
import logging
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class EmployeeSimulator:
    """
    Simulates an employee using LLM to generate realistic replies.
    
    Uses GPT-4o-mini to generate contextually appropriate responses
    to phishing simulation messages.
    """
    
    def __init__(self, openrouter_api_key: Optional[str] = None):
        """
        Initialize employee simulator.
        
        Args:
            openrouter_api_key: OpenRouter API key (uses env var if not provided)
        """
        openrouter_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OpenRouter API key required for employee simulator")
        
        self.llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.8,  # Higher temperature for more varied responses
        )
        
        self.conversation_history: Dict[str, list] = {}  # Track conversations per recipient
    
    def generate_reply(self, 
                      message_content: str,
                      recipient: str = "+1234567890",
                      message_number: int = 1,
                      employee_personality: str = "typical") -> str:
        """
        Generate a realistic employee reply to a phishing message.
        
        Args:
            message_content: The phishing message content
            recipient: Phone number (for conversation history)
            message_number: Which message in the sequence (1, 2, 3...)
            employee_personality: "typical", "skeptical", "busy", "helpful"
        
        Returns:
            Realistic employee reply text
        """
        # Get conversation history for this recipient
        history = self.conversation_history.get(recipient, [])
        
        # Build system prompt based on personality
        personality_prompts = {
            "typical": """You are a typical office employee receiving SMS messages. 
You're generally helpful but busy. You might respond quickly to urgent messages, 
but you're also cautious about suspicious links. Sometimes you're distracted and 
respond briefly, sometimes you ask questions.""",
            
            "skeptical": """You are a security-conscious employee. You're suspicious 
of unexpected verification requests and unusual links. You ask questions and 
verify before clicking anything. You might ignore some messages or respond 
with skepticism.""",
            
            "busy": """You are a very busy employee. You respond quickly and briefly 
when you do respond. Sometimes you don't respond at all because you're in meetings 
or focused on work. When you do respond, it's short and to the point.""",
            
            "helpful": """You are a helpful employee who tries to assist when asked. 
You respond promptly and are generally trusting. You might click links if they 
seem legitimate and respond positively to urgent requests."""
        }
        
        system_prompt = personality_prompts.get(employee_personality, personality_prompts["typical"])
        
        # Build context about the conversation
        context = ""
        if history:
            context = "\n\nPrevious conversation:\n"
            for i, (msg, reply) in enumerate(history[-3:], 1):  # Last 3 exchanges
                context += f"Message {i}: {msg}\n"
                context += f"Your reply: {reply}\n"
        
        # Create prompt
        prompt = f"""{system_prompt}

You received this SMS message (message #{message_number}):
"{message_content}"
{context}

Generate a realistic, human-like reply. Consider:
- The message content and urgency level
- Your personality and current state (busy, distracted, etc.)
- Whether you'd actually respond (sometimes you might not)
- Natural, casual SMS language (short, informal)
- Your level of trust/skepticism based on the message

If you decide to respond, write a realistic SMS reply (1-2 sentences max, casual tone).
If you decide not to respond, just say "NO_REPLY".

Your reply:"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            reply = response.content.strip()
            
            # Store in conversation history
            if recipient not in self.conversation_history:
                self.conversation_history[recipient] = []
            
            # Only store if there's an actual reply
            if reply and reply != "NO_REPLY":
                self.conversation_history[recipient].append((message_content, reply))
            
            return reply if reply != "NO_REPLY" else None
            
        except Exception as e:
            logger.error(f"Error generating employee reply: {e}")
            # Fallback to simple responses
            fallback_replies = [
                "Thanks, I'll check it out",
                "Got it, thanks",
                "Will do",
                None  # Sometimes no reply
            ]
            import random
            return random.choice(fallback_replies)
    
    def should_reply(self, message_content: str, message_number: int) -> bool:
        """
        Determine if employee should reply to this message.
        
        Args:
            message_content: Message content
            message_number: Message number in sequence
        
        Returns:
            True if employee should reply, False otherwise
        """
        # Employees are more likely to reply to:
        # - Early messages (1-5)
        # - Urgent messages
        # - Questions
        
        urgency_keywords = ["urgent", "immediately", "asap", "now", "verify", "locked"]
        question_keywords = ["?", "can you", "please", "need"]
        
        has_urgency = any(keyword in message_content.lower() for keyword in urgency_keywords)
        has_question = any(keyword in message_content.lower() for keyword in question_keywords)
        
        # Higher probability for early messages, urgent messages, or questions
        import random
        base_probability = 0.3  # 30% base chance
        
        if message_number <= 5:
            base_probability = 0.6  # 60% for early messages
        if has_urgency:
            base_probability = 0.7  # 70% for urgent
        if has_question:
            base_probability = 0.5  # 50% for questions
        
        return random.random() < base_probability
    
    def clear_history(self, recipient: Optional[str] = None):
        """Clear conversation history for a recipient or all recipients."""
        if recipient:
            self.conversation_history.pop(recipient, None)
        else:
            self.conversation_history.clear()


