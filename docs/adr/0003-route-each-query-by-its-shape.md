# 0003. Understand the query, then route it by shape instead of fusing every query

**Context.** Fusing lexical and vector results with reciprocal rank fusion on every query helps sentences and
synonyms, but it pays for a vector search on SKU lookups that only an exact match can answer, embeds words the
shop's model has never seen, and keeps "under 120 euros" as text to match instead of a constraint.

**Decision.** `Parser` classifies the query (SKU, keyword, sentence, agent) and extracts constraints (price bounds,
colour, brand, size, stock) using only the tenant's own facet values from the index and the phrases in config.
Explicit agent fields win over extracted ones. `Router` then picks the plan: SKU lookups go to an exact term match
and skip the vector search; queries the model cannot embed go lexical; everything else is fused, with per-shape
weights from config. Filters are hard (`filter` clauses in both the lexical query and the kNN pre-filter).

**Consequences.** The ablations in the README separate the two parts: most of the relevance gain comes from query
understanding; routing mostly saves cluster time. A wrong extraction removes good products, so extraction only
uses values the tenant actually has.
