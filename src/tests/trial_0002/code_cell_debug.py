from prompts import JUPYTER_CELL_GEN_PROMPT
from query import query_llm
from parsing import extract_json
from jupyter import (
    execute_cell_universal,
    add_cell_to_notebook
)
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell, new_output

import os



class CodeCellDebugger:
    def __init__(self, notebook_path):
        self.notebook_path = notebook_path
        self.runs = []
        self.num_rewrites = 0

    def run_debug(self, cell_content, error_msg):
        """
        This will create a new code cell
        \TODO{get this to actually rewrite the cell}
        """
        
        prompt_str = f"""
        Given the code cell:
        {cell_content}
        , and the error message:
        {error_msg}
        , rewrite the code to fix the issue.
        {JUPYTER_CELL_GEN_PROMPT}
        """
        # The JUPYTER_CELL_GEN_PROMPT instructs the model to 
        # format the response as a sequence of markdown cell -> code cell.
        # Then we can extract the markdown/code
        
        llm_response = query_llm(prompt_str)
        cell_list = extract_json(llm_response)

        for cell in cell_list:
            print('cell:', cell)
            # cell = json.loads(cell)
            cell_type = cell.get("cell_type", "code")
            content = cell.get("content", "")
            
            # For code cells, execute them immediately and attach the output.
            if cell_type == "code":
                cell_output = execute_cell_universal(content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    content,
                    cell_type='code',
                    output=new_output(output_type=output_type, data=cell_output)
                )
            elif cell_type == "markdown":
                cell_output = execute_cell_universal(content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    content,
                    cell_type='markdown',
                    output=new_output(output_type=output_type, data=cell_output)
                )