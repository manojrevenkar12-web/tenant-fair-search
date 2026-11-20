# Runbook: relevance dropped after a change

**Signal.** The dev evaluation's nDCG@10 for `routed` fell, the gate failed, or a shop reports worse results.

1. Compare the new `reports/dev.json` with the last committed one: which query shape moved (`by_shape`), and did
   `violations_top10` or `zero_results` move with it?
2. Shape-specific drops usually mean a setting: `retrieval.weights` (sentences, agents), `understanding` phrases
   (price words, colour synonyms) or `lexicalFields`.
3. A drop for one shop only usually means its term model: retrain from its feed and logs, check the vocabulary size
   in `prepared` in the report, then re-index that shop.
4. Revert the change, or keep it only if the paired interval against the previous `routed` result excludes zero.
5. Never use held-out numbers to decide.
