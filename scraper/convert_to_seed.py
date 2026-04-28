"""
Convert scraped MyScheme eligibility text into structured criteria JSON.

Parses raw eligibility text and extracts structured rules like:
  {field: "age", operator: "gte", value: "18"}

This is the "AI-assisted structuring" step from the pipeline.
"""
import json
import re
import os

INPUT = os.path.join("scraper", "output", "myscheme_full_all.json")
OUTPUT = os.path.join("app", "data", "schemes_seed.json")

STATE_CODES = {
    "Gujarat": "GJ", "Maharashtra": "MH", "Tamil Nadu": "TN", "Karnataka": "KA",
    "Kerala": "KL", "Rajasthan": "RJ", "Bihar": "BR", "Uttar Pradesh": "UP",
    "Madhya Pradesh": "MP", "Odisha": "OD", "West Bengal": "WB", "Assam": "AS",
    "Punjab": "PB", "Haryana": "HR", "Jharkhand": "JH", "Chhattisgarh": "CG",
    "Uttarakhand": "UK", "Himachal Pradesh": "HP", "Goa": "GA", "Sikkim": "SK",
    "Tripura": "TR", "Meghalaya": "ML", "Mizoram": "MZ", "Nagaland": "NL",
    "Manipur": "MN", "Arunachal Pradesh": "AR", "Delhi": "DL", "Puducherry": "PY",
    "Jammu and Kashmir": "JK", "Ladakh": "LA", "Chandigarh": "CH",
    "Andhra Pradesh": "AP", "Telangana": "TS",
    "Andaman and Nicobar Islands": "AN",
    "Dadra and Nagar Haveli and Daman and Diu": "DD",
}


def extract_criteria(text, scheme_data):
    """Parse eligibility text into structured criteria rules."""
    criteria = []
    text_lower = text.lower()

    # Age criteria
    age_patterns = [
        (r'aged?\s+(?:between\s+)?(\d+)\s*(?:years?)?\s*(?:to|and|-)\s*(\d+)', 'range'),
        (r'(?:above|over|atleast|at least|minimum)\s+(\d+)\s*(?:years?)', 'min'),
        (r'(\d+)\s*(?:years?)\s+(?:and above|or above|or more|or older)', 'min'),
        (r'(?:below|under|upto|up to|not exceeding|maximum)\s+(\d+)\s*(?:years?)', 'max'),
        (r'(\d+)\s*(?:years?)\s+(?:or below|or under|or less|or younger)', 'max'),
    ]
    for pattern, ptype in age_patterns:
        m = re.search(pattern, text_lower)
        if m:
            if ptype == 'range':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Minimum age {m.group(1)} years"})
                criteria.append({"field": "age", "operator": "lte", "value": m.group(2), "description": f"Maximum age {m.group(2)} years"})
            elif ptype == 'min':
                criteria.append({"field": "age", "operator": "gte", "value": m.group(1), "description": f"Minimum age {m.group(1)} years"})
            elif ptype == 'max':
                criteria.append({"field": "age", "operator": "lte", "value": m.group(1), "description": f"Maximum age {m.group(1)} years"})
            break

    # Income criteria
    income_patterns = [
        (r'(?:annual|yearly)\s+(?:family\s+)?income\s+(?:should\s+)?(?:not\s+)?(?:exceed|be\s+less|be\s+below|up\s*to|below)\s+(?:rs\.?\s*)?(\d[\d,]*)', 'max'),
        (r'income\s+(?:not\s+)?(?:exceeding|more\s+than|above)\s+(?:rs\.?\s*)?(\d[\d,]*)', 'max'),
        (r'(?:rs\.?\s*)?(\d[\d,]*)\s+(?:per\s+annum|annual|yearly)', 'max'),
        (r'BPL', 'bpl'),
    ]
    for pattern, ptype in income_patterns:
        m = re.search(pattern, text_lower) if ptype != 'bpl' else re.search(pattern, text)
        if m:
            if ptype == 'max':
                val = m.group(1).replace(",", "")
                criteria.append({"field": "annual_income", "operator": "lte", "value": val, "description": f"Annual income up to Rs.{val}"})
            elif ptype == 'bpl':
                criteria.append({"field": "is_bpl", "operator": "eq", "value": "true", "description": "Must be Below Poverty Line"})
            break

    # Gender
    if any(w in text_lower for w in ["women only", "female only", "girl", "women applicant", "must be a woman", "must be female"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "female", "description": "For women/girls only"})
    elif any(w in text_lower for w in ["male only", "men only", "must be male", "must be a man"]):
        criteria.append({"field": "gender", "operator": "eq", "value": "male", "description": "For men only"})

    # Caste/category
    caste_map = {
        "scheduled caste": "sc", "scheduled tribe": "st",
        "SC": "sc", "ST": "st", "OBC": "obc", "EWS": "ews",
        "general category": "general",
    }
    for keyword, val in caste_map.items():
        if keyword.lower() in text_lower or keyword in text:
            criteria.append({"field": "caste_category", "operator": "eq", "value": val, "description": f"Must belong to {keyword} category"})
            break

    # Disability
    if any(w in text_lower for w in ["disability", "disabled", "divyang", "pwbd", "differently abled"]):
        criteria.append({"field": "is_disabled", "operator": "eq", "value": "true", "description": "For persons with disabilities"})

    # Student
    if any(w in text_lower for w in ["student", "studying", "enrolled", "pursuing education", "post-matric", "scholarship"]):
        criteria.append({"field": "is_student", "operator": "eq", "value": "true", "description": "Must be a student"})

    # State from scheme data
    states = scheme_data.get("states", [])
    ministry = scheme_data.get("ministry", "")
    if not states and "Government of" in ministry:
        state_name = ministry.replace("Government of", "").strip()
        if state_name in STATE_CODES:
            criteria.append({"field": "state", "operator": "eq", "value": state_name, "description": f"Resident of {state_name}"})

    # Occupation
    if any(w in text_lower for w in ["farmer", "agricultur", "cultivat"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "farmer", "description": "Must be a farmer"})
    elif any(w in text_lower for w in ["construction worker", "building worker"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "construction_worker", "description": "Must be a construction worker"})
    elif any(w in text_lower for w in ["street vendor", "hawker"]):
        criteria.append({"field": "occupation", "operator": "eq", "value": "street_vendor", "description": "Must be a street vendor"})

    # Minority
    if any(w in text_lower for w in ["minority", "muslim", "christian", "sikh", "buddhist", "jain", "parsi"]):
        criteria.append({"field": "is_minority", "operator": "eq", "value": "true", "description": "Must belong to a minority community"})

    return criteria


def convert():
    """Convert all scraped schemes into seed format."""
    with open(INPUT, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    seed_data = []
    for s in schemes:
        name = s.get("name", "").strip()
        if not name:
            continue

        elig_text = s.get("eligibility_text", "")
        criteria = extract_criteria(elig_text, s)

        # Determine states
        states = s.get("states", [])
        state_codes = []
        ministry = s.get("ministry", "")
        if "Government of" in ministry:
            state_name = ministry.replace("Government of", "").strip()
            if state_name in STATE_CODES:
                state_codes = [STATE_CODES[state_name]]
        for st in states:
            if st in STATE_CODES and STATE_CODES[st] not in state_codes:
                state_codes.append(STATE_CODES[st])

        # Gender specific
        gender = None
        for c in criteria:
            if c["field"] == "gender":
                gender = c["value"]

        # Category from tags/category
        cat = s.get("category", "").split(",")[0].strip().lower().replace(" & ", "_").replace(" ", "_") if s.get("category") else None

        seed_data.append({
            "name": name,
            "description": s.get("description", "")[:1000] or s.get("benefits", "")[:1000],
            "ministry": ministry,
            "scheme_type": s.get("scheme_type", "central"),
            "benefit_amount": None,
            "benefit_description": s.get("benefits", "")[:500],
            "apply_link": s.get("source_url") or f"https://www.myscheme.gov.in/schemes/{s.get('slug', '')}",
            "category": cat,
            "gender_specific": gender,
            "states": state_codes,
            "criteria": criteria,
        })

    # Save
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(seed_data, f, indent=2, ensure_ascii=False)

    # Stats
    total = len(seed_data)
    with_criteria = sum(1 for s in seed_data if s["criteria"])
    total_criteria = sum(len(s["criteria"]) for s in seed_data)
    print(f"Converted {total} schemes")
    print(f"  With criteria: {with_criteria} ({with_criteria*100//total}%)")
    print(f"  Total criteria rules: {total_criteria}")
    print(f"  Saved to: {OUTPUT}")


if __name__ == "__main__":
    convert()
