import os

os.environ['endpoint'] = "http://localhost:11434/api/chat" 


from jupyter import (
    create_notebook, start_streaming,
    execute_cell, execute_cell_universal, edit_cell_in_notebook,
    generate_cell_content, add_cell_to_notebook
)
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell, new_output

from query import query_llm
from prompts import MAIN_TASK_PROMPT, DATA_LOADING_FILE_CONTEXT_PROMPT
from parsing import extract_subtasks
from code_cell_debug import CodeCellDebugger


def main_llm():
    # Define the notebook path and create an empty notebook.
    notebook_path = './llm_generated_notebook.ipynb'
    create_notebook(notebook_path)
    
    # Start streaming the notebook content in a widget.
    stream_widget = start_streaming(notebook_path)
    print("Running in a live notebook session using the current kernel.")

    cell_content = "import matplotlib\nmatplotlib.use('Agg')\nprint('Successfully imported matplotlib.')"
        
    cell_output, error_occured = execute_cell_universal(cell_content)
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

    print('cell_content:', cell_content, 'cell_output:', cell_output)
    
    
    # Define the list of high-level tasks for the notebook.
    # tasks = [
    #     # "Set up a Jupyter notebook environment to house your analysis. Create an initial markdown cell explaining your plan and the approach you will take. Then create a code cell with the necessary imports and environment setup.",
    #     # "Determine what kind of spatial transcriptomics data you are working with. Create a markdown cell summarizing the approach/data, and a code cell that loads and inspects the data stored in the folder ../../read_only_sandbox/raw_data/.",
    #     "you are an autonomous bioinformatician. you have a collection of spatial transcriptomics datasets stored in ../../../read_only_sandbox/raw_data , there are h5 files storing counts matrices. write me a chunk of code in a jupyter notebook cell that will figure out what kind of data you are working with, by listing the files and reading them in, using python's nbformat api. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell. you can use glob to get all files.",
    #     "Set up a pipeline in the notebook to explore and preprocess the data. Include steps such as quality control, normalization, and initial visualization. Provide your thought process in a markdown cell, followed by the code. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell.  you can use glob to get all files if you need to.",
    #     "Set up a post-preprocessing pipeline to further process the data. This should include more detailed visualizations and parameter tuning. Provide your reasoning in a markdown cell and the corresponding code in another cell. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell.",
    #     "Develop a pipeline to make novel discoveries about the dataset. This may include discovering novel subpopulations, analyzing spatial relationships between cell types, performing pseudotime analysis, or identifying DEGs. Explain your approach in a markdown cell, and then provide the code. Use nbformat. Make sure any code you want to run is stored in a function called main(), and call main() at the end of the cell."
    # ]

    tasks_str = query_llm(MAIN_TASK_PROMPT)
    print('tasks_str:', tasks_str)
    # Take extra care to properly format tasks string.
    _prompt = f"Given the generated subtasks {tasks_str}, please respond with a list of tasks in the format '[[item]][[1:N]][[description-1:N]]'."
    tasks_str = query_llm(_prompt)
    tasks = extract_subtasks(tasks_str)
    tasks = [t for t in tasks if len(t) > 10] # make sure the task is not too short, e.g. empty or newline etc.
    print('generated tasks:', tasks)

    conversation_history = []
    # Process each high-level task one at a time.
    for task in tasks:
        task = task + '\nhere is context about the files: ' + DATA_LOADING_FILE_CONTEXT_PROMPT + '\n \
            use that if you have not loaded in the data, otherwise ignore it.'
        task_history = ""
        task_addressed = False
        # Generate the cell content for the current task.
        idx = 0
        NUM_TRIES = 10
        while not task_addressed and idx <= NUM_TRIES:
            cell_list, llm_raw_response = generate_cell_content(task, conversation_history)
            print('cell_list:', cell_list)
            
            # For each cell returned by the LLM, add it to the notebook.
            for cell in cell_list:
                print('cell:', cell)
                # cell = json.loads(cell)
                cell_type = cell.get("cell_type", "code")
                cell_content = cell.get("content", "")
                # print('--------------------------------')
                # print(cell_type, content)
                # print('--------------------------------')
                # add_cell_to_notebook(notebook_path, content, cell_type=cell_type)
                
                # For code cells, execute them immediately and attach the output.
                if cell_type == "code":
                    cell_output, error_occured = execute_cell_universal(cell_content)
                    output_type = "display_data" if "image/png" in cell_output else "execute_result"
                    output = new_output(
                        output_type=output_type, 
                        data=cell_output
                    )
                    add_cell_to_notebook(
                        notebook_path,
                        cell_content,
                        cell_type='code',
                        output=output
                    )
                    while error_occured:
                        error_msg = cell_output
                        print('debugging error_msg:', error_msg)
                        # debug the cell
                        cell_debugger = CodeCellDebugger(notebook_path)
                        cell_content, cell_output, error_occured = cell_debugger.run_debug(cell_content, error_msg)
                        print('error occured:', error_occured)
                    # append to task history when debugging is complete
                    task_history = task_history + "\n\ncell_content: " + str(cell_content) + "\n\ncell_output: " + str(cell_output)
                elif cell_type == "markdown":
                    cell_output, error_occured = execute_cell_universal(cell_content)
                    output_type = "display_data" if "image/png" in cell_output else "execute_result"
                    output = new_output(
                        output_type=output_type, 
                        data=cell_output
                    )
                    add_cell_to_notebook(
                        notebook_path,
                        cell_content,
                        cell_type='markdown',
                        output=output
                    )
                    task_history = task_history + "\n\ncell_content: " + str(cell_content) + "\n\ncell_output: " + str(cell_output)
            # check if task is complete
            print('checking if task is complete...')
            prompt_str = f"Based on the generated cells, have you adequately (i.e. at least minimally, and ideally moderately) completed the task: {task}? Here is the task history: {task_history} If yes, respond ONLY with the lowercase letter 'y'. If no, respond ONLY with the lowercase letter 'n'. Make sure the response is exactly one character."
            # prompt_str = f"Based on the generated cells, have you adequately (i.e. at least minimally, and ideally moderately) completed the task: {task}? If yes, respond ONLY with the lowercase letter 'y'. If no, respond ONLY with the lowercase letter 'n'. Make sure the response is exactly one character."
            payload = {
                "model": "deepseek-r1:70b",
                "messages": [{"role": "system", "content": prompt_str}]
            }
            # The following is SUCH a hack but seems to work for now. 
            # \TODO{make the task_addressed robust.}
            task_addressed_str = query_llm(prompt_str, conversation_history).strip().lower().replace('\n', '')
            print('task addressed:', task_addressed_str, ' | length: ', len(task_addressed_str))
            task_addressed = task_addressed_str[-1] == 'y'
            print('task addressed:', task_addressed)
            conversation_history.append("\n\ncell_content: " + str(cell_content) + "\n\ncell_output: " + str(cell_output))
            idx += 1
    
    print("Notebook generation complete!")


if __name__ == '__main__':
    main_llm()