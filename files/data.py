"""
customer_support_env/data.py
────────────────────────────
30 curated customer-support tickets used as the environment dataset.

Design principles:
  - Authentic customer voices (typos, frustration, urgency)
  - Explicit _why field documents the label rationale
  - Balanced distribution across categories, tiers, and sentiments
  - Edge cases included to challenge frontier models
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Schema constants
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED = {
    "tier":       {"free", "premium", "enterprise"},
    "category":   {"billing", "technical", "account", "shipping", "general"},
    "priority":   {"low", "medium", "high", "urgent"},
    "department": {"tier1", "tier2", "billing", "engineering", "management"},
    "sentiment":  {"frustrated", "angry", "positive", "neutral", "confused", "urgent"},
}

REQUIRED_FIELDS = {
    "id":                  str,
    "subject":             str,
    "body":                str,
    "tier":                str,
    "category":            str,
    "priority":            str,
    "department":          str,
    "previous_tickets":    int,
    "requires_escalation": bool,
    "open_since_hours":    int,
    "sentiment":           str,
    "response_keywords":   list,
}


def validate_tickets() -> None:
    """Validate all tickets; raises RuntimeError listing every problem found."""
    errors: list[str] = []

    for idx, ticket in enumerate(TICKETS):
        tid = ticket.get("id", f"#{idx}") if isinstance(ticket, dict) else f"#{idx}"

        if not isinstance(ticket, dict):
            errors.append(f"{tid}: must be a dict")
            continue

        for field, ftype in REQUIRED_FIELDS.items():
            if field not in ticket:
                errors.append(f"{tid}: missing '{field}'")
                continue

            val = ticket[field]
            if not isinstance(val, ftype):
                errors.append(
                    f"{tid}.{field}: expected {ftype.__name__}, got {type(val).__name__}"
                )
                continue

            if field in ALLOWED and val not in ALLOWED[field]:
                errors.append(
                    f"{tid}.{field}: '{val}' not in {sorted(ALLOWED[field])}"
                )

            if field == "subject" and len(str(val).strip()) < 5:
                errors.append(f"{tid}.subject: too short (min 5 chars)")
            if field == "body" and len(str(val).strip()) < 20:
                errors.append(f"{tid}.body: too short (min 20 chars)")
            if field == "response_keywords":
                if len(val) < 2:
                    errors.append(f"{tid}.response_keywords: need at least 2 items")
                if not all(isinstance(k, str) for k in val):
                    errors.append(f"{tid}.response_keywords: all items must be strings")

    if errors:
        msg = f"Ticket data invalid ({len(errors)} errors):\n" + "\n".join(errors)
        raise RuntimeError(msg)

    logger.debug("validate_tickets: all %d tickets OK", len(TICKETS))


# ─────────────────────────────────────────────────────────────────────────────
# Dataset  (30 tickets)
# ─────────────────────────────────────────────────────────────────────────────

TICKETS: list[dict] = [
    # ── BILLING (7) ──────────────────────────────────────────────────────────
    {
        "id": "TKT-001",
        "subject": "Wrong amount charged on my account",
        "body": (
            "I was charged $49.99 but I only selected the $29.99 plan. "
            "This happened two days ago and I haven't been able to reach support. "
            "I need this refunded ASAP. Can you help?"
        ),
        "tier": "premium",
        "category": "billing",
        "priority": "high",
        "department": "billing",
        "previous_tickets": 2,
        "requires_escalation": False,
        "open_since_hours": 28,
        "sentiment": "frustrated",
        "response_keywords": ["refund", "investigate", "resolved", "timeline"],
        "_why": (
            "Classic overcharge. Premium + open 28 h → high (not urgent — fixable within SLA). "
            "Billing dept handles charge disputes, not tier1."
        ),
    },
    {
        "id": "TKT-002",
        "subject": "Charged twice for subscription renewal",
        "body": (
            "My card was debited twice yesterday when my subscription renewed. "
            "I have two charges for the same month. This is really frustrating. "
            "Please reverse one charge."
        ),
        "tier": "enterprise",
        "category": "billing",
        "priority": "urgent",
        "department": "billing",
        "previous_tickets": 3,
        "requires_escalation": True,
        "open_since_hours": 6,
        "sentiment": "frustrated",
        "response_keywords": ["duplicate", "refund", "investigate", "timeline", "sorry"],
        "_why": (
            "Duplicate charge on enterprise account → financial trust risk → urgent. "
            "Escalation required because enterprise billing errors impact retention."
        ),
    },
    {
        "id": "TKT-003",
        "subject": "Can I downgrade to a cheaper plan",
        "body": (
            "I've been on the Pro plan for 8 months but I realize I don't use all the features. "
            "Can I switch to the basic plan instead? "
            "Will I get a refund for the difference in this billing cycle?"
        ),
        "tier": "free",
        "category": "billing",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 15,
        "sentiment": "neutral",
        "response_keywords": ["process", "refund", "downgrade", "effective"],
        "_why": "FAQ-level billing question. Free tier, no urgency. Tier1 handles plan changes.",
    },
    {
        "id": "TKT-004",
        "subject": "Invoice discrepancy for Q4",
        "body": (
            "Our account was invoiced for 15 licenses in December, but we only activated 12. "
            "We need a credit for the 3 unused licenses. Please review and adjust the invoice."
        ),
        "tier": "enterprise",
        "category": "billing",
        "priority": "high",
        "department": "billing",
        "previous_tickets": 8,
        "requires_escalation": False,
        "open_since_hours": 48,
        "sentiment": "neutral",
        "response_keywords": ["review", "credit", "invoice", "resolve"],
        "_why": "Enterprise invoice dispute. High priority (48 h open, SLA pressure). Billing dept.",
    },
    {
        "id": "TKT-005",
        "subject": "My payment method was declined",
        "body": (
            "I tried to renew my subscription but my credit card was declined. "
            "It's the same card that worked last month. "
            "I don't understand why it's failing. Can you help me renew?"
        ),
        "tier": "premium",
        "category": "billing",
        "priority": "medium",
        "department": "tier1",
        "previous_tickets": 1,
        "requires_escalation": False,
        "open_since_hours": 8,
        "sentiment": "neutral",
        "response_keywords": ["card", "retry", "contact", "renew"],
        "_why": "Payment troubleshooting — not an error on our side. Tier1 walks through retry steps.",
    },
    {
        "id": "TKT-006",
        "subject": "Refund request - dissatisfied with service",
        "body": (
            "I signed up last week but the service isn't meeting my needs. "
            "I'd like to request a refund within the 14-day window. "
            "Can you process that for me?"
        ),
        "tier": "free",
        "category": "billing",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 2,
        "sentiment": "neutral",
        "response_keywords": ["refund", "policy", "process", "timeline"],
        "_why": "Within-policy refund. Free tier. Tier1 follows standard refund script.",
    },
    {
        "id": "TKT-007",
        "subject": "Bulk discount eligibility question",
        "body": (
            "We're a small nonprofit looking to bring your solution to 50+ users. "
            "Do you offer nonprofit discounts or volume pricing? "
            "What would our pricing look like?"
        ),
        "tier": "premium",
        "category": "billing",
        "priority": "medium",
        "department": "billing",
        "previous_tickets": 5,
        "requires_escalation": False,
        "open_since_hours": 12,
        "sentiment": "neutral",
        "response_keywords": ["discount", "pricing", "volume", "inquiry"],
        "_why": "Volume pricing inquiry. Billing dept handles custom quotes.",
    },

    # ── TECHNICAL (7) ────────────────────────────────────────────────────────
    {
        "id": "TKT-008",
        "subject": "Can't log in to my account",
        "body": (
            "I keep getting 'invalid credentials' even though I'm 100% sure my password is correct. "
            "I've tried resetting it but the reset email never arrives. "
            "This is blocking me from accessing my data."
        ),
        "tier": "premium",
        "category": "technical",
        "priority": "urgent",
        "department": "engineering",
        "previous_tickets": 4,
        "requires_escalation": True,
        "open_since_hours": 3,
        "sentiment": "frustrated",
        "response_keywords": ["investigate", "account", "access", "restore"],
        "_why": "Blocking login failure + broken email reset = urgent. Engineering needs access logs.",
    },
    {
        "id": "TKT-009",
        "subject": "API endpoint returning 500 errors randomly",
        "body": (
            "The /data/export endpoint is intermittently returning 500 Internal Server Error. "
            "This happens maybe 20% of the time. The rest of the API works fine. "
            "Can you check the logs?"
        ),
        "tier": "enterprise",
        "category": "technical",
        "priority": "urgent",
        "department": "engineering",
        "previous_tickets": 12,
        "requires_escalation": True,
        "open_since_hours": 1,
        "sentiment": "neutral",
        "response_keywords": ["investigate", "logs", "error", "fix"],
        "_why": "Enterprise production API 500s = urgent. Engineering immediate response.",
    },
    {
        "id": "TKT-010",
        "subject": "Export function is very slow on large datasets",
        "body": (
            "When I try to export 500k records, it takes about 15 minutes and sometimes times out. "
            "The UI just hangs. Is there a faster way? Other tools do this instantly."
        ),
        "tier": "premium",
        "category": "technical",
        "priority": "high",
        "department": "engineering",
        "previous_tickets": 3,
        "requires_escalation": False,
        "open_since_hours": 18,
        "sentiment": "frustrated",
        "response_keywords": ["performance", "optimization", "workaround", "timeline"],
        "_why": "Performance issue degrading workflow. Premium + 18 h open → high. Engineering.",
    },
    {
        "id": "TKT-011",
        "subject": "Mobile app keeps crashing on iOS 18",
        "body": (
            "The iOS app crashes as soon as I open it on my iPhone 15. "
            "I've tried uninstalling and reinstalling. I'm on iOS 18.2. Is this a known issue?"
        ),
        "tier": "free",
        "category": "technical",
        "priority": "high",
        "department": "tier2",
        "previous_tickets": 1,
        "requires_escalation": False,
        "open_since_hours": 24,
        "sentiment": "frustrated",
        "response_keywords": ["iOS", "crash", "logs", "workaround"],
        "_why": "OS-version crash. High priority (could affect many users). Tier2 gathers diagnostics.",
    },
    {
        "id": "TKT-012",
        "subject": "Database connection issues after migration",
        "body": (
            "After you migrated our data yesterday, we're seeing intermittent 'database unavailable' errors. "
            "Our production app is affected. Can you check on our connection pool?"
        ),
        "tier": "enterprise",
        "category": "technical",
        "priority": "urgent",
        "department": "engineering",
        "previous_tickets": 6,
        "requires_escalation": True,
        "open_since_hours": 4,
        "sentiment": "urgent",
        "response_keywords": ["migration", "connection", "investigate", "production"],
        "_why": "Post-migration prod outage. Enterprise + urgent sentiment. Engineering immediately.",
    },
    {
        "id": "TKT-013",
        "subject": "Question about API rate limits",
        "body": (
            "I'm reading the docs and I'm confused about how rate limiting works. "
            "Is it per-second, per-minute, or per hour? And does it reset automatically? "
            "I want to make sure I design my integration correctly."
        ),
        "tier": "premium",
        "category": "technical",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 2,
        "requires_escalation": False,
        "open_since_hours": 6,
        "sentiment": "neutral",
        "response_keywords": ["rate limits", "documentation", "integration", "example"],
        "_why": "Documentation question, not an incident. Tier1 links to docs.",
    },
    {
        "id": "TKT-014",
        "subject": "Feature request: bulk delete capability",
        "body": (
            "I'd really love a bulk delete feature. "
            "Right now I can only delete one item at a time and it's tedious when I have thousands. "
            "Would this be something you could add?"
        ),
        "tier": "free",
        "category": "general",
        "priority": "low",
        "department": "engineering",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 12,
        "sentiment": "neutral",
        "response_keywords": ["feature", "request", "roadmap", "feedback"],
        "_why": "Feature request — general category. Engineering/product intake. Low priority.",
    },

    # ── ACCOUNT (6) ──────────────────────────────────────────────────────────
    {
        "id": "TKT-015",
        "subject": "Still getting charged after I thought I cancelled",
        "body": (
            "I emailed support 2 weeks ago asking to cancel my account. "
            "I haven't used the service since, but I got a charge yesterday. "
            "Was my cancellation request processed?"
        ),
        "tier": "premium",
        "category": "account",
        "priority": "high",
        "department": "tier2",
        "previous_tickets": 6,
        "requires_escalation": False,
        "open_since_hours": 14,
        "sentiment": "frustrated",
        "response_keywords": ["cancellation", "account", "verify", "charges"],
        "_why": "Core issue is account status, not a charge error. Tier2 investigates cancellation record.",
    },
    {
        "id": "TKT-016",
        "subject": "Can't change my email address",
        "body": (
            "I'm trying to update the email on file but the form keeps rejecting my new email. "
            "It says 'email already in use' but I don't have any other accounts. What's going on?"
        ),
        "tier": "free",
        "category": "account",
        "priority": "medium",
        "department": "tier1",
        "previous_tickets": 1,
        "requires_escalation": False,
        "open_since_hours": 11,
        "sentiment": "confused",
        "response_keywords": ["email", "account", "update", "investigation"],
        "_why": "Account management. Free tier, medium priority. Tier1 checks for duplicate accounts.",
    },
    {
        "id": "TKT-017",
        "subject": "Need to delete all my personal data",
        "body": (
            "I no longer want to use this service and I need all my personal information deleted "
            "in compliance with privacy laws. Can you tell me what data you have and how to request deletion?"
        ),
        "tier": "enterprise",
        "category": "account",
        "priority": "high",
        "department": "management",
        "previous_tickets": 0,
        "requires_escalation": True,
        "open_since_hours": 20,
        "sentiment": "neutral",
        "response_keywords": ["data", "deletion", "gdpr", "process"],
        "_why": "GDPR/privacy request. Enterprise + legal obligation → high + management. Escalation needed.",
    },
    {
        "id": "TKT-018",
        "subject": "I forgot my password",
        "body": (
            "I haven't logged in in 6 months and I forgot my password. "
            "I clicked 'forgot password' but I'm not getting the reset email. What should I do?"
        ),
        "tier": "free",
        "category": "account",
        "priority": "medium",
        "department": "tier1",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 5,
        "sentiment": "neutral",
        "response_keywords": ["password", "reset", "email", "verify"],
        "_why": "Standard account access issue. Tier1 verifies email and resends reset link.",
    },
    {
        "id": "TKT-019",
        "subject": "How do I transfer account ownership after acquisition",
        "body": (
            "My company was acquired and I need to transfer ownership of this account to the new manager. "
            "How does that process work?"
        ),
        "tier": "enterprise",
        "category": "account",
        "priority": "high",
        "department": "tier2",
        "previous_tickets": 2,
        "requires_escalation": False,
        "open_since_hours": 32,
        "sentiment": "neutral",
        "response_keywords": ["transfer", "account", "ownership", "process"],
        "_why": "Enterprise ownership transfer. High priority (SLA pressure). Tier2 handles special admin.",
    },
    {
        "id": "TKT-020",
        "subject": "My account looks compromised",
        "body": (
            "I'm seeing activity from places I've never been and there's an extra team member in my "
            "account that I didn't add. I think someone has access to my account. PLEASE help ASAP!!!"
        ),
        "tier": "premium",
        "category": "account",
        "priority": "urgent",
        "department": "management",
        "previous_tickets": 5,
        "requires_escalation": True,
        "open_since_hours": 2,
        "sentiment": "urgent",
        "response_keywords": ["security", "compromised", "investigate", "emergency"],
        "_why": "Security incident. Premium + urgent language → urgent. Management/security response.",
    },

    # ── GENERAL (5) ──────────────────────────────────────────────────────────
    {
        "id": "TKT-021",
        "subject": "Great service, thanks!",
        "body": (
            "I just wanted to say I've been using your platform for 2 years now and it's been fantastic. "
            "The customer service team is amazing and the product keeps getting better. Keep up the great work!"
        ),
        "tier": "premium",
        "category": "general",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 7,
        "requires_escalation": False,
        "open_since_hours": 1,
        "sentiment": "positive",
        "response_keywords": ["thank", "feedback", "appreciate", "community"],
        "_why": "Positive feedback. Low priority. Tier1 sends thanks and logs as testimonial.",
    },
    {
        "id": "TKT-022",
        "subject": "Interested in partnership opportunities",
        "body": (
            "We run a complementary SaaS product and we think our user bases would benefit from integration. "
            "Would your team be interested in exploring a partnership?"
        ),
        "tier": "premium",
        "category": "general",
        "priority": "low",
        "department": "management",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 3,
        "sentiment": "neutral",
        "response_keywords": ["partnership", "integration", "discuss", "interested"],
        "_why": "Business development inquiry. Management decides on strategic partnerships.",
    },
    {
        "id": "TKT-023",
        "subject": "Documentation typo suggestion",
        "body": (
            "In the API docs section 3.2, there's a typo: 'reciever' should be 'receiver'. "
            "Also, the example could be clearer if you showed error handling. Just wanted to flag this!"
        ),
        "tier": "free",
        "category": "general",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 2,
        "requires_escalation": False,
        "open_since_hours": 8,
        "sentiment": "positive",
        "response_keywords": ["documentation", "typo", "feedback", "thanks"],
        "_why": "Doc quality feedback. Low priority. Tier1 forwards to docs team.",
    },
    {
        "id": "TKT-024",
        "subject": "Webinar invitation and feedback request",
        "body": (
            "We're hosting a webinar on data management best practices and we'd love a speaker from your team. "
            "Would you be interested in participating?"
        ),
        "tier": "enterprise",
        "category": "general",
        "priority": "medium",
        "department": "management",
        "previous_tickets": 4,
        "requires_escalation": False,
        "open_since_hours": 24,
        "sentiment": "neutral",
        "response_keywords": ["webinar", "event", "participation", "discuss"],
        "_why": "Community/partnership event. Enterprise engagement. Management decides participation.",
    },
    {
        "id": "TKT-025",
        "subject": "How to report a security vulnerability responsibly",
        "body": (
            "I found a potential security issue but I don't want to disclose it publicly. "
            "What's your responsible disclosure policy? Who should I contact?"
        ),
        "tier": "premium",
        "category": "general",
        "priority": "high",
        "department": "management",
        "previous_tickets": 1,
        "requires_escalation": True,
        "open_since_hours": 7,
        "sentiment": "neutral",
        "response_keywords": ["security", "responsible", "disclosure", "contact"],
        "_why": "Security disclosure. High priority (safety). Management/security team must respond.",
    },

    # ── SHIPPING (4) ─────────────────────────────────────────────────────────
    {
        "id": "TKT-026",
        "subject": "Where is my physical product order?",
        "body": (
            "I ordered the branded USB drives promotional kit on March 15. "
            "It was supposed to arrive by March 25 but it's still not here. "
            "My tracking number isn't working. Can you check on this?"
        ),
        "tier": "free",
        "category": "shipping",
        "priority": "medium",
        "department": "tier1",
        "previous_tickets": 0,
        "requires_escalation": False,
        "open_since_hours": 36,
        "sentiment": "frustrated",
        "response_keywords": ["tracking", "shipment", "delay", "investigate"],
        "_why": "Missing package. Free tier, medium priority. Tier1 checks carrier status.",
    },
    {
        "id": "TKT-027",
        "subject": "Received damaged hardware",
        "body": (
            "My box arrived today but the device inside was damaged — the screen is cracked and it won't power on. "
            "This is a $800 unit. I need immediate replacement or full refund."
        ),
        "tier": "enterprise",
        "category": "shipping",
        "priority": "urgent",
        "department": "tier2",
        "previous_tickets": 2,
        "requires_escalation": True,
        "open_since_hours": 5,
        "sentiment": "frustrated",
        "response_keywords": ["damaged", "replacement", "return", "urgent"],
        "_why": "Expensive damaged hardware + enterprise = urgent. Tier2 processes emergency replacement.",
    },
    {
        "id": "TKT-028",
        "subject": "Order never arrived after 45 days, need replacement",
        "body": (
            "I placed an order 45 days ago and it never arrived. "
            "I've waited way too long. I just need the replacement sent this week, please."
        ),
        "tier": "premium",
        "category": "shipping",
        "priority": "high",
        "department": "tier1",
        "previous_tickets": 3,
        "requires_escalation": False,
        "open_since_hours": 16,
        "sentiment": "frustrated",
        "response_keywords": ["replacement", "reship", "lost", "timeline"],
        "_why": "Lost package + 45-day wait + premium = high priority. Tier1 authorises replacement.",
    },
    {
        "id": "TKT-029",
        "subject": "Can I expedite my shipment?",
        "body": (
            "I have an event this Saturday and I need my order to arrive by Friday. "
            "I ordered it yesterday and I see it's scheduled to arrive in 7-10 days. "
            "Can you ship it faster? I'll pay for expedited shipping."
        ),
        "tier": "premium",
        "category": "shipping",
        "priority": "low",
        "department": "tier1",
        "previous_tickets": 1,
        "requires_escalation": False,
        "open_since_hours": 2,
        "sentiment": "neutral",
        "response_keywords": ["expedited", "shipping", "rush", "options"],
        "_why": "Shipping upgrade request. Premium, low priority. Tier1 explains options and cost.",
    },

    # ── EDGE CASE (1) ────────────────────────────────────────────────────────
    {
        "id": "TKT-030",
        "subject": "URGENT: I'M FURIOUS AND YOU RUINED MY BUSINESS!!!",
        "body": (
            "This is absolutely unacceptable. I've been trying to reach support for a WEEK and nobody has responded. "
            "My data export failed and I can't access my reports. "
            "THIS IS A TECHNICAL EMERGENCY. You're the worst service I've ever used!!! Fix this NOW!!!"
        ),
        "tier": "enterprise",
        "category": "technical",
        "priority": "urgent",
        "department": "engineering",
        "previous_tickets": 9,
        "requires_escalation": True,
        "open_since_hours": 48,
        "sentiment": "angry",
        "response_keywords": ["understand", "apologize", "export", "immediate"],
        "_why": (
            "ALL_CAPS ≠ change of category. Issue is technical (export failure). "
            "Enterprise + business impact + 48 h open → urgent. Engineering must act."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Validate at import time (raises RuntimeError on bad data, logged not printed)
# ─────────────────────────────────────────────────────────────────────────────
try:
    validate_tickets()
except RuntimeError as _e:
    raise RuntimeError(f"TICKET DATA INVALID: {_e}") from _e
