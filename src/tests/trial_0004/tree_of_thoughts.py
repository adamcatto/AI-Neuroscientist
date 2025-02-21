import os
import requests
from typing import List



class ProgramTreeOfThoughts:
    def __init__(self, model: str, task_prompt: str):
        self.task_prompt = task_prompt
        self.children = []

    def generate_branches_string(self, prompt_string: str):
        """
        Given a task node represented by `prompt_string`, 
        generate a list of subtasks that can be used to solve the task.
        """
        prompt = f"""
        Given the task: "{prompt_string}", break down the task into a sequence of subtasks to approach solving it. 
        Each response should be a structured thought process leading toward a solution.
        Each of the tasks should be enumerated like '\item[1][task-description]' ... '\item[N][task-description]'.
        """
        payload = {
            "model": "deepseek-r1:70b",
            "messages": [{"role": "user", "content": prompt_string}],
            "max_tokens": 2500,   # Consider increasing if output is too short.
            "temperature": 0.7,
            "stream": True
        }
        try:
            response = requests.post(os.environ["endpoint"], json=payload, stream=True)
            # response.raise_for_status()
        except Exception as e:
            print("DEBUG: Error during request:", e)
            return ""
        return response["message"]["content"].split("\n\n")  # Split into separate thoughts

    def parse_branches_string_to_nodes(self, branches: List[str]):
        for branch in branches:
            self.children.append(ProgramTreeOfThoughts(model=self.model, task_prompt=branch))