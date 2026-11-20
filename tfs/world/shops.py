"""The simulated shops, their shoppers and agents, and the truth about what each query was looking for.

Products carry hidden attributes (category and features) that never leave the world. The platform sees what a
real platform sees: the product feed, the queries, and a history of searches and purchases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

import numpy as np

from tfs import settings
from tfs.world.luck import stream


@dataclass(frozen=True)
class Product:
    id: str
    sku: str
    title: str
    description: str
    brand: str
    colour: str
    size: str
    price: float
    in_stock: bool
    category: str  # hidden
    features: tuple[str, ...]  # hidden

    def feed(self) -> dict:
        """What the shop sends to the search platform."""
        return {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "description": self.description,
            "brand": self.brand,
            "colour": self.colour,
            "size": self.size,
            "price": self.price,
            "inStock": self.in_stock,
        }


@dataclass(frozen=True)
class Intent:
    category: str | None = None
    colour: str | None = None
    features: tuple[str, ...] = ()
    brand: str | None = None
    size: str | None = None
    max_price: float | None = None
    in_stock: bool = False
    target: str | None = None  # a SKU lookup wants exactly one product


@dataclass(frozen=True)
class Query:
    id: str
    tenant: str
    shape: str  # sku, keyword, sentence, agent
    text: str
    filters: dict | None
    intent: Intent

    def body(self) -> dict:
        b: dict = {"query": self.text}
        if self.filters is not None:
            b["filters"] = self.filters
        return b


def grade(p: Product, intent: Intent) -> int:
    """0 wrong thing; 1 right kind of thing that breaks a stated constraint; 2 acceptable; 3 everything asked for."""
    if intent.target is not None:
        return 3 if p.id == intent.target else 0
    if p.category != intent.category:
        return 0
    if (
        (intent.colour is not None and p.colour != intent.colour)
        or (intent.brand is not None and p.brand != intent.brand)
        or (intent.size is not None and p.size != intent.size)
        or (intent.max_price is not None and p.price > intent.max_price)
        or (intent.in_stock and not p.in_stock)
    ):
        return 1
    return 3 if all(f in p.features for f in intent.features) else 2


def violates(p: Product, intent: Intent) -> bool:
    """True when the product is the right kind of thing but breaks a constraint the query stated."""
    return intent.target is None and grade(p, intent) == 1


@dataclass
class Shop:
    name: str
    kind: str
    products: list[Product]
    queries: list[Query] = field(default_factory=list)
    logs: list[tuple[str, str]] = field(default_factory=list)

    @cached_property
    def by_id(self) -> dict[str, Product]:
        return {p.id: p for p in self.products}

    def grades(self, q: Query) -> dict[str, int]:
        """Every product that matters to this query, with its grade."""
        if q.intent.target is not None:
            return {q.intent.target: 3}
        return {p.id: g for p in self.products if (g := grade(p, q.intent)) > 0}


def _pick(rng: np.random.Generator, items):
    items = list(items)
    return items[int(rng.integers(len(items)))]


def _title(s: str) -> str:
    return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in s.split())


class ShopMaker:
    """Builds one shop from catalogue.yaml for one seed."""

    def __init__(self, seed: int, name: str, kind: str, n_products: int):
        self.seed = seed
        self.name = name
        self.kind = kind
        self.n_products = n_products
        self.spec = settings.catalogue()["kinds"][kind]
        self.world = settings.world()
        self.cats = self.spec["categories"]

    def _sizes(self, cat: str) -> list[str]:
        return [str(s) for s in self.cats[cat].get("sizes", self.spec["sizes"])]

    def products(self) -> list[Product]:
        rng = stream(self.seed, self.name, "products")
        cfg = self.world["products"]
        cats = sorted(self.cats)
        catalogue = settings.catalogue()
        skus = rng.choice(np.arange(10000, 99999), size=self.n_products, replace=False)
        out = []
        for i in range(self.n_products):
            cat = _pick(rng, cats)
            c = self.cats[cat]
            k = int(rng.integers(cfg["features"][0], cfg["features"][1] + 1))
            feats = tuple(sorted(rng.choice(c["features"], size=min(k, len(c["features"])), replace=False)))
            term = _pick(rng, c["merchant"])
            other = _pick(rng, c["merchant"])
            brand = _pick(rng, self.spec["brands"])
            colour = _pick(rng, sorted(self.spec["colours"]))
            size = _pick(rng, self._sizes(cat))
            lo, hi = c["price"]
            price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), 2)
            lead = feats[0]
            title_colour = f"{colour} " if rng.random() < cfg["colour_in_title"] else ""
            title = _title(f"{brand} {lead} {title_colour}{term}")
            rest = ", ".join(feats[1:]) if len(feats) > 1 else lead
            use = _pick(rng, self.spec["uses"])
            material = _pick(rng, self.spec["materials"])
            filler = _pick(rng, catalogue["filler"])
            description = (
                f"A {rest} {other} for {use}. Made from {material} in {colour}. {filler.capitalize()}."
            )
            out.append(
                Product(
                    id=f"{self.name}-{i:05d}",
                    sku=f"{self.spec['sku_prefix']}-{int(skus[i])}".upper(),
                    title=title,
                    description=description,
                    brand=brand,
                    colour=colour,
                    size=size,
                    price=price,
                    in_stock=bool(rng.random() < cfg["in_stock"]),
                    category=cat,
                    features=feats,
                )
            )
        return out

    # -- shoppers and agents --------------------------------------------------------------------------------

    def _intent(self, rng: np.random.Generator, products: list[Product], agent: bool, sentence: bool) -> Intent:
        q = self.world["queries"]["intent"]
        cat = _pick(rng, sorted(self.cats))
        c = self.cats[cat]
        in_cat = self._by_category(products).get(cat, [])
        colour = _pick(rng, sorted(self.spec["colours"])) if rng.random() < q["colour"] else None
        n_feat = 1 if rng.random() < q["features"] else 0
        features = tuple(sorted(rng.choice(c["features"], size=n_feat, replace=False))) if n_feat else ()
        brand = _pick(rng, self.spec["brands"]) if rng.random() < q["brand"] else None
        size = _pick(rng, self._sizes(cat)) if rng.random() < q["size"] else None
        price_p = q["max_price_agent"] if agent else (q["max_price_sentence"] if sentence else 0.0)
        max_price = None
        if rng.random() < price_p and in_cat:
            prices = np.array([p.price for p in in_cat])
            max_price = float(np.ceil(np.quantile(prices, rng.uniform(0.35, 0.75)) / 10.0) * 10.0)
        in_stock = bool(agent and rng.random() < q["in_stock_agent"])
        return Intent(cat, colour, features, brand, size, max_price, in_stock)

    def _by_category(self, products: list[Product]) -> dict[str, list[Product]]:
        key = id(products)
        if getattr(self, "_cat_key", None) != key:
            groups: dict[str, list[Product]] = {}
            for p in products:
                groups.setdefault(p.category, []).append(p)
            self._cat_key, self._cat_groups = key, groups
        return self._cat_groups

    def _colour_word(self, rng: np.random.Generator, colour: str) -> str:
        return _pick(rng, self.spec["colours"][colour])

    def _keyword(self, rng: np.random.Generator, it: Intent) -> str:
        term = _pick(rng, self.cats[it.category]["shopper"])
        words = []
        if it.brand:
            words.append(it.brand)
        if it.colour:
            words.append(self._colour_word(rng, it.colour))
        words.extend(it.features)
        words.append(term)
        if it.size and rng.random() < 0.5:
            words.append(f"size {it.size}")
        return " ".join(words)

    def _sentence(self, rng: np.random.Generator, it: Intent) -> str:
        term = _pick(rng, self.cats[it.category]["shopper"])
        use = _pick(rng, self.spec["uses"])
        feat = " ".join(it.features)
        colour = self._colour_word(rng, it.colour) if it.colour else ""
        brand = f" from {it.brand}" if it.brand else ""
        size = f" in size {it.size}" if it.size else ""
        price = ""
        if it.max_price is not None:
            p = int(it.max_price)
            price = _pick(rng, [f" under {p} euros", f" below {p} eur", f" for less than €{p}", f" up to {p} euros"])
        templates = [
            f"looking for a {colour} {feat} {term} for {use}{brand}{size}{price}",
            f"i need a {feat} {colour} {term} that works for {use}{price}{size}{brand}",
            f"which {term} would you recommend for {use}, ideally {feat} {colour}{price}{brand}",
            f"can you show me {colour} {term} options good for {use}{size}{price}",
        ]
        return " ".join(_pick(rng, templates).split())

    def _agent(self, rng: np.random.Generator, it: Intent) -> tuple[str, dict]:
        term = _pick(rng, self.cats[it.category]["shopper"])
        text = " ".join([*it.features, term])
        filters: dict = {}
        if it.colour:
            filters["colour"] = it.colour
        if it.brand:
            filters["brand"] = it.brand
        if it.size:
            filters["size"] = it.size
        if it.max_price is not None:
            filters["maxPrice"] = it.max_price
        if it.in_stock:
            filters["inStock"] = True
        return text, filters

    def queries(self, products: list[Product]) -> list[Query]:
        rng = stream(self.seed, self.name, "queries")
        cfg = self.world["queries"]
        mix = cfg["shapes"][self.kind]
        shapes, weights = zip(*sorted(mix.items()), strict=False)
        weights = np.array(weights) / sum(weights)
        out = []
        for i in range(cfg["per_tenant"]):
            shape = shapes[int(rng.choice(len(shapes), p=weights))]
            qid = f"{self.name}-q{i:04d}"
            if shape == "sku":
                p = _pick(rng, products)
                text = p.sku.lower() if rng.random() < cfg["intent"]["sku_lowercase"] else p.sku
                out.append(Query(qid, self.name, shape, text, None, Intent(target=p.id)))
                continue
            it = self._intent(rng, products, agent=shape == "agent", sentence=shape == "sentence")
            if shape == "keyword":
                out.append(Query(qid, self.name, shape, self._keyword(rng, it), None, it))
            elif shape == "sentence":
                out.append(Query(qid, self.name, shape, self._sentence(rng, it), None, it))
            else:
                text, filters = self._agent(rng, it)
                out.append(Query(qid, self.name, shape, text, filters, it))
        return out

    def logs(self, products: list[Product]) -> list[tuple[str, str]]:
        """Past sessions: what was typed and what was bought. Some purchases have nothing to do with the query."""
        rng = stream(self.seed, self.name, "logs")
        cfg = self.world["logs"]
        by_cat = self._by_category(products)
        out = []
        for _ in range(cfg["sessions_per_tenant"]):
            sentence = rng.random() < cfg["sentence_share"]
            it = self._intent(rng, products, agent=False, sentence=sentence)
            text = self._sentence(rng, it) if sentence else self._keyword(rng, it)
            if rng.random() < cfg["bought_relevant"]:
                pool = [p for p in by_cat.get(it.category, []) if grade(p, it) >= 2] or by_cat.get(it.category, [])
                if not pool:
                    continue
                bought = _pick(rng, pool)
            else:
                bought = _pick(rng, products)
            out.append((text, bought.id))
        return out

    def build(self) -> Shop:
        products = self.products()
        return Shop(self.name, self.kind, products, self.queries(products), self.logs(products))


def world(seed: int) -> list[Shop]:
    return [ShopMaker(seed, t["name"], t["kind"], t["products"]).build() for t in settings.world()["tenants"]]
