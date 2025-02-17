import requests
import json

url = "http://localhost:11434/api/chat"
payload = {
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Name three AGI focused companies."}]
}
response = requests.post(url, json=payload)
# data = response.json()
# print(json.dumps(data, indent=2))
outs = []
for line in response.text.splitlines():
    d = json.loads(line)
    content = d['message']['content']
    outs.append(content)

print("".join(outs))