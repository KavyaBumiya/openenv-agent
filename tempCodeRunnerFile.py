from customer_support_env.models import TicketAction

# Parse the LLM response
result = {'category': 'billing', 'priority': 'high'}

action = TicketAction(
        category=result['category'],
        priority=result['priority'],
        department=None,
        response=None,
        requires_escalation=False
    )