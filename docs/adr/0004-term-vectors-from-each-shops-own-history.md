# 0004. Learn term vectors from each shop's own search-to-purchase history

**Context.** The semantic side needs embeddings. A general-purpose model was not available in this environment,
and the words that matter are shop-specific: "jubilee clip" is a hose clamp in one shop and nothing in another.

**Decision.** For each tenant, `tfs.learn.terms` builds a term-by-product matrix from product text and from the
words of queries that ended in a purchase of that product, takes positive PMI and a truncated SVD (32 dimensions),
and publishes `<tenant>.json`. The service embeds text as the idf-weighted mean of known term vectors. A model is
trained only on its own tenant's data and loaded only for that tenant.

**Consequences.** Shopper words that never appear in titles ("raincoat", "couch", "jubilee clip") land next to the
merchant's words. Unseen words get no vector, which the router treats as "go lexical". Swapping in a pretrained
encoder means replacing `Embedder` and the trainer; the index mapping's `dims` and `embedding.dim` must match.
