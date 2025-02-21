JUPYTER_CELL_GEN_PROMPT = (
    "Please generate a JSON-formatted list of Jupyter notebook cells to complete this task."
    "You should return exactly two cells: "
    "(1) a markdown cell describing your plan of attack based on the task, history, and previous cell output, and "
    "(2) the code to run in the notebook to accomplish the task or subtask."
    # "Please generate a JSON-formatted list of Jupyter notebook cells to complete this task. "
    "Each cell should be an object with keys 'cell_type' (either 'markdown' or 'code') and "
    "'content' (the cell content). Do not include any additional text, only output valid JSON that starts with '[' and ends with ']'."
    "Make sure that the keys of the JSON objects are exactly 'cell_type' and 'content'."
)

MAIN_TASK_PROMPT = """
Your task is design a pipeline using scanpy (import scanpy as sc) to make novel discoveries about a spatial transcriptomics dataset. 
the files are h5ad files located somewhere in the directory ../../../read_only_sandbox/raw_data/Cb
, in some subfolder maybe. 
I will tell you now that the pattern to find the h5ad files is 'glob.glob(f"../../../read_only_sandbox/raw_data/Cb/**/*.h5ad", recursive=True)'. Use that to load the data.
Using the information about the task and the file locations, break down the pipeline into conceptual steps, and enumerate their order like 
'[[item]][[1]][[description-1]]', '[[item]][[2]][[description-2]]', ..., '[[item]][[N]][[description-N]]'. 
be sure to return them with '[[item]][[1:N]][[description-1:N]]' as described before. 
For each step 1-N, determine whether the step is 'atomic', 
i.e. its objective can be satisfied by a chunk of code without having to refer to its outputs. 
If yes, write the code and proceed to the next step. 
Otherwise, for step j, break down step j into M substeps j.1, ..., j.M if it is considered to be a 'linear' task, 
i.e. it does not require many trial and error; 
otherwise if it is considered 'exploratory', i.e. you may need to try a few approaches before something works, 
generate candidate approaches and test them out.
Again, I want to stress: make sure for each step, you return something that looks like
"[[item]][[1]][[<description-of-approach-1>]]" EXACTLY FOLLOWING THIS FORMAT. It is crucial for parsing. So do it.
Include in <description-of-approach-1> EVERYTHING that is part of the approach, icluding atomic/exploratory, code, and substeps.
One last time, make sure each step is recorded as [["item"]][[index]][[description]].
Do NOT just list the steps like 1. 2. 3., but like "[[item]][[1]][[<description>]]". "[[item]][[2]][[<description>]]"
Here is an example of what I mean:
"[[item]][[1]][['description': 'Import data analysis libraries', 'atomic': True, 'code': 'import numpy as np\nimport pandas as pd'\nimport anndata as ad]]", 
"[[item]][[2]][['description': 'Load the data', 'atomic': False]]", 
"[[item]][[2.1]][['description': 'Find h5ad files in folder', 'atomic': True, 'code': 'h5ad_files = glob.glob(f"{folder_path}/**/*.h5ad", recursive=True)']]",
""[[item]][[2.2]][['description': 'Read in the h5ad files', 'atomic': True, 'code': 'adata = sc.read(h5ad_files)']]",
"[[item]][[3]][['description': 'Preprocess the data', 'atomic': True, 'code': 'sc.pp.filter_cells(adata, min_genes=200)\n#...']]".
"""

DATA_LOADING_FILE_CONTEXT_PROMPT = """
the files are h5ad files located somewhere in the directory ../../../read_only_sandbox/raw_data/Cb
, in some subfolder maybe. 
I will tell you now that the pattern to find the h5ad files is 'glob.glob(f"../../../read_only_sandbox/raw_data/Cb/**/*.h5ad", recursive=True)'. Use that to load the data.
"""