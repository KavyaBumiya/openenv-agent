"""
OpenAI Integration Module
=========================
Provides AI-powered scoring, feedback, and analysis using OpenAI API.

Features:
- AI-powered response quality evaluation
- Intelligent feedback generation
- Agent performance analysis
- Dynamic scoring based on semantic understanding
"""

import logging
import os
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. AI features will be disabled.")


class OpenAIIntegration:
    """Wrapper for OpenAI API calls with caching and error handling."""
    
    def __init__(self):
        """Initialize OpenAI client from API key."""
        self.enabled = OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY'))
        
        if self.enabled:
            try:
                self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                logger.info("✅ OpenAI integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️  OpenAI API key not found. AI features disabled.")
    
    def evaluate_response_quality(self, response: str, ticket_desc: str) -> Dict[str, Any]:
        """
        Evaluate customer support response quality using AI.
        
        Args:
            response: The support agent's response text
            ticket_desc: The original ticket description
            
        Returns:
            Dict with 'score' (0-1), 'reasoning', and 'suggestions'
        """
        if not self.enabled:
            return {
                'score': 0.5,
                'reasoning': 'OpenAI integration disabled',
                'suggestions': []
            }
        
        try:
            prompt = f"""Evaluate the quality of this customer support response on a scale of 0-1.
            
TICKET: {ticket_desc}

RESPONSE: {response}

Provide a JSON response with:
- score: float between 0 and 1
- reasoning: brief explanation
- suggestions: list of 1-2 improvement suggestions"""

            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert customer support evaluator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                result['score'] = max(0.001, min(0.999, float(result.get('score', 0.5))))
                return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse OpenAI response: {response_text}")
                return {
                    'score': 0.5,
                    'reasoning': response_text[:100],
                    'suggestions': []
                }
                
        except Exception as e:
            logger.error(f"OpenAI evaluation failed: {e}")
            return {
                'score': 0.5,
                'reasoning': f'API error: {str(e)[:50]}',
                'suggestions': []
            }
    
    def analyze_agent_strategy(self, actions: list, tickets: list) -> Dict[str, Any]:
        """
        Analyze agent's overall strategy and performance using AI.
        
        Args:
            actions: List of actions taken by agent
            tickets: List of tickets processed
            
        Returns:
            Dict with 'performance_level', 'strengths', 'weaknesses'
        """
        if not self.enabled:
            return {
                'performance_level': 'baseline',
                'strengths': [],
                'weaknesses': []
            }
        
        try:
            # Summarize actions for context
            action_summary = f"Processed {len(tickets)} tickets with {len(actions)} actions"
            
            prompt = f"""Analyze this customer support agent's strategy:

{action_summary}

Provide a JSON response with:
- performance_level: 'poor', 'baseline', 'good', or 'excellent'
- strengths: list of 2-3 strengths
- weaknesses: list of 2-3 improvement areas"""

            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating customer support strategies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=250
            )
            
            response_text = completion.choices[0].message.content
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    'performance_level': 'baseline',
                    'strengths': ['Engaged with tickets'],
                    'weaknesses': ['Room for improvement']
                }
                
        except Exception as e:
            logger.error(f"OpenAI strategy analysis failed: {e}")
            return {
                'performance_level': 'baseline',
                'strengths': [],
                'weaknesses': []
            }
    
    def generate_feedback(self, score: float, action_type: str, context: str) -> str:
        """
        Generate intelligent feedback for agent actions.
        
        Args:
            score: The reward/score received
            action_type: Type of action ('classify', 'route', 'resolve')
            context: Context about the action
            
        Returns:
            Feedback string
        """
        if not self.enabled:
            return f"Score: {score:.3f}"
        
        try:
            prompt = f"""Generate brief, encouraging feedback for a support agent.
            
Action: {action_type}
Score: {score:.1%}
Context: {context}

Provide 1-2 sentences of constructive feedback."""

            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a supportive coach for customer support agents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI feedback generation failed: {e}")
            return f"Score: {score:.3f}"
    
    def classify_priority_ai(self, ticket_desc: str) -> Dict[str, Any]:
        """
        Use AI to classify ticket priority (complements rule-based scoring).
        
        Args:
            ticket_desc: Ticket description
            
        Returns:
            Dict with 'priority', 'urgency_score', 'reasoning'
        """
        if not self.enabled:
            return {
                'priority': 'medium',
                'urgency_score': 0.5,
                'reasoning': 'AI disabled'
            }
        
        try:
            prompt = f"""Analyze ticket priority:

TICKET: {ticket_desc}

Respond in JSON format:
- priority: 'low', 'medium', or 'high'
- urgency_score: 0-1 float
- reasoning: brief explanation"""

            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are expert at prioritizing customer support tickets."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            response_text = completion.choices[0].message.content
            result = json.loads(response_text)
            result['urgency_score'] = max(0.001, min(0.999, float(result.get('urgency_score', 0.5))))
            return result
            
        except Exception as e:
            logger.error(f"AI priority classification failed: {e}")
            return {
                'priority': 'medium',
                'urgency_score': 0.5,
                'reasoning': str(e)[:50]
            }


# Singleton instance
_openai_integration = None


def get_openai_integration() -> OpenAIIntegration:
    """Get or create OpenAI integration singleton."""
    global _openai_integration
    if _openai_integration is None:
        _openai_integration = OpenAIIntegration()
    return _openai_integration
