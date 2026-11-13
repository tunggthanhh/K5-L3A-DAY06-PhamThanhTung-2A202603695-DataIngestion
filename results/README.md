# Results

Generated artifacts are kept in [starter/results](../starter/results):

- `metrics.json`: automatic Hit@1 and Evidence Hit@3 by strategy and split.
- `traces.json`: full top-3 retrieval trace for every question and strategy.
- `qdrant/`: persistent local Qdrant index; regenerate with `python -m src.run`.

Manual audit labels must be added before submission; do not invent them.
