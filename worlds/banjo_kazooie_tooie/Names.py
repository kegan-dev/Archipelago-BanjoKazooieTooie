"""Names of the combined world "Banjo-Kazooie & Tooie": the game, the BK items renamed beside Tooie's, the Tooie
locations the hub door leaves out, and the hub's entrances (docs/ROADMAP.md, "The way there", step 2)."""

from .bk.Names import itemName as bk_item, regionName as bk_region
from .bt.Names import locationName as bt_location, regionName as bt_region

GAME = "Banjo-Kazooie & Tooie"

# BK's collectables that share their name with Tooie's (the owner's choice of 2026-10-31: separate items, BK's
# called "Lair ..."). Tooie's keep their names: the stock Tooie world's rules ask for them by name.
RENAMED = {
    bk_item.JIGGY: "Lair Jiggy",
    bk_item.EMPTY_HONEYCOMB: "Lair Empty Honeycomb",
    bk_item.MUMBO_TOKEN: "Lair Mumbo Token",
}

# Tooie's locations in the ruined Lair, which the hub door replaces (the owner's decision of 2026-10-15: the
# ruined Lair is left out and Cheato moves): the seven nests there (Archipelago-BanjoTooie/worlds/banjo_tooie/
# Regions.py:624-632).
RUINED_LAIR = (
    bt_location.NESTSM1, bt_location.NESTSM2, bt_location.NESTSM3, bt_location.NESTSM4, bt_location.NESTSM5,
    bt_location.NESTSM6, bt_location.NESTSM7,
)

# Cheato's five rewards, in the ruined Lair in Tooie (Regions.py:22-28), are given in King Jingaling's zombified
# throne room here (the owner's decision of 2026-11-14; Tooie map 0x19B, the one the palace's door in Jinjo Village
# leads to): the Tooie hack spawns Cheato there with the combined client's hub_door setting
# (hack/bt/n64/src/cheato.c). Tooie's logic has the throne room in "Isle O Hags - Jinjo Village", where "IoH: King
# Jingaling Jiggy" is too (Regions.py:29-39; it defines "Isle O Hags - King Jingaling Palace" and gives it nothing),
# and Tooie's rules for the rewards count Cheato Pages only (Rules.py:5972-5973, :6480-6493). The locations keep Tooie's names ("SM: Cheato Reward 1", ...) and ids,
# which the stock client sends from the hack's flags.
CHEATO_REWARDS = (bt_location.CHEATOR1, bt_location.CHEATOR2, bt_location.CHEATOR3, bt_location.CHEATOR4,
                  bt_location.CHEATOR5)
CHEATO_HOME = bt_region.IOHJV

# The hub door: Tooie's "Spiral Mountain - Gruntilda's Lair" (reached by Tooie's own rule, SM_to_GL) leads into
# BK's Lair, whose exit leads back to Tooie's Spiral Mountain. BK's Spiral Mountain is left out, and its Menu's
# locations (the note doors' thresholds) go to the Lobby.
TOOIE_HUB = bt_region.SMGL
TOOIE_SM = bt_region.SM
BK_LOBBY = bk_region.GL
HUB_IN = "Hub Door: Into Gruntilda's Lair"
HUB_OUT = "Hub Door: Out to Spiral Mountain"
BK_LEFT_OUT = bk_region.SM
BK_MENU = bk_region.MENU
