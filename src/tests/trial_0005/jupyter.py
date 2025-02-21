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

from parsing import extract_json
from query import query_llm



def generate_cell_content(task, conversation_history, task_history=""):
    """
    For a given task, ask the LLM to generate a JSON-formatted list of
    notebook cells. Each cell is expected to be a JSON object with:
      - "cell_type": "markdown" or "code"
      - "content": the actual cell text.
    """
    prompt = (
        f"Task: {task}\n"
        "Please generate a JSON-formatted list of Jupyter notebook cells to complete this task."
        "You should return exactly two cells: "
        "(1) a markdown cell describing your plan of attack based on the task, history, and previous cell output, and "
        "(2) the code to run in the notebook to accomplish the task or subtask."
        # "Please generate a JSON-formatted list of Jupyter notebook cells to complete this task. "
        "Each cell should be an object with keys 'cell_type' (either 'markdown' or 'code') and "
        "'content' (the cell content). Do not include any additional text, only output valid JSON that starts with '[' and ends with ']'."
        "Make sure that the keys of the JSON objects are exactly 'cell_type' and 'content'."
        f"Here is the previous task outputs: {task_history}\n"
    )
    # print(prompt)
    
    llm_response = query_llm(prompt, conversation_history)
    # print("\n-----------------\n-----------------\nresponse: \n-------------------\n", llm_response)
    # return llm_response
    # print('response: ', llm_response)
    try:
        cell_list = extract_json(llm_response)
        # print('cell_list:', cell_list, type(cell_list))
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
    
    # print(f"Added a new {cell_type} cell to {notebook_path}")
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

import sys
import base64
import traceback
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
from IPython.core.interactiveshell import InteractiveShell

def execute_cell_universal(cell_code: str):
    """
    Executes a given code cell in the IPython environment and captures:
    - Execution output (stdout)
    - Error messages (stderr or exceptions)
    - Image output (if a figure is generated)
    """
    print('running')
    ipython = get_ipython()
    print('running more...')
    
    if ipython is None:
        ipython = InteractiveShell.instance()
    
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()

    sys.stdout = stdout_buffer  # Capture standard output
    sys.stderr = stderr_buffer  # Capture error messages
    plt.close("all")

    error_occurred = False
    final_output = {}

    try:
        result = ipython.run_cell(cell_code)

        # Capture standard output
        execution_output = stdout_buffer.getvalue().strip()
        error_output = stderr_buffer.getvalue().strip()

        # Explicitly check `error_before_exec`
        # if result.error_before_exec is not None:
        #     error_occurred = True
        #     final_output = {"text/plain": f"Syntax Error: {error_output}"}
        #     print("Detected error_before_exec:", result.error_before_exec)

        # Check if the result itself is an exception
        if isinstance(result.result, BaseException):
            error_occurred = True
            error_message = traceback.format_exception_only(type(result.result), result.result)
            final_output = {"text/plain": "Runtime Error:\n" + "".join(error_message)}

        # Capture errors from `stderr`
        elif error_output:
            error_occurred = True
            final_output = {"text/plain": "Captured Error:\n" + error_output}

        # Capture plots if available
        elif plt.get_fignums():
            buf = BytesIO()
            plt.gcf().savefig(buf, format="png")
            buf.seek(0)
            encoded_img = base64.b64encode(buf.read()).decode("utf-8")
            final_output = {"image/png": encoded_img}

        # Handle normal execution output
        else:
            final_output = {"text/plain": execution_output or str(result.result)}

    except Exception as e:
        error_occurred = True
        final_output = {"text/plain": f"Exception: {traceback.format_exc()}"}

    finally:
        sys.stdout = sys.__stdout__  # Restore stdout
        sys.stderr = sys.__stderr__  # Restore stderr

    print("Final Output:", final_output)
    print("Error Occurred:", error_occurred)
    
    return final_output, error_occurred


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

# --

if __name__ == '__main__':
    execute_cell_universal("pritn('hello')")