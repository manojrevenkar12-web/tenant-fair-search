# 0001. Measure on simulated shops with a hidden truth, every design on the same luck

**Context.** Relevance work needs graded judgements, and isolation work needs a burst you can replay. Real
catalogues and click logs are not available here, and click-through measured on a live system grades the system
that produced the clicks.

**Decision.** A world (`tfs/world`) generates four shops per seed (outdoor, fashion, industrial parts, home) with
products whose category and features are hidden. Merchants and shoppers name things with different words
(`config/catalogue.yaml`), shoppers and AI agents phrase queries in four shapes, and every product is graded 0 to 3
against every query's intent. The platform sees only the feed, the queries and a history of search-then-purchase
sessions. All draws are keyed by seed and purpose, so every design answers identical queries and both admission
modes face identical arrivals.

**Consequences.** Numbers are about the simulated shops. The vocabulary gap, the share of sentences and agents,
and the purchase noise are assumptions written in config, and changing them changes the results.
