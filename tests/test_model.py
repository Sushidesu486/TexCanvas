from dataclasses import FrozenInstanceError

import pytest

from texcanvas.model import Deck, Metadata


def test_models_are_immutable():
    deck = Deck(metadata=Metadata(title="Test"), sections=())
    with pytest.raises(FrozenInstanceError):
        deck.aspect = "4:3"

