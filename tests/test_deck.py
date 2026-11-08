from blackjack.cards import full_deck
from blackjack.deck import shuffled_deck


def test_same_secret_and_game_give_same_deck():
    assert shuffled_deck("s3cret", 7) == shuffled_deck("s3cret", 7)


def test_different_game_or_secret_changes_deck():
    base = shuffled_deck("s3cret", 7)
    assert shuffled_deck("s3cret", 8) != base
    assert shuffled_deck("other", 7) != base


def test_deck_is_a_permutation_and_shuffled():
    deck = shuffled_deck("s3cret", 1)
    assert sorted(deck) == sorted(full_deck())
    assert deck != full_deck()
