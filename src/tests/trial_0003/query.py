import requests
import json
import os


def query_llm(prompt, conversation_history=None, model="deepseek-r1:70b"):
    """
    Query the deepseek-r1:70b model through Ollama with additional debugging.
    Combines the system prompt, conversation history, and user prompt into one string.
    """
    if conversation_history is None:
        conversation_history = []
    # Build conversation including the system prompt
    # messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # messages = [{"role": "system", "content": "bioinformatics researcher."}]
    # messages.append({"role": "user", "content": prompt})
    messages = [{"role": "coding-assistant", "content": prompt + '\n\nhistory: \n' + str(conversation_history)}]
    # messages.extend(conversation_history)

    
    # Combine messages into one prompt string.
    prompt_string = ""
    for message in messages:
        prompt_string += f"{message['role']}: {message['content']}\n\n"
    
    # Define the Ollama API endpoint and payload.
    if 'endpoint' in os.environ.keys():
        endpoint = os.environ['endpoint']
    else:
        endpoint = "http://localhost:11434/api/chat"  # Adjust as needed.
    # payload = {
    #     "model": "llama3.2",
    #     "messages": [{"role": "user", "content": "Name three AGI focused companies."}]
    # }
    print(prompt_string)
    payload = {
        # "model": "llama3.3:70b-instruct-q2_K",
        "model": model,
        # "messages": [{"role": "bioinformatics researcher", "content": prompt_string}],
        "messages": [{"role": "user", "content": prompt_string}],
        "max_tokens": 2500,   # Consider increasing if output is too short.
        "temperature": 0.7,
        "stream": True
    }
    
    # Debug: log payload information.
    print("DEBUG: Sending payload to Ollama:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(endpoint, json=payload, stream=True)
        # response.raise_for_status()
    except Exception as e:
        print("DEBUG: Error during request:", e)
        return ""
    
    # Debug: log raw response text.
    # simple_prompt = "user: Hello, please say something."
    # print(query_llm(simple_prompt))
    # print("DEBUG: Raw response from Ollama:")
    # print(response.text)
    
    try:
        outs = []
        # for line in response.text.splitlines():
        #     d = json.loads(line)
        #     content = d['message']['content']
        #     outs.append(content)
        #     # print(content)
        #     # print('----------------------------------------------')
        for line in response.iter_lines():
            if line:
                try:
                    d = json.loads(line.decode("utf-8"))
                    print(d.get("message", {}).get("content", ""), end="", flush=True)
                    outs.append(d.get("message", {}).get("content", ""))
                except json.JSONDecodeError:
                    continue  # Skip bad lines

        print('returning outs')
        outs = "".join(outs)
        # print(outs)
        return outs
    except Exception as e:
        print("DEBUG: Failed to decode JSON from response:", e)
        return ""
