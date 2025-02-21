The plan for this trial is to:

1. improve the data loading. It may be that we need to supply the pattern to find the h5ad files in the prompt.
Can try that for now.

2. Use the debugger agent. From preliminary runs, it seems necessary for data loading.

Note to self: I should make a file explorer agent, in case no actual folders/paths are supplied.
Simply passing some file pattern as a prompt and hoping the rest is handled is fragile.

Note to self: simply passing the whole conversation history as part of the prompt is a bad idea.
Instead, I should probably store embeddings of past results and do RAG with these embeddings.