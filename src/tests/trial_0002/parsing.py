import json
import re
from typing import List


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


def extract_subtasks(subtasks_str: str) -> List[str]:
    """
    The subtasks will be formatted like 
    [[item]][[1][[task_description_1]]
    ...
    [[item]][[N]][[task_description_N]]
    """
    
    pattern = r"\[\[item\]\]\[\[(\d+)\]\]\[\[(.*?)\]\]"   # Updated to match exactly the desired format
    matches = re.findall(pattern, subtasks_str) 

    matches = [match[1].strip() for match in matches]   # Return only the description part (without leading or trailing whitespace)
    if not matches:
        print("Couldn't find subtasks using the pattern. Trying a different pattern.")
        # try parsing between [[item]] and [[item]] if the above pattern fails
        pattern = r"\[\[item\]\]\[\[(\d+)\]\]\[\[(.*?)\]\]"
        matches = re.findall(pattern, subtasks_str)
        matches = [match[1].strip() for match in matches]
    if not matches:
        pattern = re.compile(r"[\[\(\{\n]?\s*(\d+)\s*[\.\]\)\}]", re.MULTILINE)

        steps = {}
        matches = list(pattern.finditer(subtasks_str))

        for i, match in enumerate(matches):
            step_num = int(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(subtasks_str)
            
            steps[step_num] = subtasks_str[start:end].strip()

        return list(steps.values())
    
    return matches
    




if __name__ == '__main__':
    # s = "test_bad [[item]][[1]][[1 should go]] this should not [[item]][[2]][[2good]] bbaadd"
    # print(extract_subtasks(s))
    s = """1. **Import Necessary Libraries**: This is an atomic step because it can be done with a simple code block without requiring outputs from other steps.
    2. **Load Data**: This involves locating h5ad files in the directory and reading them into AnnData objects. It's broken down into two substeps since each part is straightforward but necessary.
    3. **Basic Data Exploration**: Another atomic step to understand the dataset quickly through basic statistics.
    4. **Preprocessing**: Includes filtering cells based on gene counts, normalizing data, logging transformation, and removing mitochondrial genes. Each preprocessing task is a separate substep because they can be executed linearly without trial and error.
    5. **Dimensionality Reduction (PCA)**: Perform PCA to reduce data dimensions for downstream analysis. Atomic since it's a direct computation.
    6. **UMAP for Visualization**: Use UMAP to project cells into 2D space for visualization, which is an atomic step after PCA.
    7. **Clustering with Leiden Algorithm**: Cluster cells based on their expression profiles using the Leiden algorithm. This is atomic and follows directly from the UMAP computation.
    8. **Marker Gene Identification**: Identify genes that distinguish each cluster. This is broken down into two substeps: running the rank_genes_groups function and visualizing results.
    """
    print(extract_subtasks(s))
