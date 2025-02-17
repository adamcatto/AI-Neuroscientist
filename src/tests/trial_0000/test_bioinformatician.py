import os
import json
import time
import requests
import re
import base64
from io import StringIO, BytesIO
import sys
import threading

from IPython import get_ipython
from IPython.display import display, Javascript
import ipywidgets as widgets
import matplotlib.pyplot as plt
import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell, new_output
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# SYSTEM PROMPT
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = """
you are an autonomous bioinformatician. you have a collection of spatial transcriptomics datasets stored in ../../read_only_sandbox/raw_data . Your task is to (1) set up a jupyter notebook environment to house your analysis with scanpy, (2) determine what kind of data you are working with and summarize it in a markdown cell, using any python code necessary to complete this portion of the task, (3) set up a jupyter notebook-based pipeline to explore and preprocess the data, (4) in the same notebook, set up a post-preprocessing pipeline to process the data, making useful visualizations and carefully choosing parameters, (5) in the same notebook, set up a pipeline to make novel discoveries about the dataset; these can be related to novel subpopulation discovery, spatial relationships between cell types, pseudotime analysis, DEGs, etc, think outside the box and make the discoveries really novel, designing your own algorithms whenever necessary. at each step, break down the subtasks to whatever degree necessary and generate sequences of jupyter notebook cells (code and markdown) to complete your tasks. before creating and running the code cell, describe your thought process at the current stage in a markdown cell. use the outputs of the previous cells to update your plan after each cell has run.
"""

# ----------------------------------------------------------------------------
# QUERY FUNCTION USING OLLAMA
# ----------------------------------------------------------------------------

def query_llm(prompt, conversation_history=None):
    """
    Query the Llama3.2-70B model through Ollama with additional debugging.
    Combines the system prompt, conversation history, and user prompt into one string.
    """
    if conversation_history is None:
        conversation_history = []
    # Build conversation including the system prompt
    # messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # messages = [{"role": "system", "content": "bioinformatics researcher."}]
    # messages.append({"role": "user", "content": prompt})
    messages = [{"role": "user", "content": prompt}]
    messages.extend(conversation_history)
    
    # Combine messages into one prompt string.
    prompt_string = ""
    for message in messages:
        prompt_string += f"{message['role']}: {message['content']}\n\n"
    
    # Define the Ollama API endpoint and payload.
    endpoint = "http://localhost:11434/api/chat"  # Adjust as needed.
    # payload = {
    #     "model": "llama3.2",
    #     "messages": [{"role": "user", "content": "Name three AGI focused companies."}]
    # }
    print(prompt_string)
    payload = {
        # "model": "llama3.3:70b-instruct-q2_K",
        "model": "deepseek-r1:70b",
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
    


import json
import re

import json
import re

def extract_json(text):
    """
    Extracts valid JSON notebook cells and captures any non-JSON text separately.
    - Identifies the JSON structure (`[...]`) in the response.
    - Extracts any extra text before or after the JSON as a separate markdown cell.
    """
    # Remove Markdown-style code blocks if present
    text = re.sub(r"```(?:json)?(.*?)```", r"\1", text, flags=re.DOTALL).strip()

    # Extract the first JSON array
    json_regex = r'\[\s*\{.*?\}\s*\]'  # Matches a JSON list containing at least one object
    match = re.search(json_regex, text, re.DOTALL)

    json_cells = []
    markdown_text = ""

    if match:
        json_str = match.group(0)  # Extract only the JSON part
        try:
            json_cells = json.loads(json_str)  # Attempt to parse JSON
        except json.JSONDecodeError as e:
            print("Extraction found text but could not parse JSON:", e)
            print("Problematic JSON:", json_str)
            json_cells = []

        # Extract non-JSON text before and after the JSON block
        markdown_text = text.replace(json_str, "").strip()

    else:
        # If no JSON is found, treat everything as a markdown cell
        markdown_text = text.strip()

    # If there's non-JSON text, return it as a markdown cell
    if markdown_text:
        json_cells.insert(0, {"cell_type": "markdown", "content": markdown_text})

    return json_cells if json_cells else [{'cell_type': 'markdown', 'content': f'DEBUG: {text}'}]


def generate_cell_content(task, conversation_history):
    """
    For a given task, ask the LLM to generate a JSON-formatted list of
    notebook cells. Each cell is expected to be a JSON object with:
      - "cell_type": "markdown" or "code"
      - "content": the actual cell text.
    """
    prompt = (
        f"Task: {task}\n"
        "Please generate a JSON-formatted list of Jupyter notebook cells to complete this task. "
        "Each cell should be an object with keys 'cell_type' (either 'markdown' or 'code') and "
        "'content' (the cell content). Do not include any additional text, only output valid JSON that starts with '[' and ends with ']'."
        "Make sure that the keys of the JSON objects are exactly 'cell_type' and 'content'."
    )
    # print(prompt)
    
    llm_response = query_llm(prompt, conversation_history)
    # print("\n-----------------\n-----------------\nresponse: \n-------------------\n", llm_response)
    # return llm_response
    # print('response: ', llm_response)
    try:
        cell_list = extract_json(llm_response)
        print('cell_list:', cell_list, type(cell_list))
        # return [{
        #     "cell_type": "code",
        #     "content": llm_response
        # }], llm_response
        return cell_list, "".join(llm_response)
    except Exception as e:
        # Try to extract valid JSON from the response
        cell_list = extract_json(llm_response)
        if cell_list is not None:
            return cell_list, llm_response
        else:
            # Fallback cell if JSON extraction fails
            fallback = [{
                "cell_type": "markdown",
                "content": f"LLM response could not be parsed as JSON. Raw response:\n{llm_response}"
            }]
            return fallback, llm_response

# ----------------------------------------------------------------------------
# NOTEBOOK AUTOMATION CODE
# ----------------------------------------------------------------------------

def checks_out(x):
    if isinstance(x, pd.DataFrame):
        return True
    elif isinstance(x, np.ndarray):
        return True
    elif x is None:
        return False
    elif not x:
        return False
    else:
        return True

# ----------------------------------------------------------------------------
# UTILITIES FOR LIVE NOTEBOOK UI REFRESH
# ----------------------------------------------------------------------------
def refresh_notebook_ui():
    try:
        display(Javascript("Jupyter.notebook.kernel.execute('pass')"))
    except Exception as e:
        print("Could not trigger refresh via JavaScript:", e)

# ----------------------------------------------------------------------------
# CREATE A NEW EMPTY NOTEBOOK
# ----------------------------------------------------------------------------
def create_notebook(notebook_path: str):
    nb = new_notebook(cells=[])
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Created notebook: {notebook_path}")

# ----------------------------------------------------------------------------
# APPEND A CELL TO THE NOTEBOOK FILE
# ----------------------------------------------------------------------------
def add_cell_to_notebook(notebook_path: str, cell_content: str, cell_type: str = 'code', output=None):
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    
    if cell_type == 'markdown':
        new_cell = new_markdown_cell(cell_content)
    elif cell_type == 'code':
        new_cell = new_code_cell(cell_content)
        if output:
            new_cell["outputs"] = [output]  # Attach output to the cell
    else:
        raise ValueError("Unsupported cell type. Use 'markdown' or 'code'.")

    nb.cells.append(new_cell)

    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    
    print(f"Added a new {cell_type} cell to {notebook_path}")
    refresh_notebook_ui()

# ----------------------------------------------------------------------------
# EXECUTE CODE IN THE CURRENT IPYTHON SESSION
# ----------------------------------------------------------------------------
def execute_cell(cell_code: str):
    ipython = get_ipython()
    if ipython is None:
        from IPython.core.interactiveshell import InteractiveShell
        ipython = InteractiveShell.instance()
    
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer
    
    try:
        result = ipython.run_cell(cell_code)
        execution_output = stdout_buffer.getvalue().strip()
        final_output = result.result if result.result is not None else execution_output
    finally:
        sys.stdout = sys.__stdout__
    return str(final_output)

def execute_cell_universal(cell_code: str):
    ipython = get_ipython()
    if ipython is None:
        from IPython.core.interactiveshell import InteractiveShell
        ipython = InteractiveShell.instance()
    
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer
    plt.close("all")
    
    try:
        result = ipython.run_cell(cell_code)
        execution_output = stdout_buffer.getvalue().strip()
        return_value = result.result if result.result is not None else ""
        fig = plt.gcf()
        if fig and fig.get_axes():
            buf = BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            encoded_img = base64.b64encode(buf.read()).decode("utf-8")
            final_output = {"image/png": encoded_img}
        else:
            final_output = str(return_value) if checks_out(return_value) else execution_output
            final_output = {"text/plain": final_output}
    finally:
        sys.stdout = sys.__stdout__
    
    return final_output

# ----------------------------------------------------------------------------
# EDIT A CELL IN THE NOTEBOOK FILE
# ----------------------------------------------------------------------------
def edit_cell_in_notebook(notebook_path: str, cell_index: int, new_content: str) -> None:
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    
    if cell_index < 0 or cell_index >= len(nb.cells):
        raise IndexError("Cell index out of range.")
    
    nb.cells[cell_index]['source'] = new_content
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    
    print(f"Cell {cell_index} updated in {notebook_path}")
    refresh_notebook_ui()

# ----------------------------------------------------------------------------
# STREAM THE NOTEBOOK FILE IN REAL TIME VIA A WIDGET
# ----------------------------------------------------------------------------
def monitor_file(file_path: str, text_widget: widgets.Textarea, sleep_time: float = 0.5):
    last_mtime = None
    while True:
        try:
            mtime = os.path.getmtime(file_path)
        except FileNotFoundError:
            mtime = None
        
        if mtime != last_mtime:
            last_mtime = mtime
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                text_widget.value = content
            except Exception as e:
                text_widget.value = f"Error reading file: {e}"
        time.sleep(sleep_time)

def start_streaming(file_path: str) -> widgets.Textarea:
    text_area = widgets.Textarea(
        value='',
        placeholder='Streaming file content...',
        description='Tail:',
        layout=widgets.Layout(width='100%', height='300px')
    )
    display(text_area)
    thread = threading.Thread(target=monitor_file, args=(file_path, text_area), daemon=True)
    thread.start()
    return text_area

# ----------------------------------------------------------------------------
# MAIN FUNCTION USING THE LLM VIA OLLAMA
# ----------------------------------------------------------------------------
def main_llm():
    # Define the notebook path and create an empty notebook.
    notebook_path = './llm_generated_notebook.ipynb'
    create_notebook(notebook_path)
    
    # Start streaming the notebook content in a widget.
    stream_widget = start_streaming(notebook_path)
    print("Running in a live notebook session using the current kernel.")

    cell_content = "import matplotlib\nmatplotlib.use('Agg')\nprint('Imports successful.')"
        
    cell_output = execute_cell_universal(cell_content)
    output_type = "display_data" if "image/png" in cell_output else "execute_result"

    
    output = new_output(
        output_type=output_type, 
        data=cell_output
    )
    
    add_cell_to_notebook(
        notebook_path, 
        cell_content, 
        cell_type='code',
        output=output)
    
    
    # Define the list of high-level tasks for the notebook.
    tasks = [
        # "Set up a Jupyter notebook environment to house your analysis. Create an initial markdown cell explaining your plan and the approach you will take. Then create a code cell with the necessary imports and environment setup.",
        # "Determine what kind of spatial transcriptomics data you are working with. Create a markdown cell summarizing the approach/data, and a code cell that loads and inspects the data stored in the folder ../../read_only_sandbox/raw_data/.",
        "you are an autonomous bioinformatician. you have a collection of spatial transcriptomics datasets stored in ../../read_only_sandbox/raw_data . write me a chunk of code in a jupyter notebook cell that will figure out what kind of data you are working with, by listing the files and reading them in, using python's nbformat api. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell. you can use glob to get all files.",
        "Set up a pipeline in the notebook to explore and preprocess the data. Include steps such as quality control, normalization, and initial visualization. Provide your thought process in a markdown cell, followed by the code. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell.  you can use glob to get all files if you need to.",
        "Set up a post-preprocessing pipeline to further process the data. This should include more detailed visualizations and parameter tuning. Provide your reasoning in a markdown cell and the corresponding code in another cell. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell.",
        "Develop a pipeline to make novel discoveries about the dataset. This may include discovering novel subpopulations, analyzing spatial relationships between cell types, performing pseudotime analysis, or identifying DEGs. Explain your approach in a markdown cell, and then provide the code. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell."
    ]
    
    conversation_history = []
    # Process each high-level task one at a time.
    for task in tasks:
        # print(task)
        cell_list, llm_raw_response = generate_cell_content(task, conversation_history)
        print('cell_list:', cell_list)
        
        # For each cell returned by the LLM, add it to the notebook.
        for cell in cell_list:
            print('cell:', cell)
            # cell = json.loads(cell)
            cell_type = cell.get("cell_type", "code")
            content = cell.get("content", "")
            # print('--------------------------------')
            # print(cell_type, content)
            # print('--------------------------------')
            # add_cell_to_notebook(notebook_path, content, cell_type=cell_type)
            
            # For code cells, execute them immediately and attach the output.
            if cell_type == "code":
                cell_output = execute_cell_universal(content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    notebook_path,
                    content,
                    cell_type='code',
                    output=new_output(output_type=output_type, data=cell_output)
                )
            elif cell_type == "markdown":
                cell_output = execute_cell_universal(content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    notebook_path,
                    content,
                    cell_type='markdown',
                    output=new_output(output_type=output_type, data=cell_output)
                )
        # Append the raw LLM response to the conversation history for context.
        # conversation_history.append({"role": "assistant", "content": llm_raw_response})
        time.sleep(1)  # Optional delay between tasks
    
    print("Notebook generation complete!")

# Run the fully automated pipeline using Llama3.2-70B with Ollama.
main_llm()