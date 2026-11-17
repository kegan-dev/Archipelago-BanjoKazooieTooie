"""The moves the two games share: one item teaches the move in both (the owner's decisions of 2026-10-31).

A shared move is Tooie's item, under Tooie's name and id: the stock Tooie world's rules and client know it so. The
combined world never adds BK's item for it, and the client gives BK the move from Tooie's item (client/items.py).
Tooie may also hand out a move with a progressive item, whose chain gives moves one per copy received
(Archipelago-BanjoTooie/worlds/banjo_tooie/Items.py:105-115); BK's rule and the client count those too.

Tooie's yaml setting randomize_bk_moves decides the moves of both games (Options.RandomizeBKMoves, since 2026-11-03):
each choice's moves are start items, which both games learn, and every other is in the pool (the combined world's
START_MOVES). BK learns a move only from its item; Tooie's own code knows some for free besides, for the choices it
has (none, the McJiggy special: Tooie's has_BK_move, Rules.py:5975-5986), which the start items match.
"""

from typing import Any, Callable, Dict, List, Mapping, Set, Tuple

from .bk.Names import itemName as bk
from .bt.Items import progressive_ability_breakdown
from .bt.Names import itemName as bt
from .bt.Options import ProgressiveEggAim, ProgressiveWaterTraining

# BK's name -> Tooie's item. The nine with the same name, and the same move under another name: Flight is Tooie's
# Flight Pad, Swim its Dive, Feathery Flap its Flutter, Turbo Talon Trot its Turbo Trainers, Wading Boots its
# Stilt Stride, Eggs its Third Person Egg Shooting (shooting eggs; the egg type, Blue Eggs, stays Tooie's), Claw
# Swipe its Ground Rat-a-tat Rap (the standing attack) and Rat-a-tat Rap its Air Rat-a-tat Rap (the jumping one).
# Shock Spring Jump stays BK's own: Tooie's spring jump, Leg Spring, is Kazooie's alone and one of Tooie's own
# moves (the owner's decision).
SHARED: Dict[str, str] = {
    bk.TALON_TROT: bt.TTROT,
    bk.BEAK_BUSTER: bt.BBUST,
    bk.WONDERWING: bt.WWING,
    bk.BEAK_BOMB: bt.BBOMB,
    bk.CLIMB: bt.CLIMB,
    bk.FLAP_FLIP: bt.FFLIP,
    bk.BEAK_BARGE: bt.BBARGE,
    bk.ROLL: bt.ROLL,
    bk.TALL_JUMP: bt.TJUMP,
    bk.FLIGHT: bt.FPAD,
    bk.SWIM: bt.DIVE,
    bk.FEATHERY_FLAP: bt.FLUTTER,
    bk.TURBO_TROT: bt.TTRAIN,
    bk.WADING_BOOTS: bt.SSTRIDE,
    bk.EGGS: bt.EGGSHOOT,
    bk.CLAW_SWIPE: bt.GRAT,
    bk.RATATAT_RAP: bt.ARAT,
}
BK_OF_TOOIE: Dict[str, str] = {tooie: bk_name for bk_name, tooie in SHARED.items()}

Chains = Mapping[str, List[str]]


def active_chains(option: Callable[[str], int]) -> Dict[str, List[str]]:
    """Tooie's progressive items the yaml turns on, each with the moves its copies give, in order. Tooie's
    item_filter then puts the progressive item in the pool for those moves (__init__.py:516-551), and its
    starting attack may be one (choose_starter_attack, __init__.py:691-735). `option` gives an option's value by
    its name: the world's options, or the slot data's for the client."""
    names = []
    if option("progressive_beak_buster"):
        names.append(bt.PBBUST)
    if option("progressive_shoes"):
        names.append(bt.PSHOES)
    if option("progressive_water_training") == ProgressiveWaterTraining.option_basic:
        names.append(bt.PSWIM)
    elif option("progressive_water_training") == ProgressiveWaterTraining.option_advanced:
        names.append(bt.PASWIM)
    if option("progressive_bash_attack"):
        names.append(bt.PBASH)
    if option("progressive_flight"):
        names.append(bt.PFLIGHT)
    if option("progressive_egg_aiming") == ProgressiveEggAim.option_basic:
        names.append(bt.PEGGAIM)
    elif option("progressive_egg_aiming") == ProgressiveEggAim.option_advanced:
        names.append(bt.PAEGGAIM)
    return {name: list(progressive_ability_breakdown[name]) for name in names}


def slot_chains(slot_data: Mapping[str, Any]) -> Dict[str, List[str]]:
    """The chains as the client reads them, from the slot data: Tooie's fill_slot_data sends every option's value
    under "options" (Archipelago-BanjoTooie/worlds/banjo_tooie/__init__.py:1113-1133)."""
    options = slot_data.get("options") or {}
    return active_chains(lambda name: options.get(name, 0))


def grants(tooie_move: str, chains: Chains) -> List[Tuple[str, int]]:
    """The items that teach a shared move, each with the copies it takes: the move's own item, or a progressive
    item with the move at that place in its chain."""
    found = [(tooie_move, 1)]
    for progressive, chain in chains.items():
        if tooie_move in chain:
            found.append((progressive, chain.index(tooie_move) + 1))
    return found


def bk_moves_known(counts: Mapping[str, int], chains: Chains) -> Set[str]:
    """The shared moves, by BK's names, that the items received teach (`counts`: item name -> copies)."""
    return {bk_name for bk_name, tooie in SHARED.items()
            if any(counts.get(item, 0) >= copies for item, copies in grants(tooie, chains))}
