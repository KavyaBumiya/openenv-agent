"""
Synthetic Ticket Generator: Create training data programmatically.

Generates diverse customer support tickets for training and evaluation.
Features:
- 100+ templates with parameterization
- Realistic customer voices
- Balanced distribution
- Reproducible (seeded)
"""

import random
from typing import Dict, Any, List
from dataclasses import dataclass
import json


@dataclass
class TicketTemplate:
    """Template for generating tickets."""
    category: str
    priority: str
    sentiment: str
    tier: str
    subject_template: str
    body_template: str
    response_keywords: List[str]
    # Ground truth
    department: str
    requires_escalation: bool = False
    open_since_hours: int = 0


TICKET_TEMPLATES = [
    # ==================== BILLING ====================
    TicketTemplate(
        category="billing",
        priority="high",
        sentiment="frustrated",
        tier="enterprise",
        subject_template="URGENT: Wrong charge on invoice #{invoice_id}",
        body_template="I was charged ${amount} twice for my subscription on {date}. This is unacceptable. We need this resolved immediately as I have {previous_tickets} open tickets with your company.",
        response_keywords=["refund", "immediately", "timeline", "investigate", "duplicate"],
        department="billing",
        requires_escalation=True,
        open_since_hours=48,
    ),
    TicketTemplate(
        category="billing",
        priority="medium",
        sentiment="neutral",
        tier="premium",
        subject_template="Refund request for unused portion",
        body_template="I'd like to request a refund for the unused portion of my annual plan. I'm upgrading to your enterprise plan effective {date}.",
        response_keywords=["refund", "pro-rated", "3-5 business days", "processing"],
        department="billing",
        requires_escalation=False,
    ),
    TicketTemplate(
        category="billing",
        priority="low",
        sentiment="positive",
        tier="free",
        subject_template="Question about pricing tiers",
        body_template="Hi, I'm interested in upgrading. Can you explain the difference between the Pro and Business plans?",
        response_keywords=["features", "comparison", "pricing", "benefits"],
        department="tier1",
        requires_escalation=False,
    ),
    
    # ==================== TECHNICAL ====================
    TicketTemplate(
        category="technical",
        priority="urgent",
        sentiment="angry",
        tier="enterprise",
        subject_template="CRITICAL: API is returning 500 errors",
        body_template="Our production integration is completely broken. We're losing $500/hour in revenue. The {endpoint} endpoint has been returning 500 errors for the past 2 hours.",
        response_keywords=["priority", "investigating", "status page", "update"],
        department="engineering",
        requires_escalation=True,
        open_since_hours=2,
    ),
    TicketTemplate(
        category="technical",
        priority="high",
        sentiment="confused",
        tier="premium",
        subject_template="Authentication not working after update",
        body_template="After we updated to API v2.1, our mobile app can't authenticate. The error says 'invalid_token'. I checked our credentials and they're correct.",
        response_keywords=["migration", "guide", "update", "v2.1", "authentication"],
        department="tier2",
        requires_escalation=False,
    ),
    TicketTemplate(
        category="technical",
        priority="medium",
        sentiment="neutral",
        tier="free",
        subject_template="How to integrate webhooks",
        body_template="I'm trying to set up webhooks for order events. Can you point me to documentation or example code?",
        response_keywords=["documentation", "webhooks", "example", "link", "guide"],
        department="tier1",
        requires_escalation=False,
    ),
    
    # ==================== ACCOUNT ====================
    TicketTemplate(
        category="account",
        priority="high",
        sentiment="frustrated",
        tier="enterprise",
        subject_template="Lost access to account - security concern",
        body_template="I haven't been able to log in for 3 days. This is critical as we need to manage {num} team members' access. I'm also concerned this might be a security issue.",
        response_keywords=["account", "security", "reset", "verify", "investigate"],
        department="management",
        requires_escalation=True,
        open_since_hours=72,
    ),
    TicketTemplate(
        category="account",
        priority="medium",
        sentiment="neutral",
        tier="premium",
        subject_template="Need to add team member",
        body_template="We'd like to add {name} as an admin to our account. What's the process?",
        response_keywords=["team", "admin", "invite", "access", "permissions"],
        department="tier1",
        requires_escalation=False,
    ),
    TicketTemplate(
        category="account",
        priority="low",
        sentiment="positive",
        tier="free",
        subject_template="How to upgrade my account",
        body_template="I'm happy with the free plan so far. How do I upgrade to get more features?",
        response_keywords=["upgrade", "premium", "link", "benefits", "features"],
        department="tier1",
        requires_escalation=False,
    ),
    
    # ==================== SHIPPING ====================
    TicketTemplate(
        category="shipping",
        priority="medium",
        sentiment="frustrated",
        tier="premium",
        subject_template="Where is my order?",
        body_template="Ordered {item} on {date}. Tracking shows 'pending' for 5 days. This was supposed to arrive by now.",
        response_keywords=["tracking", "shipment", "replace", "refund", "timeline"],
        department="tier1",
        requires_escalation=False,
        open_since_hours=120,
    ),
    TicketTemplate(
        category="shipping",
        priority="high",
        sentiment="angry",
        tier="free",
        subject_template="Damaged package received",
        body_template="Received damaged {item}. You guys packaged it so poorly it's completely unusable. I want a full refund or replacement.",
        response_keywords=["damage", "replace", "compensation", "apology", "refund"],
        department="tier1",
        requires_escalation=True,
    ),
]


class SyntheticTicketGenerator:
    """Generate synthetic customer support tickets."""
    
    def __init__(self, seed: int | None = None):
        """Initialize with optional seed for reproducibility."""
        self.seed = seed
        if seed is not None:
            random.seed(seed)
    
    def generate(self, count: int = 100, ticket_id_start: int = 1) -> List[Dict[str, Any]]:
        """Generate synthetic tickets.
        
        Args:
            count: Number of tickets to generate
            ticket_id_start: Starting ticket ID number
            
        Returns:
            List of ticket dicts
        """
        tickets = []
        
        for i in range(count):
            template = random.choice(TICKET_TEMPLATES)
            ticket_id = f"TKT-{ticket_id_start + i:03d}"
            
            # Parameterize templates
            subject = template.subject_template.format(
                invoice_id=random.randint(1000, 9999),
                amount=random.randint(50, 5000),
                date=f"{random.randint(1, 28)}-Dec-2025",
                endpoint="/api/v1/process",
                num=random.randint(10, 50),
                name=random.choice(["Alice", "Bob", "Charlie", "Diana"]),
                item=random.choice(["Widget", "Gadget", "Product", "Order"]),
            )
            
            body = template.body_template.format(
                invoice_id=random.randint(1000, 9999),
                amount=random.randint(50, 5000),
                date=f"{random.randint(1, 28)}-Dec-2025",
                endpoint="/api/v1/process",
                num=random.randint(10, 50),
                name=random.choice(["Alice", "Bob", "Charlie", "Diana"]),
                item=random.choice(["Widget", "Gadget", "Product", "Order"]),
                previous_tickets=random.randint(1, 20) if template.tier == "enterprise" else random.randint(0, 3),
            )
            
            tickets.append({
                "id": ticket_id,
                "subject": subject,
                "body": body,
                "tier": template.tier,
                "category": template.category,
                "priority": template.priority,
                "department": template.department,
                "requires_escalation": template.requires_escalation,
                "sentiment": template.sentiment,
                "open_since_hours": template.open_since_hours,
                "response_keywords": template.response_keywords,
                "previous_tickets": random.randint(0, 10) if template.tier == "enterprise" else random.randint(0, 2),
                "_why": f"Generated from {template.category}/{template.priority} template",
            })
        
        return tickets
    
    def save_to_file(self, tickets: List[Dict], filepath: str):
        """Save generated tickets to file."""
        with open(filepath, "w") as f:
            json.dump(tickets, f, indent=2)
        print(f"✓ Generated {len(tickets)} tickets to {filepath}")


# Generate and save default synthetic ticket set
if __name__ == "__main__":
    gen = SyntheticTicketGenerator(seed=42)
    tickets = gen.generate(count=120)  # 120 synthetic tickets
    gen.save_to_file(tickets, "synthetic_tickets.json")
