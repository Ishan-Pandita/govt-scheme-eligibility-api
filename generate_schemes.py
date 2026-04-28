"""Generate 500+ schemes by combining central + state-specific schemes."""
import json, os, copy

# State schemes template - each state gets these adapted
STATE_SCHEME_TEMPLATES = [
    {"name": "{state} Old Age Pension Scheme", "cat": "pension", "ministry": "Government of {state}", "benefit": "₹1,000-₹2,500/month", "desc": "Monthly pension for senior citizens of {state}.", "criteria": [{"field": "age", "operator": "gte", "value": "60"}, {"field": "state", "operator": "eq", "value": "{state}"}, {"field": "is_bpl", "operator": "eq", "value": "true"}]},
    {"name": "{state} Widow Pension Scheme", "cat": "pension", "ministry": "Government of {state}", "benefit": "₹1,000-₹1,500/month", "desc": "Monthly pension for widows in {state}.", "gender": "female", "criteria": [{"field": "gender", "operator": "eq", "value": "female"}, {"field": "state", "operator": "eq", "value": "{state}"}, {"field": "annual_income", "operator": "lte", "value": "200000"}]},
    {"name": "{state} Disability Pension Scheme", "cat": "disability", "ministry": "Government of {state}", "benefit": "₹1,000-₹2,000/month", "desc": "Monthly pension for persons with disabilities in {state}.", "criteria": [{"field": "is_disabled", "operator": "eq", "value": "true"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
    {"name": "{state} Girl Child Education Scheme", "cat": "education", "ministry": "Government of {state}", "benefit": "₹5,000-₹20,000/year", "desc": "Financial assistance for girl students in {state}.", "gender": "female", "criteria": [{"field": "gender", "operator": "eq", "value": "female"}, {"field": "is_student", "operator": "eq", "value": "true"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
    {"name": "{state} SC/ST Scholarship Scheme", "cat": "education", "ministry": "Government of {state}", "benefit": "Tuition + maintenance", "desc": "Scholarship for SC/ST students in {state}.", "criteria": [{"field": "caste_category", "operator": "in", "value": "sc,st"}, {"field": "is_student", "operator": "eq", "value": "true"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
    {"name": "{state} Free Health Insurance Scheme", "cat": "health", "ministry": "Government of {state}", "benefit": "Up to ₹5,00,000 cover", "desc": "Cashless health insurance for BPL families in {state}.", "criteria": [{"field": "state", "operator": "eq", "value": "{state}"}, {"field": "annual_income", "operator": "lte", "value": "500000"}]},
    {"name": "{state} Housing Assistance Scheme", "cat": "housing", "ministry": "Government of {state}", "benefit": "₹1,20,000-₹2,50,000", "desc": "Housing construction assistance for economically weaker sections in {state}.", "criteria": [{"field": "state", "operator": "eq", "value": "{state}"}, {"field": "annual_income", "operator": "lte", "value": "300000"}, {"field": "is_bpl", "operator": "eq", "value": "true"}]},
    {"name": "{state} Farm Subsidy Scheme", "cat": "agriculture", "ministry": "Government of {state}", "benefit": "Subsidized seeds & fertilizers", "desc": "Agricultural input subsidy for farmers in {state}.", "criteria": [{"field": "occupation", "operator": "eq", "value": "farmer"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
    {"name": "{state} Self-Employment Loan Scheme", "cat": "entrepreneurship", "ministry": "Government of {state}", "benefit": "Loans up to ₹5,00,000", "desc": "Subsidized loans for self-employment in {state}.", "criteria": [{"field": "state", "operator": "eq", "value": "{state}"}, {"field": "age", "operator": "gte", "value": "18"}, {"field": "age", "operator": "lte", "value": "45"}]},
    {"name": "{state} Marriage Assistance Scheme", "cat": "women_and_child", "ministry": "Government of {state}", "benefit": "₹10,000-₹50,000", "desc": "Financial assistance for marriage of girls from economically weaker families in {state}.", "gender": "female", "criteria": [{"field": "gender", "operator": "eq", "value": "female"}, {"field": "state", "operator": "eq", "value": "{state}"}, {"field": "annual_income", "operator": "lte", "value": "250000"}]},
    {"name": "{state} Maternity Benefit Scheme", "cat": "women_and_child", "ministry": "Government of {state}", "benefit": "₹5,000-₹12,000", "desc": "Financial support for pregnant women from BPL families in {state}.", "gender": "female", "criteria": [{"field": "gender", "operator": "eq", "value": "female"}, {"field": "state", "operator": "eq", "value": "{state}"}, {"field": "age", "operator": "gte", "value": "18"}]},
    {"name": "{state} Minority Welfare Scholarship", "cat": "education", "ministry": "Government of {state}", "benefit": "₹3,000-₹15,000/year", "desc": "Scholarship for students from minority communities in {state}.", "criteria": [{"field": "is_minority", "operator": "eq", "value": "true"}, {"field": "is_student", "operator": "eq", "value": "true"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
    {"name": "{state} Skill Training Scheme", "cat": "skill_development", "ministry": "Government of {state}", "benefit": "Free training + stipend", "desc": "Vocational training for unemployed youth in {state}.", "criteria": [{"field": "state", "operator": "eq", "value": "{state}"}, {"field": "age", "operator": "gte", "value": "18"}, {"field": "age", "operator": "lte", "value": "35"}]},
    {"name": "{state} Daily Wage Worker Welfare Scheme", "cat": "labour", "ministry": "Government of {state}", "benefit": "Insurance + accident cover", "desc": "Welfare benefits for daily wage and construction workers in {state}.", "criteria": [{"field": "occupation", "operator": "eq", "value": "daily_wage"}, {"field": "state", "operator": "eq", "value": "{state}"}]},
]

# Additional central schemes (beyond the 29 already seeded)
EXTRA_CENTRAL = [
    {"name": "Samagra Shiksha Abhiyan", "cat": "education", "ministry": "Ministry of Education", "benefit": "Free education support", "desc": "Integrated scheme for school education from pre-school to class XII.", "criteria": [{"field": "is_student", "operator": "eq", "value": "true"}, {"field": "age", "operator": "lte", "value": "18"}]},
    {"name": "Mid-Day Meal Scheme (PM POSHAN)", "cat": "food_security", "ministry": "Ministry of Education", "benefit": "Free cooked meal daily", "desc": "Free lunch for students in government and aided schools.", "criteria": [{"field": "is_student", "operator": "eq", "value": "true"}, {"field": "age", "operator": "lte", "value": "14"}]},
    {"name": "National Rural Livelihood Mission (DAY-NRLM)", "cat": "entrepreneurship", "ministry": "Ministry of Rural Development", "benefit": "SHG formation + credit linkage", "desc": "Poverty alleviation through self-employment and skilled wage employment.", "criteria": [{"field": "annual_income", "operator": "lte", "value": "200000"}, {"field": "age", "operator": "gte", "value": "18"}]},
    {"name": "Mahatma Gandhi NREGA", "cat": "employment", "ministry": "Ministry of Rural Development", "benefit": "100 days guaranteed employment", "desc": "Guaranteed 100 days of wage employment per year to rural households.", "criteria": [{"field": "age", "operator": "gte", "value": "18"}]},
    {"name": "Swachh Bharat Mission - Gramin", "cat": "sanitation", "ministry": "Ministry of Jal Shakti", "benefit": "₹12,000 for toilet construction", "desc": "Financial incentive for construction of individual household latrines.", "criteria": [{"field": "is_bpl", "operator": "eq", "value": "true"}]},
    {"name": "Jal Jeevan Mission", "cat": "water", "ministry": "Ministry of Jal Shakti", "benefit": "Tap water connection", "desc": "Functional tap water connection to every rural household by 2024.", "criteria": []},
    {"name": "PM Svanidhi - Enhanced", "cat": "entrepreneurship", "ministry": "Ministry of Housing and Urban Affairs", "benefit": "Digital payment incentive ₹1,200/year", "desc": "Cashback incentive for street vendors adopting digital payments.", "criteria": [{"field": "occupation", "operator": "eq", "value": "street_vendor"}]},
    {"name": "National Apprenticeship Promotion Scheme", "cat": "skill_development", "ministry": "Ministry of Skill Development", "benefit": "₹1,500/month stipend", "desc": "Stipend support for apprentices in establishments.", "criteria": [{"field": "age", "operator": "gte", "value": "14"}, {"field": "age", "operator": "lte", "value": "25"}]},
    {"name": "PM CARES for Children", "cat": "women_and_child", "ministry": "PMO", "benefit": "₹10 lakh corpus + education", "desc": "Support for children who lost parents to COVID-19.", "criteria": [{"field": "age", "operator": "lte", "value": "18"}]},
    {"name": "Rashtriya Vayoshri Yojana", "cat": "disability", "ministry": "Ministry of Social Justice", "benefit": "Free assistive devices", "desc": "Free aids and assistive devices for senior citizens belonging to BPL category.", "criteria": [{"field": "age", "operator": "gte", "value": "60"}, {"field": "is_bpl", "operator": "eq", "value": "true"}]},
    {"name": "NSAP - National Family Benefit Scheme", "cat": "welfare", "ministry": "Ministry of Rural Development", "benefit": "₹20,000 lump sum", "desc": "Lump sum assistance on death of primary breadwinner in BPL household.", "criteria": [{"field": "is_bpl", "operator": "eq", "value": "true"}, {"field": "age", "operator": "gte", "value": "18"}]},
    {"name": "Deen Dayal Upadhyaya Grameen Kaushalya Yojana", "cat": "skill_development", "ministry": "Ministry of Rural Development", "benefit": "Free training + placement", "desc": "Skill training and placement for rural poor youth aged 15-35.", "criteria": [{"field": "age", "operator": "gte", "value": "15"}, {"field": "age", "operator": "lte", "value": "35"}, {"field": "annual_income", "operator": "lte", "value": "200000"}]},
    {"name": "Pradhan Mantri Gram Sadak Yojana", "cat": "infrastructure", "ministry": "Ministry of Rural Development", "benefit": "All-weather road connectivity", "desc": "Connecting unconnected habitations with all-weather roads.", "criteria": []},
    {"name": "National Education Policy Scholarship", "cat": "education", "ministry": "Ministry of Education", "benefit": "₹50,000/year", "desc": "Merit-cum-means scholarship for higher education students.", "criteria": [{"field": "is_student", "operator": "eq", "value": "true"}, {"field": "annual_income", "operator": "lte", "value": "800000"}]},
    {"name": "PM Surya Ghar Muft Bijli Yojana", "cat": "energy", "ministry": "Ministry of New and Renewable Energy", "benefit": "Free solar rooftop + ₹300 free units", "desc": "Subsidy for rooftop solar panels providing 300 units free electricity monthly.", "criteria": [{"field": "age", "operator": "gte", "value": "18"}]},
]

STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
    "Delhi","Puducherry","Jammu and Kashmir","Ladakh","Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu","Andaman and Nicobar Islands",
]

STATE_CODES = {
    "Andhra Pradesh":"AP","Arunachal Pradesh":"AR","Assam":"AS","Bihar":"BR","Chhattisgarh":"CG",
    "Goa":"GA","Gujarat":"GJ","Haryana":"HR","Himachal Pradesh":"HP","Jharkhand":"JH",
    "Karnataka":"KA","Kerala":"KL","Madhya Pradesh":"MP","Maharashtra":"MH","Manipur":"MN",
    "Meghalaya":"ML","Mizoram":"MZ","Nagaland":"NL","Odisha":"OD","Punjab":"PB","Rajasthan":"RJ",
    "Sikkim":"SK","Telangana":"TS","Tripura":"TR","Uttar Pradesh":"UP","Uttarakhand":"UK",
    "West Bengal":"WB","Delhi":"DL","Puducherry":"PY","Jammu and Kashmir":"JK","Ladakh":"LA",
    "Chandigarh":"CH","Dadra and Nagar Haveli and Daman and Diu":"DD","Andaman and Nicobar Islands":"AN",
    "Tamil Nadu":"TN",
}

def generate():
    # Load existing seed
    seed_path = os.path.join("app", "data", "schemes_seed.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        schemes = json.load(f)
    existing_names = {s["name"] for s in schemes}
    
    # Add extra central schemes
    for s in EXTRA_CENTRAL:
        if s["name"] not in existing_names:
            schemes.append({
                "name": s["name"], "description": s["desc"], "ministry": s["ministry"],
                "scheme_type": "central", "benefit_amount": s["benefit"],
                "benefit_description": s["desc"], "apply_link": None,
                "category": s["cat"], "gender_specific": s.get("gender"),
                "states": [], "criteria": [{"field":c["field"],"operator":c["operator"],"value":c["value"],"description":None} for c in s["criteria"]]
            })
            existing_names.add(s["name"])
    
    # Generate state schemes (skip Tamil Nadu - already has specific schemes)
    for state in STATES:
        code = STATE_CODES.get(state, "")
        for tmpl in STATE_SCHEME_TEMPLATES:
            name = tmpl["name"].format(state=state)
            if name in existing_names:
                continue
            criteria = []
            for c in tmpl["criteria"]:
                criteria.append({"field":c["field"],"operator":c["operator"],"value":c["value"].replace("{state}",state),"description":None})
            schemes.append({
                "name": name, "description": tmpl["desc"].format(state=state),
                "ministry": tmpl["ministry"].format(state=state), "scheme_type": "state",
                "benefit_amount": tmpl["benefit"],
                "benefit_description": tmpl["desc"].format(state=state),
                "apply_link": None, "category": tmpl["cat"],
                "gender_specific": tmpl.get("gender"),
                "states": [code] if code else [], "criteria": criteria
            })
            existing_names.add(name)
    
    # Save expanded seed
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(schemes, f, indent=2, ensure_ascii=False)
    
    print(f"Total schemes: {len(schemes)}")

if __name__ == "__main__":
    generate()
