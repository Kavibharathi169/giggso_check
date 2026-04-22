import requests

payload = {
    'query': 'Extract all compliance policies, requirements, and checklist items. Strictly format as JSON.',
    'domain': 'all',
    'user_id': 'test'
}
res = requests.post('http://127.0.0.1:8000/api/chat', json=payload)
data = res.json()
print("Raw Data type:", type(data.get('raw_data')))
print("Raw Data length:", len(data.get('raw_data')) if isinstance(data.get('raw_data'), list) else data.get('raw_data'))
