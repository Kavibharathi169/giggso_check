import requests
import json

url = "http://localhost:8000/api/v1/checklist"
payload = {
    "query": "governance compliance requirements",
    "top_k": 10
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)

print("Status code:", response.status_code)
print("Response:")
print(response.json())

# Write response to file for guaranteed visibility
with open("checklist_api_response.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=2)
