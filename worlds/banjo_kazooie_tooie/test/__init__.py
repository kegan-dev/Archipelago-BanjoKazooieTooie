from collections import Counter
from typing import Any, Dict, Optional

from BaseClasses import MultiWorld
from test.bases import WorldTestBase
from test.general import setup_multiworld

from ..Names import GAME

EARLY_STEPS = ("generate_early", "create_regions", "create_items")


class CombinedTestBase(WorldTestBase):
    game = GAME


def make(options: Optional[Dict[str, Any]] = None, seed: int = 1, steps=EARLY_STEPS) -> MultiWorld:
    """A solo multiworld of the combined game through `steps`."""
    from .. import BanjoKazooieTooieWorld
    return setup_multiworld(BanjoKazooieTooieWorld, steps, seed, options or {})


def items_of(multiworld: MultiWorld, player: int = 1) -> Counter:
    """Every item of `player` by name: in the pool, from the start, and placed (locked) at a location."""
    items = [item for item in multiworld.itempool if item.player == player]
    items += multiworld.precollected_items[player]
    items += [location.item for location in multiworld.get_locations(player)
              if location.item is not None and location.item.code is not None]
    return Counter(item.name for item in items)
