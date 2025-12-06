import json

with open('data/damages_with_embeddings.json') as f:
    cases = json.load(f)

print(f'Total cases in damages_with_embeddings.json: {len(cases)}')
print()

# Check FLA relationships
fla_count = 0
fla_relationships = []
for c in cases:
    ext = c.get('extended_data', {})
    if ext.get('family_law_act_claims'):
        fla_count += 1
        for claim in ext.get('family_law_act_claims', []):
            fla_relationships.append(claim.get('relationship'))

print(f'Cases with FLA claims: {fla_count}')
print(f'Total FLA relationships: {len(fla_relationships)}')
print()

# Find MacMillan
macmillan_cases = []
for c in cases:
    if c.get('case_name') and 'MacMillan' in c.get('case_name', '') and 'Moreau' in c.get('case_name', ''):
        macmillan_cases.append(c)

print(f'Found {len(macmillan_cases)} MacMillan cases')
for c in macmillan_cases:
    print(f'\nCase: {c.get("case_name")}')
    print(f'Year: {c.get("year")}')
    print(f'Region: {c.get("region")}')
    print(f'Damages: {c.get("damages")}')
    print(f'Non-pecuniary: {c.get("non_pecuniary_damages")}')
    print(f'Comments: {c.get("comments", "")[:200]}')
    print(f'Summary: {c.get("summary_text", "")[:200]}')
    print(f'Extended data:')
    ext = c.get('extended_data', {})
    print(f'  Injuries: {ext.get("injuries", [])}')
    print(f'  FLA claims: {len(ext.get("family_law_act_claims", []))}')
    if ext.get('family_law_act_claims'):
        for fla in ext.get('family_law_act_claims', [])[:2]:
            print(f'    - {fla.get("relationship")}: ${fla.get("amount", 0):,.0f}')
    print(f'  Plaintiff ID: {ext.get("plaintiff_id")}')
    print(f'  Num plaintiffs: {ext.get("num_plaintiffs")}')

# Check for cases with diffuse axonal injury
print('\n\n=== Checking for diffuse axonal injury ===')
dai_cases = []
for c in cases:
    ext = c.get('extended_data', {})
    injuries = ext.get('injuries', [])
    injuries_str = ' '.join(injuries).lower()
    if 'diffuse' in injuries_str or 'axonal' in injuries_str:
        dai_cases.append(c)

print(f'Found {len(dai_cases)} cases with diffuse/axonal in injuries')
for c in dai_cases[:3]:
    ext = c.get('extended_data', {})
    print(f'  - {c.get("case_name")}: {ext.get("injuries", [])}')
