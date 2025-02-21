I've implemented: 

* better parsing

* Main task breakdown into subtasks

And have refactored the codebase.

I've started implementing the programmatic tree of thoughts class but haven't finished it. That's for the next few trials.

I've also implemented ability to generate "atomic" vs. "exploratory" tasks; for exploratory, 

I've implemented a debugger agent too. Not using it currently but that's also for the next few trials.

## Issues

1. The agent has hallucinated some Python package named `spage`, and gets stuck trying to import / install it

2. The agent seems to convince itself that the supposed package called `spage` supplied in the task prompt is not actually 
a PyPI package, maybe it's a command line tool or deprecated etc... however, because the agent is currently incapable of modifying the prompt
and just seems to 

## Next steps

1. make the data loading portion robust. this is the most vital task right now.

2. allow agent to modify task in the while-loop if it finds some issue with it, e.g. it says to use a package that doesn't exist.

3. utilize debugger agent

4. tree of thoughts

5. better handling of atomic vs. exploratory tasks, emphasis on exploratory 
(this will come after fixing atomic issues such as finding and loading data, as well as previous three points.)

... I'm also thinking I should have the model generate sufficient cell output conditions for satisfying a subtask.
For instance, in the case of data loading task, maybe the model would say something like 
"a concatenated anndata object", but then maybe the agent would have to scan the `locals()` and `globals()`.