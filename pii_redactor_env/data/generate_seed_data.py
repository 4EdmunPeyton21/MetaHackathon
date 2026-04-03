"""
pii_redactor_env/data/generate_seed_data.py
--------------------------------------------
Generates reproducible synthetic PII datasets using Faker.

Run:
    python -m pii_redactor_env.data.generate_seed_data

Outputs:
    data/easy/customers.csv    — 500 rows, ~30% with CC numbers
    data/medium/chat_logs.txt  — 200 chat messages with SSNs
    data/hard/records.json     — 50 nested customer records with mixed PII
"""

from __future__ import annotations

import csv
import json
import os
import random
from pathlib import Path

try:
    from faker import Faker
except ImportError:
    print("Faker is required: pip install faker")
    raise

# Reproducibility
SEED = 42
fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

# Output directory (relative to this script)
BASE_DIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════
# EASY: customers.csv — 500 rows, ~30% with CC in notes
# ═══════════════════════════════════════════════════════════════

def _generate_cc() -> str:
    """Generate a fake credit card number in a random format."""
    digits = fake.credit_card_number(card_type=None)
    fmt = random.choice(["raw", "dashed", "spaced"])
    if fmt == "dashed" and len(digits) == 16:
        return f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:]}"
    elif fmt == "spaced" and len(digits) == 16:
        return f"{digits[:4]} {digits[4:8]} {digits[8:12]} {digits[12:]}"
    return digits


CC_NOTE_TEMPLATES = [
    "Payment with card {cc}",
    "CC: {cc} on file",
    "Card number {cc} for auto-pay",
    "Billing card: {cc}",
    "Auto-pay card: {cc}",
    "Card {cc} used for subscription",
    "Charged to {cc} on last order",
    "Refund issued to card {cc}",
]

CLEAN_NOTES = [
    "Regular customer",
    "No special notes",
    "Preferred customer since 2019",
    "Loyal customer",
    "VIP member",
    "Customer since 2020",
    "Requires signature on delivery",
    "Standard account",
    "Seasonal buyer",
    "Call before delivery",
    "Corporate account",
    "Wholesale pricing applied",
    "Free shipping eligible",
    "Returns frequently",
    "Gift buyer — holiday season",
    "Referred by existing customer",
    "No notes",
    "",
]


def generate_easy_csv(num_rows: int = 500) -> None:
    """Generate customers.csv with CC numbers injected in ~30% of notes."""
    output_path = BASE_DIR / "easy" / "customers.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["id", "first_name", "last_name", "email", "phone", "address", "notes"]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(1, num_rows + 1):
            first = fake.first_name()
            last = fake.last_name()

            # ~30% chance of CC in notes
            if random.random() < 0.30:
                cc = _generate_cc()
                template = random.choice(CC_NOTE_TEMPLATES)
                notes = template.format(cc=cc)
            else:
                notes = random.choice(CLEAN_NOTES)

            writer.writerow({
                "id": i,
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower()}@{fake.free_email_domain()}",
                "phone": f"555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
                "address": fake.street_address(),
                "notes": notes,
            })

    print(f"  ✓ Generated {output_path} ({num_rows} rows)")


# ═══════════════════════════════════════════════════════════════
# MEDIUM: chat_logs.txt — 200 messages with SSNs in ~15%
# ═══════════════════════════════════════════════════════════════

USERNAMES = ["sarah_j", "mike_d", "lisa_m", "alex_k", "priya_s", "tom_w", "emma_r"]

SSN_MESSAGE_TEMPLATES = [
    "Customer provided SSN {ssn} for identity verification",
    "Verified identity with SSN {ssn}",
    "SSN on file: {ssn}",
    "my SSN is {ssn}",
    "Customer's SSN {ssn} confirmed",
    "Please verify SSN {ssn} against records",
    "Update SSN to {ssn} per customer request",
]

CLEAN_MESSAGE_TEMPLATES = [
    "Good morning everyone!",
    "Let me pull up my notes.",
    "Order #{order_id} is pending review.",
    "I need help with ticket #{ticket_id}.",
    "Revenue this quarter hit {amount} million.",
    "My team closed {count} tickets last week.",
    "The new batch import has {count} records to process.",
    "I'll update the dashboard by 5 PM.",
    "Customer callback number is 555-{phone}.",
    "Extension is {ext}.",
    "Product ID for the new release is PRD-{prod_id}.",
    "Meeting starts at {time}.",
    "Can someone review PR #{pr_id}?",
    "That should be handled through the secure portal.",
    "Send that through HR, not here.",
    "Let's wrap up. Any other items?",
    "Thanks all!",
    "Sounds good, will follow up.",
    "Budget for Q2 is ${budget}.",
    "We processed {count} refunds yesterday.",
    "Server uptime is at 99.{uptime}%.",
    "Deployment scheduled for {date}.",
]


def _generate_ssn() -> str:
    """Generate a fake SSN in format XXX-XX-XXXX."""
    return f"{random.randint(100, 899):03d}-{random.randint(10, 99):02d}-{random.randint(1000, 9999):04d}"


def generate_medium_chat(num_messages: int = 200) -> None:
    """Generate chat_logs.txt with SSNs injected in ~15% of messages."""
    output_path = BASE_DIR / "medium" / "chat_logs.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    hour, minute, second = 9, 0, 0

    for i in range(num_messages):
        # Advance timestamp
        second += random.randint(10, 45)
        if second >= 60:
            minute += second // 60
            second = second % 60
        if minute >= 60:
            hour += minute // 60
            minute = minute % 60

        timestamp = f"[{hour:02d}:{minute:02d}:{second:02d}]"
        user = random.choice(USERNAMES)

        # ~15% chance of SSN message
        if random.random() < 0.15:
            ssn = _generate_ssn()
            template = random.choice(SSN_MESSAGE_TEMPLATES)
            message = template.format(ssn=ssn)
        else:
            template = random.choice(CLEAN_MESSAGE_TEMPLATES)
            message = template.format(
                order_id=random.randint(10000, 99999),
                ticket_id=random.randint(1000, 99999),
                amount=round(random.uniform(0.5, 50.0), 1),
                count=random.randint(10, 5000),
                phone=f"{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
                ext=random.randint(1000, 9999),
                prod_id=f"{random.randint(20230101, 20260401)}",
                time=f"{random.randint(9, 17):02d}:{random.choice(['00', '15', '30', '45'])}",
                pr_id=random.randint(100, 9999),
                budget=f"{random.randint(10, 500)},{random.randint(0, 999):03d}",
                uptime=random.randint(90, 99),
                date=fake.date_this_year().isoformat(),
            )

        lines.append(f"{timestamp} {user}: {message}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  ✓ Generated {output_path} ({num_messages} messages)")


# ═══════════════════════════════════════════════════════════════
# HARD: records.json — 50 nested customer records with mixed PII
# ═══════════════════════════════════════════════════════════════

def _generate_customer_record(cust_id: int) -> dict:
    """Generate a single deeply nested customer record with mixed PII."""
    first = fake.first_name()
    last = fake.last_name()
    email = f"{first.lower()}.{last.lower()}@{fake.domain_name()}"
    phone = f"({random.randint(200, 999):03d}) {random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}"
    ssn = _generate_ssn()

    # Generate 1-3 orders
    orders = []
    for j in range(random.randint(1, 3)):
        cc = _generate_cc()
        order = {
            "order_id": f"ORD-{random.randint(10000, 99999)}",
            "date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "total": round(random.uniform(10.0, 2000.0), 2),
            "payment": {
                "method": "credit_card",
                "card_number": cc,
                "expiry": f"{random.randint(1, 12):02d}/{random.randint(25, 30):02d}",
            },
            "items": [
                {
                    "sku": f"PROD-{random.randint(1, 500):03d}",
                    "name": fake.word().capitalize() + " " + random.choice(["Pro", "Kit", "Pack", "Set", "Bundle"]),
                    "qty": random.randint(1, 10),
                    "price": round(random.uniform(5.0, 500.0), 2),
                }
                for _ in range(random.randint(1, 4))
            ],
        }
        orders.append(order)

    # Generate 0-2 support tickets
    tickets = []
    for j in range(random.randint(0, 2)):
        # Build transcript that might include PII
        transcript_parts = [
            f"Customer {first} {last} contacted support.",
        ]
        if random.random() < 0.5:
            transcript_parts.append(f"Verified with SSN {ssn}.")
        if random.random() < 0.4:
            transcript_parts.append(f"Email on file: {email}.")
        if random.random() < 0.3:
            transcript_parts.append(f"Callback number: {phone}.")
        transcript_parts.append(f"Issue resolved with ${random.randint(10, 200)} credit.")

        tickets.append({
            "ticket_id": f"TKT-{random.randint(1000, 99999)}",
            "date": fake.date_between(start_date="-6m", end_date="today").isoformat(),
            "status": random.choice(["resolved", "open", "pending", "escalated"]),
            "priority": random.choice(["low", "medium", "high"]),
            "transcript": " ".join(transcript_parts),
        })

    return {
        "id": f"CUST-{cust_id:03d}",
        "profile": {
            "first_name": first,
            "last_name": last,
            "contact": {
                "email": email,
                "phone": phone,
                "address": {
                    "street": fake.street_address(),
                    "city": fake.city(),
                    "state": fake.state_abbr(),
                    "zip": fake.zipcode(),
                },
            },
            "ssn": ssn,
        },
        "orders": orders,
        "support_tickets": tickets,
        "loyalty_points": random.randint(0, 10000),
        "account_status": random.choice(["active", "inactive", "suspended"]),
    }


def generate_hard_json(num_customers: int = 50) -> None:
    """Generate records.json with deeply nested mixed PII."""
    output_path = BASE_DIR / "hard" / "records.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "company": "Acme Data Corp",
        "export_date": "2024-03-15",
        "version": "2.1.0",
        "customers": [
            _generate_customer_record(i) for i in range(1, num_customers + 1)
        ],
        "metadata": {
            "total_customers": num_customers,
            "generated_by": "seed_data_generator_v1",
            "contains_pii": True,
            "pii_types": ["credit_card", "ssn", "email", "phone"],
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Generated {output_path} ({num_customers} customers)")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def generate_all() -> None:
    """Generate all three seed datasets."""
    print("Generating seed data...")
    generate_easy_csv(num_rows=500)
    generate_medium_chat(num_messages=200)
    generate_hard_json(num_customers=50)
    print("\nDone! All seed data generated.")


if __name__ == "__main__":
    generate_all()
