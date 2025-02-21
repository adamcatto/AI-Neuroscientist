interesting to note: at one point, the model actually checked `locals()` to see if adata was defined.

The approach as it stands just does not work. It keeps getting stuck and forgetting to return a markdown cell
followed by a code cell.

I think this is in part because we pass the whole history as part of the prompt, including the thought process.
This doesn't work.

I think it makes more sense to just pass the code cell content so the model knows what has been defined.
Alternatively, we can pass the outputs of `locals()` and `globals()` but I am not sure this is ideal...