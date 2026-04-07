"""
Semantic Response Evaluator: Uses embeddings for quality assessment.

Replaces keyword-based evaluation with semantic similarity scoring.
Better for:
- Detecting paraphrased responses
- Evaluating response quality beyond keywords
- Avoiding agents gaming the keyword checker
"""

import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Semantic evaluation disabled.")


class SemanticResponseEvaluator:
    """Evaluate response quality using semantic similarity."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize semantic evaluator.
        
        Args:
            model_name: HuggingFace model name for embeddings
        """
        self.enabled = SEMANTIC_AVAILABLE
        self.model_name = model_name
        self.model = None
        
        if self.enabled:
            try:
                logger.info(f"Loading semantic model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info("✓ Semantic evaluator ready")
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}")
                self.enabled = False
    
    def evaluate_response(
        self,
        response: str,
        ideal_responses: list[str],
        required_keywords: list[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Evaluate response quality using semantic similarity.
        
        Args:
            response: Agent's response
            ideal_responses: List of ideal/reference responses
            required_keywords: Keywords that should be present
            
        Returns:
            {
                "semantic_score": float (0-1),
                "keyword_coverage": float (0-1),
                "combined_score": float (0-1),
                "reasoning": str,
                "top_matches": list[tuple],  # (ideal_response, similarity)
            }
        """
        result = {
            "semantic_score": 0.5,
            "keyword_coverage": 0.5,
            "combined_score": 0.5,
            "reasoning": "Semantic evaluation disabled",
            "top_matches": [],
        }
        
        if not self.enabled or not self.model:
            return result
        
        if not response or len(response) < 10:
            result["reasoning"] = "Response too short"
            return result
        
        try:
            # Semantic similarity to ideal responses
            response_embedding = self.model.encode(response, convert_to_tensor=True)
            ideal_embeddings = [
                self.model.encode(ir, convert_to_tensor=True)
                for ir in ideal_responses
            ]
            
            similarities = [
                float(st_util.pytorch_cos_sim(response_embedding, ie)[0])
                for ie in ideal_embeddings
            ]
            
            semantic_score = max(similarities) if similarities else 0.5
            
            # Store top matches for transparency
            top_matches = sorted(
                zip(ideal_responses, similarities),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            result["top_matches"] = [(text, float(sim)) for text, sim in top_matches]
            
            # Keyword coverage
            keyword_coverage = 0.5
            if required_keywords:
                response_lower = response.lower()
                keywords_found = sum(1 for kw in required_keywords if kw.lower() in response_lower)
                keyword_coverage = keywords_found / len(required_keywords) if required_keywords else 0.5
            
            # Combined: 70% semantic, 30% keyword
            combined_score = 0.7 * semantic_score + 0.3 * keyword_coverage
            
            result.update({
                "semantic_score": float(semantic_score),
                "keyword_coverage": float(keyword_coverage),
                "combined_score": float(combined_score),
                "reasoning": f"Semantic similarity: {semantic_score:.2f}, Keywords: {keyword_coverage:.0%}",
            })
            
            logger.debug(f"Semantic evaluation: score={combined_score:.3f}")
            
        except Exception as e:
            logger.error(f"Semantic evaluation failed: {e}")
            result["reasoning"] = f"Evaluation error: {str(e)[:50]}"
        
        return result


# Singleton instance
_evaluator: Optional[SemanticResponseEvaluator] = None


def get_semantic_evaluator() -> SemanticResponseEvaluator:
    """Get or create semantic evaluator singleton."""
    global _evaluator
    if _evaluator is None:
        _evaluator = SemanticResponseEvaluator()
    return _evaluator
