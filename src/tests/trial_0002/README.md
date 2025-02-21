This time you run the pipeline with `python main.py`. I've refactored the sprawling / disorganized `test_bioinformatician.py` and removed it.

There's some functionality I've at least implemented like debugging and tree of thoughts, but these are not used currently.

In this iteration, the agent breaks down a main task prompt

Note to self: refactor the main task prompt to take in user-specified context about the experiments as well.

Another note to self: I really want this to be human-in-the-loop. 
I eventually want to create a GUI that stores the agent's state (e.g. its subtasks, notebook, updates to tasks over time, etc.)
with which the user can interact, pausing the agent's execution and modifying the tasks.
This will come into play when the agent is more robust.