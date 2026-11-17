"""Which game each trap and nest of the combined slot went to: a trap or a nest hits the game being played when it
arrives, once (the owner's decisions of 2026-11-09 for the traps and of 2026-11-11 for the nests).

The slot's traps are Tooie's five items (Archipelago-BanjoTooie/worlds/banjo_tooie/Items.py:148-152), and both games
play them: Tooie's hack the totals of each kind in pc.traps (client/game.py:685-749 of the Tooie world), BK's the
totals in its link block (worlds/banjo_kazooie/client/link.py). Its filler is Tooie's Egg Nest and Feather Nest
(Items.py:190-194), which both games apply too: Tooie's hack the totals in pc.items (client/game.py:614-617, the hack's
ap.c applies the difference from the counts it saved), BK's as refills (the items block's refills: an Egg Nest fills
the blue eggs, a Feather Nest the less full feather). Each game keeps the counts it has applied in its save. So each
game is given its share, and a share never shrinks: per kind, the items received are split between "bk" and "tooie",
and one in neither goes to the game whose half of the client asks first (BK's poll while BK plays, the stock Tooie
code's write while Tooie runs). The split is kept in the server's data storage under storage_key, so that nothing is
given twice across switches, reconnects and restarts. Golden Egg Nests are not split: they stay Tooie's.

Pure Python but for Tooie's tables of the trap and nest items.
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..bt.Items import nest_table              # Tooie's Egg Nest and Feather Nest, with their ids
from ..bt.Names import itemName as tooie_names
from ..bt.client.game import AP_TRAP_INDEX    # Tooie's trap item id -> its kind 0..4

TRAP_KINDS = 5              # kinds 0..4: the traps, in the order of AP_TRAP_INDEX and of BK's link block
EGG_NEST, FEATHER_NEST = 5, 6
KINDS = 7
GAMES = ("bk", "tooie")

# An item id -> its kind
KIND_OF: Dict[int, int] = dict(AP_TRAP_INDEX)
KIND_OF[nest_table[tooie_names.ENEST].btid] = EGG_NEST
KIND_OF[nest_table[tooie_names.FNEST].btid] = FEATHER_NEST


def storage_key(team: int, slot: int) -> str:
    return f"BanjoKazooieTooie_{team}_{slot}_traps"


def received(item_ids: Iterable[int]) -> List[int]:
    """The traps and nests received of each kind."""
    counts = [0] * KINDS
    for item_id in item_ids:
        kind = KIND_OF.get(item_id)
        if kind is not None:
            counts[kind] += 1
    return counts


def _counts(value: Any, length: int) -> Optional[List[int]]:
    if isinstance(value, list) and len(value) == length and all(isinstance(c, int) and c >= 0 for c in value):
        return list(value)
    return None


class TrapShares:
    """The traps and nests of each kind given to each game. Unknown (None from the client's view) until read from the
    server.

    Shares stored before the nests were split (the traps' five counts, 2026-11-10) or none at all leave the nests
    unknown: the first take then gives every nest received so far to Tooie, where the stock client put them all, so
    that Tooie's hack, which applies its share's difference from the count it saved (ap.c), never sees a lower total."""

    def __init__(self, stored: Optional[Dict[str, Any]] = None) -> None:
        self.given: Dict[str, List[int]] = {game: [0] * KINDS for game in GAMES}
        self.nests_known = False
        stored = stored if isinstance(stored, dict) else {}
        full = {game: _counts(stored.get(game), KINDS) for game in GAMES}
        if all(full.values()):
            self.given = full
            self.nests_known = True
            return
        for game in GAMES:
            traps = _counts(stored.get(game), TRAP_KINDS)
            if traps is not None:
                self.given[game][:TRAP_KINDS] = traps

    def to_storage(self) -> Dict[str, List[int]]:
        return {game: list(counts) for game, counts in self.given.items()}

    def take(self, game: str, counts: Sequence[int]) -> bool:
        """The traps and nests received (`counts`, by kind) that no game has yet, for `game`. True when the shares
        changed."""
        changed = False
        if not self.nests_known:
            for kind in (EGG_NEST, FEATHER_NEST):
                self.given["tooie"][kind] = counts[kind]
                self.given["bk"][kind] = 0
            self.nests_known = True
            changed = True
        for kind in range(KINDS):
            new = counts[kind] - sum(self.given[g][kind] for g in GAMES)
            if new > 0:
                self.given[game][kind] += new
                changed = True
        return changed

    def share(self, game: str) -> tuple:
        return tuple(self.given[game])

    def for_tooie(self, items: Iterable[Any]) -> List[Any]:
        """The items received as Tooie's stock code should see them: without the traps and nests that went to BK (the
        first of each kind), so that it writes Tooie's share as each kind's total."""
        skip = list(self.given["bk"])
        out = []
        for item in items:
            kind = KIND_OF.get(getattr(item, "item", None))
            if kind is not None and skip[kind] > 0:
                skip[kind] -= 1
                continue
            out.append(item)
        return out
