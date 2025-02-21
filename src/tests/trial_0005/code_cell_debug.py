from prompts import JUPYTER_CELL_GEN_PROMPT
from query import query_llm
from parsing import extract_json, extract_code
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
        "You should write exactly according to this format:\n"
        "'[code]\n<code cell content>\n[/code].\nDo not include any additional text, only the [code]\n<code cell content>\n[/code]".
        Make sure each [code] and [/code] is on its own line, and has 1 square bracket on each side.
        """
        # The JUPYTER_CELL_GEN_PROMPT instructs the model to 
        # format the response as a sequence of markdown cell -> code cell.
        # Then we can extract the markdown/code
        
        # llm_response = query_llm(prompt_str, conversation_history=None, model="deepseek-coder:33b-instruct")
        llm_response = query_llm(prompt_str, conversation_history=None)
        # Make sure the response is formatted with the code blocks delimited by [[code]] and [[/code]]
        _prompt = f"Given the response you have provided with the code: {llm_response}, \
            make sure it is formatted with the code blocks delimited by [code] and [/code].\
            If it is not, please provide a response that is formatted with the code blocks delimited by [code] and [/code]."
        llm_response = query_llm(_prompt, conversation_history=None)
        cell_list = extract_code(llm_response)

        for cell in cell_list:
            # print('cell:', cell)
            # cell = json.loads(cell)
            cell_type = cell.get("cell_type", "code")
            cell_content = cell.get("content", "")
            
            # For code cells, execute them immediately and attach the output.
            if cell_type == "code":
                cell_output, error_occured = execute_cell_universal(cell_content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    cell_content,
                    cell_type='code',
                    output=new_output(output_type=output_type, data=cell_output)
                )
                CODE_CELL_CONTENT = cell_content
                CODE_CELL_OUTPUT = cell_output
                CODE_CELL_ERROR = error_occured

            elif cell_type == "markdown":
                cell_output, error_occured = execute_cell_universal(cell_content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    cell_content,
                    cell_type='markdown',
                    output=new_output(output_type=output_type, data=cell_output)
                )
        return CODE_CELL_CONTENT, CODE_CELL_OUTPUT, CODE_CELL_ERROR


    def chain_debug(self, cell_content, error_msg):
        """
        This will create a new code cell
        \TODO{get this to actually rewrite the cell}
        """
        
        plan_prompt = f"""
        Given the code cell:
        {cell_content}
        , and the error message:
        {error_msg}
        brainstorm some plans to debug the code, gathering any information you may need to debug the code.
        If the error comes from a specific object attribute or method,
        you may need to investigate the object's attributes and methods.
        """

        llm_response = query_llm(plan_prompt, conversation_history=None)

        plan_selection_prompt = f"""
        Given the plans: 
        {llm_response} 
        you have brainstormed to debug the code: 
        {cell_content} 
        with the error message: 
        {error_msg}
        compile the plans into a python list delimitted by 
        ```python
        [plan1, plan2, plan3]
        ```
        making sure that everything in between ```python and the second ``` can be evaluated by the python interpreter.
        """
        llm_response = query_llm(plan_selection_prompt, conversation_history=None)
        plan_dict_list = extract_code(llm_response)
        plans = []
        for plan_dict in plan_dict_list:
            plan = plan_dict.get("content", "")
            print('printing plan:', plan)
            if plan[0] != '[':
                plan = '[' + plan
            if plan[-1] != ']':
                plan = plan + ']'
            plans += plan

        plan_content = []

        # Now we need to use the plan to generate a sequence of cells
        # that will execute the plan.
        for plan in plan_dict_list:
            
            structure_prompt = f"""
            Given the plan you have provided:
            {plan}
            , generate a block of code that will execute the plan, gathering any information you may need.
            Store the gathered information in a dictionary called `debug_info`; if debug_info exists, add the information to it, and utilize its contents to plan your debugging.
            The last line of the code block should print out the debug_info.
            "You should write the cells exactly according to this format:\n"
            "'[code]\n<code cell content>\n[/code].\nDo not include any additional text, only the [code]\n<code cell content>\n[/code]".
            Make sure each [code] and [/code] is on its own line, and has 1 square bracket on each side.
            """
            llm_response = query_llm(structure_prompt, conversation_history=None)
            cell_list = extract_code(llm_response)

            for cell in cell_list:
                # print('cell:', cell)
                # cell = json.loads(cell)
                cell_type = cell.get("cell_type", "code")
                cell_content = cell.get("content", "")
                
                # For code cells, execute them immediately and attach the output.
                if cell_type == "code":
                    cell_output, error_occured = execute_cell_universal(cell_content)
                    output_type = "display_data" if "image/png" in cell_output else "execute_result"
                    add_cell_to_notebook(
                        self.notebook_path,
                        cell_content,
                        cell_type='code',
                        output=new_output(output_type=output_type, data=cell_output)
                    )
                    CODE_CELL_CONTENT = cell_content
                    CODE_CELL_OUTPUT = cell_output
                    CODE_CELL_ERROR = error_occured
                plan_content.append(f"\ncell_content: {cell_content}\ncell_output: {cell_output}")

        # piece it all together
        plan_content = "\n".join(plan_content)
        debug_prompt = f"""
        Given the information you have gathered:
        {plan_content}
        with the original cell:
        {cell_content}
        and the error message:
        {error_msg}
        generate the debugged version of the original cell.
        """
        llm_response = query_llm(debug_prompt, conversation_history=None)
        # Make sure the response is formatted with the code blocks delimited by [[code]] and [[/code]]
        _prompt = f"Given the response you have provided with the code: {llm_response}, \
            make sure it is formatted with the code blocks delimited by [code] and [/code].\
            If it is not, please provide a response that is formatted with the code blocks delimited by [code] and [/code]."
        llm_response = query_llm(_prompt, conversation_history=None)
        cell_list = extract_code(llm_response)
        for cell in cell_list:
            # print('cell:', cell)
            # cell = json.loads(cell)
            cell_type = cell.get("cell_type", "code")
            cell_content = cell.get("content", "")
            
            # For code cells, execute them immediately and attach the output.
            if cell_type == "code":
                cell_output, error_occured = execute_cell_universal(cell_content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    cell_content,
                    cell_type='code',
                    output=new_output(output_type=output_type, data=cell_output)
                )
                CODE_CELL_CONTENT = cell_content
                CODE_CELL_OUTPUT = cell_output
                CODE_CELL_ERROR = error_occured

            elif cell_type == "markdown":
                cell_output, error_occured = execute_cell_universal(cell_content)
                output_type = "display_data" if "image/png" in cell_output else "execute_result"
                add_cell_to_notebook(
                    self.notebook_path,
                    cell_content,
                    cell_type='markdown',
                    output=new_output(output_type=output_type, data=cell_output)
                )
        return CODE_CELL_CONTENT, CODE_CELL_OUTPUT, CODE_CELL_ERROR
