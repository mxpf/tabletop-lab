from tabletop_lab.engine.zones import Deck, Zone


def test_zone_add_remove_and_lengths():
    zone = Zone("table")
    zone.add("a")
    zone.extend(["b", "c"])
    assert len(zone) == 3
    assert zone.remove("b") == "b"
    assert list(zone) == ["a", "c"]


def test_deck_draws_from_top():
    deck = Deck("deck", cards=[1, 2, 3])
    assert deck.draw(2) == [3, 2]
    assert deck.cards == [1]
