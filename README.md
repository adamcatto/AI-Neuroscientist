# AI-Neuroscientist

An experimental **autonomous bioinformatics research agent**. Given a high-level
research goal and a folder of spatial / single-cell transcriptomics data, the
agent uses a local LLM to plan an analysis, then *writes and executes* a Jupyter
notebook cell-by-cell — generating markdown rationale, running `scanpy`-based
code, capturing the output (including figures), and self-correcting when a cell
errors. Uses pure orchestration + prompt engineering (no post-training) and access to an IPython REPL.

This project was undertaken to learn how to use LlamaIndex to orchestrate local LLM-based agents,
with a focus on automating bioinformatics analysis tasks.

The repository is organized as a sequence of **trials** (`trial_0000` …
`trial_0005`), each a self-contained snapshot of the pipeline plus a
`post_mortem.md` recording what worked, what broke, and what to try next. The
project is a research log as much as a codebase.

> Status: experimental / research. The agent does not reliably complete a full
> analysis end-to-end; see [Findings & limitations](#findings--limitations).

---

## What it does

1. **Plan** — Ask the LLM to decompose a main research task (e.g. *"design a
   `scanpy` pipeline to make novel discoveries about a spatial transcriptomics
   dataset"*) into an ordered list of subtasks.
2. **Generate** — For each subtask, ask the LLM for a markdown cell (its plan of
   attack) followed by a code cell.
3. **Execute** — Run the code cell *in-process* against a live IPython kernel,
   capturing stdout, stderr/exceptions, and any matplotlib figure.
4. **Debug** — If the cell raises, hand the code + error message to a debugging
   agent that investigates and rewrites the cell, looping until it runs clean.
5. **Self-assess** — Ask the LLM whether the subtask is adequately complete
   (`y`/`n`); if not, iterate (up to 10 tries) before moving on.
6. **Persist** — Every cell (and its output) is appended to
   `llm_generated_notebook.ipynb` via `nbformat`, and a live widget streams the
   notebook file as it grows.

---

## Architecture

The mature pipeline (`src/tests/trial_0005`) is split into focused modules:

| File | Responsibility |
|------|----------------|
| `main.py` | Orchestrator. Creates the notebook, generates the task plan, runs the per-subtask generate → execute → debug → self-assess loop. |
| `query.py` | Thin client for a **local Ollama** LLM endpoint (`http://localhost:11434/api/chat`, model `deepseek-r1:70b`). Streams tokens and concatenates the response. |
| `prompts.py` | The main task prompt, the per-cell generation prompt, and the data-loading file-context prompt. |
| `parsing.py` | Robust extraction from messy LLM text: JSON cell lists (`extract_json`), the custom subtask format (`extract_subtasks`), and fenced/delimited code blocks (`extract_code`). Multiple regex fallbacks because the model rarely follows the format exactly. |
| `jupyter.py` | Programmatic notebook building (`create_notebook`, `add_cell_to_notebook`, `edit_cell_in_notebook`) and in-process execution (`execute_cell_universal`) that captures stdout, errors, and figures as base64 PNG. Also `start_streaming` for the live-tail widget. |
| `code_cell_debug.py` | `CodeCellDebugger` with two strategies: `run_debug` (one-shot rewrite from the error) and `chain_debug` (brainstorm debug plans → run probe cells that gather info into a `debug_info` dict → synthesize a fixed cell). |
| `tree_of_thoughts.py` | `ProgramTreeOfThoughts` — a recursive task-decomposition scaffold. Sketched but **not finished / not wired in**. |
| `actions/` (package) | Early home for external tools: `web_search.py` (stubs for bioRxiv / PubMed / Google Scholar / Gene Ontology queries — not implemented) and a library version of the `jupyter.py` helpers. |

### The notebook-as-state idea

There is no hidden agent scratchpad: **the notebook *is* the state.** Cells are
executed in a single shared IPython `InteractiveShell`, so variables defined in
one generated cell persist into the next, exactly as in an interactive session.
Output capture distinguishes three cases — a returned/printed value, a runtime
error (which triggers debugging), or a matplotlib figure (saved as an embedded
PNG).

### Subtask format

The planner is prompted to emit subtasks in a bracket-delimited format that
`extract_subtasks` parses:

```
[[item]][[1]][[<description of step 1>]]
[[item]][[2]][[<description of step 2>]]
...
```

Each step is also tagged `atomic` (codeable in one shot) vs. `exploratory`
(needs trial-and-error). In practice the model often ignores the format, so the
parser has a cascade of fallbacks (enumerated lists, numbered lines, etc.) and
`main.py` will re-prompt the model to reformat.

---

## Trials

Each trial directory is a frozen snapshot — `main.py`, the supporting modules,
the resulting `llm_generated_notebook.ipynb`, a short `README.md` (the plan
going in), and a `post_mortem.md` (what happened). The arc:

| Trial | Change introduced | Outcome (from post-mortem) |
|-------|-------------------|----------------------------|
| **0000** | Monolithic `test_bioinformatician.py`: fixed list of high-level tasks, generate cells once per task, no iteration. | Falls apart when it errs — no within-task experimentation; can't recover from a bad cell. |
| **0001** | Added a **task loop** (keep adding/running cells until the task is judged complete). | Gets stuck in loops: re-attempts the original task the same way and repeats the same error. Motivated isolating debugging and exploring tree-of-thoughts. |
| **0002** | Refactored the monolith into modules (`main.py`, `query.py`, `prompts.py`, `parsing.py`, `jupyter.py`). LLM now **breaks the main task into subtasks**; atomic-vs-exploratory tagging; debugger agent implemented (not yet used). | Hallucinates a nonexistent package (`spage`) and gets stuck importing/installing it. Can't yet modify a faulty task. Data loading flagged as the priority to fix. |
| **0003** | Pass the **glob pattern for the `.h5ad` files** directly in the prompt to make data loading robust. | Once checked `locals()` for `adata` — promising — but still gets stuck and forgets the required markdown-then-code structure. Suspected cause: passing the entire history (incl. chain-of-thought) into every prompt. |
| **0004** | Continued iterating on data loading / debugger usage. | A bit better, but still stuck; makes many simple coding errors. Clear need for a dedicated code-correction step. |
| **0005** | Latest. **`chain_debug`** wired into the main loop; temperature lowered for planning; task plan written into the notebook; anndata-concat hint added to each subtask. | Plans are fine, but autonomous coding is still poor — repeatedly stuck on third-party libraries (`scanpy`, `anndata`). Conclusion: need **RAG over library docs/source** and a dedicated multi-agent framework. |

`src/tests/STABLE_llm_generated_notebook.ipynb` is a known-reasonable reference
output kept outside the trial folders.

---

## Data

The agent expects spatial / single-cell transcriptomics data as `.h5ad`
(AnnData) files under `read_only_sandbox/raw_data/`. That directory is
**user-provided** and not committed — `read_only_sandbox/README.md` simply says:
*"Place your data in `./raw_data/`."* The trial prompts hard-code the glob
pattern `read_only_sandbox/raw_data/Cb/**/*.h5ad`.

The name "read-only sandbox" reflects the intent: the agent may read and analyze
the data but should not mutate the source files.

---

## Running it

> Prerequisites: a local [Ollama](https://ollama.com) server running with the
> `deepseek-r1:70b` model pulled, and a Python env with `scanpy`, `anndata`,
> `nbformat`, `ipywidgets`, `matplotlib`, `numpy`, `pandas`, `requests`.

```bash
# 1. start Ollama and pull the model
ollama pull deepseek-r1:70b

# 2. drop your .h5ad data under read_only_sandbox/raw_data/

# 3. run the latest trial from inside its directory
#    (paths in the prompts are relative, e.g. ../../../read_only_sandbox/...)
cd src/tests/trial_0005
python main.py
```

The run produces / overwrites `llm_generated_notebook.ipynb` in the trial
directory and prints the streamed LLM output to the console.

To point at a different model or endpoint, edit `query.py` (or set the
`endpoint` environment variable, which `main.py` sets to the Ollama chat URL).

---

## Findings & limitations

Distilled from the post-mortems — useful context before extending this:

- **Local coding ability is the bottleneck.** Planning is acceptable; reliably
  *writing working `scanpy`/`anndata` code* is not. The agent gets stuck on
  trivial library-API issues and on hallucinated packages.
- **Dumping full history (including chain-of-thought) into every prompt hurts.**
  It causes the model to fixate and repeat the same failing approach. Proposed
  fix: pass only executed code / relevant state, or do RAG over prior results.
- **The format contract is fragile.** Relying on the model to emit exact
  `[[item]]…` / JSON structure needs heavy parser fallbacks and re-prompting.
- **Self-assessment (`y`/`n`) is a hack** and not robust.
- **Next directions noted by the author:** RAG over third-party library
  docs/source; a file-explorer agent for when no path is given; embedding-based
  retrieval over past cell outputs instead of raw history; a human-in-the-loop
  GUI to pause/edit the agent's tasks; and likely adopting a dedicated
  multi-agent framework (LlamaIndex) as complexity grows.

---

## Repository layout

```
read_only_sandbox/        # user-provided data goes in raw_data/ (not committed)
src/
  ai_neuroscientist/       # early library package
    actions/               # jupyter helpers + web_search stubs
  tests/
    trial_0000/ … 0005/    # frozen pipeline snapshots + post-mortems + outputs
    STABLE_llm_generated_notebook.ipynb
```
