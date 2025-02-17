import sys
import time
import threading

sys.path = ['..'] + sys.path


from ai_scientist.actions.jupyter_staging import *



"""
Steps:

1. create notebook

2. start streaming

3. start ipython session

4. dummy cell add/edit + execute in a lagged loop
"""

# ----------------------------------------------------------------------------
# MAIN FUNCTION: RUN INSIDE THE NOTEBOOK
# ----------------------------------------------------------------------------
def main():
    # Define the notebook file (this file will be modified on disk).
    notebook_path = './test_notebook.ipynb'
    
    # 1. Create a new empty notebook.
    create_notebook(notebook_path)
    
    # 2. Start streaming the notebook file in a widget.
    stream_widget = start_streaming(notebook_path)
    
    # 3. Since we are running inside a live notebook, we already have an active IPython session.
    print("Running in a live notebook session using the current kernel.")

    cell_content = "import matplotlib\nmatplotlib.use('Agg')"
        
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
    
    # 4. In a loop, add new code cells to the notebook file and execute their content.
    from random import randint
    for idx in range(20):
        num1 = randint(0, 100)
        num2 = randint(0, 100)

        # -----------------------------
        # print output
        
        cell_content = f"print('hello world {idx}')"
        
        print(f"Executing cell: {cell_content}")
        
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

        time.sleep(1)  # Delay to simulate processing time
        
        # -------------------------------
        # numerical operation output
        
        numerical_content_only = f"{num1} - {num2}"

        print(f"Executing cell: {numerical_content_only}")
        
        cell_output = execute_cell_universal(numerical_content_only)
        output_type = "display_data" if "image/png" in cell_output else "execute_result"
        
        output = new_output(
            output_type=output_type, 
            data=cell_output
        )
        
        add_cell_to_notebook(
            notebook_path, 
            numerical_content_only, 
            cell_type='code', 
            output=output
        )

        time.sleep(1)  # Delay to simulate processing time

        # -------------------------------
        # show pandas dataframe output

        cell_content = f"import pandas as pd\n"
        cell_content += "import numpy as np\n"
        cell_content += "df = pd.DataFrame(np.random.rand(100, 5))"
        cell_content += "\ndf"
        print(f"Executing cell: {cell_content}")
        
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
            output=output
        )

        time.sleep(1)  # Delay to simulate processing time

        # ----------------------
        # display df.corr()

        cell_content = "import matplotlib.pyplot as plt\nimport seaborn as sns\nsns.heatmap(df.corr())\nplt.show()"
        print(f"Executing cell: {cell_content}")
        
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
            output=output
        )

        time.sleep(1)  # Delay to simulate processing time
        

# ----------------------------------------------------------------------------
# Run main if executed as a script (this cell should be run in a Notebook)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    main()