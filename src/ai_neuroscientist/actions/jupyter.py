import base64
from io import StringIO, BytesIO
import os
import sys
import threading
import time
from typing import Literal

from IPython import get_ipython
from IPython.display import display, Javascript
import ipywidgets as widgets
import matplotlib.pyplot as plt
import nbformat
from nbformat.v4 import (
    new_notebook, 
    new_markdown_cell, 
    new_code_cell, 
    new_output
)
import numpy as np
import pandas as pd


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
# UTILITIES FOR LIVE NOTEBOOK UI REFRESH (HACK)
# ----------------------------------------------------------------------------
def refresh_notebook_ui():
    """
    Attempts to force the notebook front-end to refresh.
    In classic Notebook, this can trigger a re-read of the .ipynb file.
    """
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
from io import StringIO
import sys

def execute_cell(cell_code: str):
    ipython = get_ipython()
    if ipython is None:
        from IPython.core.interactiveshell import InteractiveShell
        ipython = InteractiveShell.instance()
    
    # Redirect stdout to capture print() statements
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer
    
    try:
        result = ipython.run_cell(cell_code)
        execution_output = stdout_buffer.getvalue().strip()  # Get printed output
        
        # If there's a result (e.g., 1+1), use it, otherwise use captured stdout
        final_output = result.result if result.result is not None else execution_output
    finally:
        sys.stdout = sys.__stdout__  # Restore normal stdout

    return str(final_output)  # Ensure it's a string


def execute_cell_universal(cell_code: str):
    """
    Executes a code cell in IPython, capturing:
    - Print statements (stdout)
    - Returned values (expressions like 1+1)
    - Matplotlib figures (if generated)
    
    Returns a properly formatted output.
    """
    ipython = get_ipython()
    if ipython is None:
        from IPython.core.interactiveshell import InteractiveShell
        ipython = InteractiveShell.instance()
    
    # Capture stdout (print statements)
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer

    # Clear previous figures
    plt.close("all")
    
    try:
        # Run the cell
        result = ipython.run_cell(cell_code)

        # Capture stdout output
        execution_output = stdout_buffer.getvalue().strip()

        # Capture return value (expressions like `1 + 1`)
        return_value = result.result if result.result is not None else ""

        # Capture Matplotlib figure if generated
        fig = plt.gcf()
        if fig and fig.get_axes():  # Check if a figure was created
            buf = BytesIO()
            fig.savefig(buf, format="png")  # Save figure to buffer
            buf.seek(0)
            encoded_img = base64.b64encode(buf.read()).decode("utf-8")

            # Return an image output
            final_output = {"image/png": encoded_img}
        else:
            # If no figure, use text output (either return value or stdout)
            final_output = str(return_value) if checks_out(return_value) else execution_output
            final_output = {"text/plain": final_output}

    
    finally:
        sys.stdout = sys.__stdout__  # Restore stdout
    
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
