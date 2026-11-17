"""What Banjo-Kazooie's hack gets of the slot's items received: BK's own items by BK's id (under BK's names, the
renames undone), and the shared moves from Tooie's items, the moves' own or a progressive item's copies (Moves.py).
Tooie's half reads the same list and ignores BK's ids (Archipelago-BanjoTooie/.../client/game.py:743-759)."""

from collections import Counter
from typing import Iterable, Tuple

from ..bk.Items import all_item_table as bk_item_table
from ..bk.client import hack, ids
from ..bt.Items import all_item_table as bt_item_table

from .. import Moves

# BK's ids -> BK's names, for BK's items in the combined game (every one but the shared moves)
BK_NAME_OF_ID = {data.bkid: name for name, data in bk_item_table.items() if name not in Moves.SHARED}
TOOIE_NAME_OF_ID = {data.btid: name for name, data in bt_item_table.items() if data.btid is not None}


def bk_items(item_ids: Iterable[int], chains: Moves.Chains) -> Tuple[hack.Items, Counter]:
    """The hack's items for the ids received, and the BK names the hack has nothing for (the filler)."""
    names, tooie = [], Counter()
    for item_id in item_ids:
        if item_id in BK_NAME_OF_ID:
            names.append(BK_NAME_OF_ID[item_id])
        elif item_id in TOOIE_NAME_OF_ID:
            tooie[TOOIE_NAME_OF_ID[item_id]] += 1
    names.extend(sorted(Moves.bk_moves_known(tooie, chains)))
    return ids.items_of(names)
