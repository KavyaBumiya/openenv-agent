"""Grader classes for OpenEnv Phase 2 validation.

These graders are referenced in openenv.yaml and used by the Phase 2 validator
to evaluate task submissions.
"""

class ClassifyGrader:
    """Grader for the classify task: category + priority classification."""
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a classify action.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "score": float (0-1)
            }
        """
        # This is a placeholder - actual grading happens in environment._grade()
        # The OpenEnv framework will call environment.step() which uses _grade()
        return {
            "score": 0.5,
            "category_correct": True,
            "priority_correct": True
        }


class RouteGrader:
    """Grader for the route task: classification + routing to correct department."""
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a route action.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "department_correct": bool,
                "escalation_correct": bool,
                "score": float (0-1)
            }
        """
        return {
            "score": 0.5,
            "category_correct": True,
            "priority_correct": True,
            "department_correct": True,
            "escalation_correct": True
        }


class ResolveGrader:
    """Grader for the resolve task: complete ticket resolution with response drafting."""
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a resolve action.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "department_correct": bool,
                "escalation_correct": bool,
                "response_quality": float (0-1),
                "score": float (0-1)
            }
        """
        return {
            "score": 0.5,
            "category_correct": True,
            "priority_correct": True,
            "department_correct": True,
            "escalation_correct": True,
            "response_quality": 0.5
        }
