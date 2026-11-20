"""The term model: one tokenizer rule, learned synonyms, nothing from other tenants."""

import json

from tfs.learn.terms import Tokenizer, cosine, train
from tfs.settings import ROOT


def test_python_tokenizer_matches_the_shared_fixture():
    tok = Tokenizer()
    for case in json.loads((ROOT / "tests/fixtures/tokenize.json").read_text()):
        assert tok(case["text"]) == case["tokens"], case["text"]


def _model(shops, name):
    s = next(s for s in shops if s.name == name)
    return train(s.name, [p.feed() for p in s.products], s.logs)


def test_shopper_words_land_next_to_merchant_words(shops):
    m = _model(shops, "outdoor")
    assert cosine(m, "raincoat", "hardshell") > 0.6
    assert cosine(m, "rucksack", "daypack") > 0.6
    assert cosine(m, "raincoat", "tent") < 0.3


def test_a_model_knows_only_its_own_tenants_words(shops):
    outdoor = _model(shops, "outdoor")
    assert "couch" not in outdoor["terms"] and "skillet" not in outdoor["terms"]


def test_vectors_are_unit_length_and_numbers_are_dropped(shops):
    m = _model(shops, "home")
    assert m["dim"] == len(next(iter(m["terms"].values())))
    assert not any(t.isdigit() for t in m["terms"])
    for v in list(m["terms"].values())[:20]:
        assert abs(sum(x * x for x in v) - 1.0) < 1e-3
