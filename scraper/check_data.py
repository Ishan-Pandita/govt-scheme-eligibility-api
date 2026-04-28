import json

data = json.load(open("scraper/output/myscheme_full.json", "r", encoding="utf-8"))
print(f"Total schemes: {len(data)}")

# Count by type
central = sum(1 for s in data if s.get("scheme_type") == "central")
state = sum(1 for s in data if s.get("scheme_type") == "state")
print(f"Central: {central}, State: {state}")

# Count with eligibility text
has_elig = sum(1 for s in data if s.get("eligibility_text", "").strip())
has_benefits = sum(1 for s in data if s.get("benefits", "").strip())
has_desc = sum(1 for s in data if s.get("description", "").strip())
print(f"With eligibility text: {has_elig}")
print(f"With benefits: {has_benefits}")
print(f"With description: {has_desc}")

# Show 5 sample schemes
print("\n--- Sample Schemes ---")
for s in data[:5]:
    print(f"\nName: {s['name']}")
    print(f"Ministry: {s['ministry']}")
    print(f"Type: {s['scheme_type']}")
    elig = s.get("eligibility_text", "")[:200]
    print(f"Eligibility: {elig}...")
