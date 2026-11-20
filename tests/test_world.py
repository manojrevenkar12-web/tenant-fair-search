"""The world: deterministic, its truth hidden from the feed, and its queries answerable."""

from tfs.world.shops import Intent, Product, grade, world

HIDDEN = {"category", "features"}


def test_same_seed_same_world(shops):
    again = world(6101)
    assert [p.feed() for p in again[0].products[:50]] == [p.feed() for p in shops[0].products[:50]]
    assert [q.text for q in again[1].queries] == [q.text for q in shops[1].queries]


def test_the_feed_carries_no_hidden_attribute(shops):
    for s in shops:
        assert not HIDDEN & set(s.products[0].feed())


def test_product_ids_are_unique_across_tenants(shops):
    ids = [p.id for s in shops for p in s.products]
    assert len(ids) == len(set(ids))


def test_every_query_has_a_good_answer(shops):
    for s in shops:
        for q in s.queries:
            assert any(g >= 2 for g in s.grades(q).values()) or q.shape != "sku", q.text
            if q.shape == "sku":
                assert s.grades(q) == {q.intent.target: 3}


def test_shoppers_use_words_merchants_do_not(shops):
    outdoor = next(s for s in shops if s.name == "outdoor")
    titles = " ".join(p.title.lower() + " " + p.description.lower() for p in outdoor.products)
    typed = " ".join(q.text for q in outdoor.queries)
    shopper_only = ["raincoat", "knapsack", "sleep sack", "walking boots"]
    assert any(w in typed for w in shopper_only)
    leaked = [w for w in shopper_only if w in titles]
    assert leaked == []


def test_grades():
    p = Product("x", "AB-1", "t", "d", "vela", "navy", "m", 100.0, True, "rain_jacket", ("waterproof",))
    assert grade(p, Intent(category="tent")) == 0
    assert grade(p, Intent(category="rain_jacket", colour="red")) == 1
    assert grade(p, Intent(category="rain_jacket", max_price=90.0)) == 1
    assert grade(p, Intent(category="rain_jacket", features=("packable",))) == 2
    assert grade(p, Intent(category="rain_jacket", features=("waterproof",), colour="navy")) == 3
    assert grade(p, Intent(target="x")) == 3


def test_agents_send_constraints_as_fields(shops):
    agents = [q for s in shops for q in s.queries if q.shape == "agent"]
    assert agents and all(isinstance(q.filters, dict) for q in agents)
    assert any("maxPrice" in q.filters for q in agents)
