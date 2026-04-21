"""
Sample Data Generator
Creates realistic mock datasets for both agents.
"""

import csv
import random
import os
from datetime import datetime, timedelta


def generate_investor_csv(filepath: str = "data/investors.csv", count: int = 25):
    """Generate a sample investor CSV with realistic data."""

    first_names = ["Sarah", "Michael", "Jennifer", "David", "Emily", "Robert", "Lisa",
                   "James", "Amanda", "Daniel", "Rachel", "Christopher", "Maria", "Kevin",
                   "Laura", "Andrew", "Priya", "Thomas", "Jessica", "Brian", "Aisha",
                   "Nathan", "Michelle", "Alex", "Wei", "Samantha", "Marcus", "Elena",
                   "Ryan", "Olivia"]

    last_names = ["Chen", "Johnson", "Patel", "Williams", "Kim", "Martinez", "Thompson",
                  "Garcia", "Anderson", "Lee", "Taylor", "Brown", "Singh", "Davis",
                  "Wilson", "Moore", "Clark", "Lewis", "Robinson", "Walker", "Young",
                  "Allen", "Wright", "Scott", "Green", "Baker", "Adams", "Nelson",
                  "Hill", "Ramirez"]

    firms = [
        ("Sequoia Capital", "AI/ML, Enterprise SaaS, Deep Tech"),
        ("Andreessen Horowitz", "SaaS, AI Infrastructure, B2B Platforms"),
        ("Accel Partners", "B2B SaaS, Cloud Infrastructure, AI"),
        ("Lightspeed Venture Partners", "Enterprise Software, AI, Fintech"),
        ("Bessemer Venture Partners", "Cloud Computing, SaaS, AI/ML"),
        ("Index Ventures", "SaaS, Marketplace, AI-first Products"),
        ("Greylock Partners", "Enterprise AI, Developer Tools, SaaS"),
        ("Battery Ventures", "B2B Software, Cloud, Automation"),
        ("Insight Partners", "Growth-stage SaaS, AI, Data Analytics"),
        ("Founders Fund", "Deep Tech, AI, Disruptive Technologies"),
        ("Tiger Global", "B2B SaaS, Growth Equity, AI"),
        ("General Catalyst", "AI/ML, Enterprise, Digital Transformation"),
        ("NEA", "Technology, AI, Healthcare AI"),
        ("Khosla Ventures", "AI, Automation, Future Tech"),
        ("Sapphire Ventures", "Enterprise SaaS, AI, Cloud"),
        ("Felicis Ventures", "AI-native Products, SaaS, B2B"),
        ("First Round Capital", "Seed-stage SaaS, AI, CRM"),
        ("Union Square Ventures", "AI Platforms, Network Effects, SaaS"),
        ("Scale Venture Partners", "Enterprise Software, AI, Data"),
        ("Emergence Capital", "Enterprise Cloud, AI, B2B SaaS"),
        ("Redpoint Ventures", "Infrastructure, AI, Enterprise"),
        ("IVP", "Growth-stage SaaS, AI, Automation"),
        ("Point72 Ventures", "AI/ML, Fintech, Data Infrastructure"),
        ("Coatue Management", "Technology, AI, Growth Equity"),
        ("Ribbit Capital", "Fintech, AI, Automation"),
    ]

    investors = []
    used_names = set()

    # Add real contact as first investor
    investors.append({
        "Investor Name": "Sravanakumar Sathish",
        "Email": "sathishsravanakumar@gmail.com",
        "Firm": "TruBot AI (Self)",
        "Investment Focus": "AI/ML, SaaS Automation, CRM Platforms",
    })
    used_names.add("Sravanakumar Sathish")

    for i in range(min(count - 1, len(firms))):
        while True:
            first = random.choice(first_names)
            last = random.choice(last_names)
            name = f"{first} {last}"
            if name not in used_names:
                used_names.add(name)
                break

        firm_name, focus = firms[i]
        email = f"{first.lower()}.{last.lower()}@{firm_name.lower().replace(' ', '').replace('-', '')}.com"

        investors.append({
            "Investor Name": name,
            "Email": email,
            "Firm": firm_name,
            "Investment Focus": focus,
        })

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Investor Name", "Email", "Firm", "Investment Focus"])
        writer.writeheader()
        writer.writerows(investors)

    print(f"✅ Generated {len(investors)} investors → {filepath}")
    return filepath


def generate_crm_dataset(filepath: str = "data/crm_users.csv", count: int = 1000):
    """Generate a 1000-row CRM user dataset with realistic engagement patterns."""

    first_names = [
        "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
        "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia",
        "Lucas", "Harper", "Henry", "Evelyn", "Alexander", "Abigail", "Sebastian",
        "Emily", "Jack", "Elizabeth", "Aiden", "Sofia", "Owen", "Avery", "Samuel",
        "Ella", "Ryan", "Scarlett", "Nathan", "Grace", "Caleb", "Chloe", "Dylan",
        "Victoria", "Luke", "Riley", "Gabriel", "Aria", "Matthew", "Lily", "Leo",
        "Zoey", "Daniel", "Penelope", "Jayden", "Priya", "Raj", "Aisha", "Omar",
        "Yuki", "Min", "Wei", "Sana", "Carlos", "Fatima", "Hassan", "Chen",
        "Mei", "Akira", "Rosa", "Ahmed", "Leila", "Ivan", "Katya", "Dmitri",
    ]

    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
        "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
        "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
        "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Roberts", "Patel", "Singh", "Kim", "Chen", "Shah", "Kumar",
        "Das", "Li", "Wang", "Tanaka", "Sato", "Yamamoto", "Petrov", "Ivanov",
    ]

    companies = [
        "TechStart Inc", "GrowthCo", "DataDriven LLC", "SmartBiz Solutions",
        "InnovateCorp", "DigitalFirst Co", "CloudPeak", "NextGen Retail",
        "SwiftOps", "BlueSky Analytics", "PrimeScale", "VelocityIO",
        "Brightpath", "CoreMetrics", "AlphaFlow", "ZenithTech",
        "Meridian Labs", "PulsePoint", "Catalyst HQ", "Summit Digital",
    ]

    plans = ["free", "starter", "pro", "enterprise"]
    plan_weights = [0.40, 0.30, 0.20, 0.10]

    features = ["Campaign Builder", "Email Templates", "Analytics Dashboard",
                "CRM Contacts", "Automation Rules", "Reports", "Integrations",
                "AI Assistant", "Smart Segments", "A/B Testing"]

    now = datetime.now()
    users = []
    used_emails = set()

    # Add real contact as first CRM user (high-intent power user)
    users.append({
        "Name": "Sravanakumar Sathish",
        "Email": "sathishsravanakumar@gmail.com",
        "Company": "TruBot AI",
        "Last Activity": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
        "Page Views": 150,
        "Sessions": 45,
        "Purchases": 6,
        "Plan": "pro",
        "Feature Used": "AI Campaign Builder",
    })
    used_emails.add("sathishsravanakumar@gmail.com")

    for i in range(count - 1):
        first = random.choice(first_names)
        last = random.choice(last_names)
        company = random.choice(companies)
        name = f"{first} {last}"

        # Generate unique email
        email_base = f"{first.lower()}.{last.lower()}"
        domain = company.lower().replace(" ", "").replace(",", "") + ".com"
        email = f"{email_base}@{domain}"
        suffix = 1
        while email in used_emails:
            email = f"{email_base}{suffix}@{domain}"
            suffix += 1
        used_emails.add(email)

        # Create user profile with realistic engagement patterns
        # Profile type determines engagement pattern
        profile_type = random.choices(
            ["power_user", "regular", "casual", "churned"],
            weights=[0.15, 0.30, 0.25, 0.30],
        )[0]

        if profile_type == "power_user":
            days_since = random.randint(0, 7)
            page_views = random.randint(50, 200)
            sessions = random.randint(15, 60)
            purchases = random.randint(2, 10)
            plan = random.choices(plans, weights=[0.05, 0.15, 0.50, 0.30])[0]
        elif profile_type == "regular":
            days_since = random.randint(1, 30)
            page_views = random.randint(15, 80)
            sessions = random.randint(5, 25)
            purchases = random.randint(0, 4)
            plan = random.choices(plans, weights=[0.15, 0.40, 0.35, 0.10])[0]
        elif profile_type == "casual":
            days_since = random.randint(15, 89)
            page_views = random.randint(3, 25)
            sessions = random.randint(1, 10)
            purchases = random.randint(0, 1)
            plan = random.choices(plans, weights=[0.60, 0.25, 0.10, 0.05])[0]
        else:  # churned
            days_since = random.randint(90, 365)
            page_views = random.randint(0, 15)
            sessions = random.randint(0, 5)
            purchases = random.randint(0, 1)
            plan = random.choices(plans, weights=[0.80, 0.15, 0.04, 0.01])[0]

        last_activity = (now - timedelta(days=days_since)).strftime("%Y-%m-%d")

        users.append({
            "Name": name,
            "Email": email,
            "Company": company,
            "Last Activity": last_activity,
            "Page Views": page_views,
            "Sessions": sessions,
            "Purchases": purchases,
            "Plan": plan,
            "Feature Used": random.choice(features),
        })

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Name", "Email", "Company", "Last Activity",
            "Page Views", "Sessions", "Purchases", "Plan", "Feature Used"
        ])
        writer.writeheader()
        writer.writerows(users)

    print(f"✅ Generated {len(users)} CRM users → {filepath}")
    return filepath


if __name__ == "__main__":
    generate_investor_csv()
    generate_crm_dataset()
    print("\n🎉 All sample data generated successfully!")
