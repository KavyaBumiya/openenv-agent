#!/usr/bin/env python
"""Generate synthetic tickets for training."""

from customer_support_env.synthetic_generator import SyntheticTicketGenerator

gen = SyntheticTicketGenerator(seed=42)
tickets = gen.generate(count=120)
gen.save_to_file(tickets, "synthetic_tickets.json")
print(f"✓ Generated {len(tickets)} synthetic tickets")
print(f"  Sample: {tickets[0]['id']} - {tickets[0]['subject'][:60]}")
