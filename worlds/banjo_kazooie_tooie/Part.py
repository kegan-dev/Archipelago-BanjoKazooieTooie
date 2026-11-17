"""Banjo-Kazooie's part of the combined world: what BK's module functions (worlds/banjo_kazooie: Regions.py, Rules.py,
Pool.py) see as their world.

BkPart answers those functions' questions (Rules.py, "Lighthouse's expressions") with the combined world's names:
BK's renamed collectables, Tooie's items for the shared moves (Moves.py), the Lobby for BK's Menu and nothing for
BK's Spiral Mountain, which the hub door skips. Its options are the combined world's bk_ options under BK's names,
but for its moves, which Tooie's randomize_bk_moves decides for both games.
"""

from collections import Counter
from types import SimpleNamespace
from typing import TYPE_CHECKING, List, Optional, Set, Union

from BaseClasses import Item, ItemClassification, Location, Region

from .bk import BanjoKazooieWorld
from .bk.Entrances import identity
from .bk.Items import moves_table
from .bk.Locations import LocationData
from .bk.Rules import NoteGroup, Rule

from . import Moves
from .Names import BK_LEFT_OUT, BK_LOBBY, BK_MENU, RENAMED

if TYPE_CHECKING:
    from . import BanjoKazooieTooieWorld


def combined_name(bk_name: str) -> str:
    """A BK item's name in the combined game: Tooie's for a shared move, "Lair ..." for a renamed collectable."""
    return Moves.SHARED.get(bk_name) or RENAMED.get(bk_name, bk_name)


class BkPart:
    def __init__(self, world: "BanjoKazooieTooieWorld") -> None:
        self.world = world
        self.player = world.player
        self.multiworld = world.multiworld
        self.random = world.random
        o = world.options
        # BK's options but its moves', which randomize_bk_moves decides for both games (Options.RandomizeBKMoves);
        # BK's functions read those only in Pool.place_molehill_moves, which this part replaces (bk_place_moves)
        self.options = SimpleNamespace(
            randomize_honeycombs=o.bk_randomize_honeycombs,
            randomize_jinjos=o.bk_randomize_jinjos,
            notesanity=o.bk_notesanity,
            skip_intro=o.bk_skip_intro,
            skip_lair_cutscene=o.bk_skip_lair_cutscene,
            randomize_world_entrances=o.bk_randomize_world_entrances,
            logic_type=o.bk_logic_type,
        )
        self.chains = Moves.active_chains(lambda name: getattr(o, name).value)
        self.enabled_location_names: Set[str] = set()
        self.note_groups: List[NoteGroup] = []
        self.client_seed = 0
        self.world_entrances = identity()       # door -> the world behind it (BanjoKazooieTooieWorld.connect_entrances)
        self.world_doors: dict = {}             # the doors' connections (worlds/banjo_kazooie/Regions.py)
        self.entrance_draws = 0

    # -- what BK's functions ask --------------------------------------------------------------------------

    def location_enabled(self, name: str, data: LocationData) -> bool:
        return BanjoKazooieWorld.location_enabled(self, name, data)  # BK's own rule, with these options

    def bk_item(self, name: str) -> str:
        return combined_name(name)

    def bk_region(self, name: str) -> Optional[str]:
        if name == BK_MENU:
            return BK_LOBBY
        if name == BK_LEFT_OUT:
            return None
        return name

    def bk_move(self, move: str) -> Union[str, Rule]:
        tooie = Moves.SHARED.get(move)
        if tooie is None:
            return move
        found = Moves.grants(tooie, self.chains)
        if len(found) == 1:
            return tooie
        player = self.player
        return lambda state: any(state.has(item, player, copies) for item, copies in found)

    def bk_location(self, name: str, address: Optional[int], region: Region) -> Location:
        return self.world.new_location(name, address, region)

    def bk_event_item(self, event: str) -> Item:
        return self.world.create_event_item(event)

    def get_region(self, name: str) -> Region:
        return self.world.get_region(name)

    def get_location(self, name: str) -> Location:
        return self.world.get_location(name)

    def create_item(self, bk_name: str, classification: Optional[ItemClassification] = None) -> Item:
        """A BK item, by BK's name."""
        item = self.world.create_item(combined_name(bk_name))
        if classification is not None and bk_name not in Moves.SHARED:
            item.classification = classification
        return item

    # -- the moves ----------------------------------------------------------------------------------------

    def bk_place_moves(self, pool: List[Item]) -> None:
        """BK's moves, each exactly once. A move the slot already has stays where it is: a start item (the choice of
        randomize_bk_moves, BanjoKazooieTooieWorld._start_with_bk_moves) or, for a shared move, Tooie's item or a
        progressive item's copy in Tooie's pool. Any other move gets its item here, in the pool: BK's molehills are
        checks like any other place (the owner's decision of 2026-11-03, with the moves' one setting)."""
        multiworld, player = self.multiworld, self.player
        have = Counter(item.name for item in multiworld.precollected_items[player])
        have += Counter(item.name for item in multiworld.itempool if item.player == player)
        for move in moves_table:
            tooie = Moves.SHARED.get(move)
            found = Moves.grants(tooie, self.chains) if tooie is not None else [(move, 1)]
            if not any(have[item] >= copies for item, copies in found):
                pool.append(self.create_item(move))
