"""The world doors of both games, and the shuffle of the worlds behind them across the games (the option
cross_game_world_entrances; docs/ROADMAP.md, "Entrances shuffled across the games").

Eighteen doors: Banjo-Kazooie's nine world doors in Gruntilda's Lair (worlds/banjo_kazooie/Entrances.py) and Tooie's
nine world entrances on the Isle o' Hags, Cauldron Keep's among them, as in Tooie's own loading-zone shuffle
(WorldOrder.py:139-152 of the Tooie world). A door and the world behind it in the vanilla games share a name: a BK
level's, or a key of Tooie's loading_zones, which is its world's first region in Tooie's logic. A shuffle is a mapping
door -> world, every world behind one door; a world's way out leads back to the door it is behind, in whichever game
that is, and each door keeps its own cost (a BK door its picture and podium, a Tooie entrance its world's unlock). Boss
rooms and backdoors stay where they are (the owner's decision of 2026-11-07, as in Tooie's own shuffle).

The hacks: BK's exit map (hack/bk/decomp/include/bkbt.h, BkbtApExit; an entry for Tooie since layout 0.14.0) and
Tooie's (hack/bt/shared/include/ap_memory/pc.h: exit_map, and since dual-boot contract 5 exit_game, which says that an
entry leads into BK and where Tooie saves first). Tooie's own pairs are the stock Tooie client's to write, from the slot
data's loading_zones (client/game.py, apply_zone_warps, of the Tooie world): tooie_zones gives it a mapping of Tooie's
own, and cross_exit_maps the entries the combined client writes over it (client/bridge.py).

Pure (the names and the numbers), so that the client loads it.
"""

from typing import Dict, List, Mapping, NamedTuple, Tuple

from .bk.Entrances import DOOR_OF as BK_DOOR_OF, GAME_BK, LEVELS as BK_LEVELS

GAME_TOOIE = 2      # BkbtApExit's to_game for Tooie (include/bkbt.h, BKBT_AP_GAME_TOOIE)


class TooieDoor(NamedTuple):
    name: str                   # the loading_zones key: the world's first region in Tooie's logic (Names/regionName.py)
    zone_region: str            # the Isle o' Hags region of the loading zone (regionName.MTE ... CKE)
    hag_map: int                # the Isle o' Hags map the entrance is in
    way_back: int               # the exit of hag_map the world's way out arrives at
    world_map: int              # the world's map the entrance loads
    entrance: int               # the exit of world_map the entrance asks for and arrives at
    extra_exits: Tuple[int, ...] = ()   # more exits of world_map that guards in hag_map ask for


# Tooie's nine, in loading_zones' order (WorldOrder.py:28-38). The numbers: WORLD_MAP_ENTRANCES, client/game.py:259-331
# of the Tooie world (its key, entrance_id, exit_map, exit_id), and GGM's second guard at exit 16 (apply_zone_warps,
# :486-497); the regions: Names/regionName.py:30-38 and :46-98 (the test compares them with Tooie's names).
TOOIE_DOORS: Tuple[TooieDoor, ...] = (
    TooieDoor("Mayahem Temple", "Mayahem Temple - Main Entrance", 0x14F, 2, 0x0B8, 10),
    TooieDoor("Glitter Gulch Mine", "Glitter Gulch Mine - Main Entrance", 0x152, 2, 0x0C7, 17, (16,)),
    TooieDoor("Witchyworld", "Witchyworld - Main Entrance", 0x154, 2, 0x0D6, 18),
    TooieDoor("Jolly Roger's Lagoon - Town Center", "Jolly Roger's Lagoon - Main Entrance", 0x155, 5, 0x1A7, 3),
    TooieDoor("Terrydactyland", "Terrydactyland - Main Entrance", 0x15A, 2, 0x112, 23),
    TooieDoor("Outside Grunty Industries", "Grunty Industries - Main Entrance", 0x15C, 2, 0x100, 9),
    TooieDoor("Hailfire Peaks", "Hailfire Peaks - Main Entrance", 0x155, 6, 0x127, 21),
    TooieDoor("Cloud Cuckooland", "Cloud Cuckooland - Main Entrance", 0x15A, 5, 0x136, 20),
    TooieDoor("Cauldron Keep", "Cauldron Keep - Main Entrance", 0x15C, 3, 0x15D, 1),
)
TOOIE_DOOR_OF: Dict[str, TooieDoor] = {door.name: door for door in TOOIE_DOORS}
TOOIE_LEVELS: Tuple[str, ...] = tuple(door.name for door in TOOIE_DOORS)

# All eighteen, BK's first
LEVELS: Tuple[str, ...] = BK_LEVELS + TOOIE_LEVELS

# A Tooie entry: (on_map, og_map, og_exit, to_map, to_exit, stay_exit), each into BK (exit_game's to_game 1)
TooieEntry = Tuple[int, int, int, int, int, int]
# A BK entry: (on_map, og_map, og_exit, to_game, to_map, to_exit), as worlds/banjo_kazooie/Entrances.py has them
BkEntry = Tuple[int, int, int, int, int, int]


def game_of(level: str) -> int:
    """The game a door, or a world, is in: GAME_BK or GAME_TOOIE."""
    if level in BK_DOOR_OF:
        return GAME_BK
    if level in TOOIE_DOOR_OF:
        return GAME_TOOIE
    raise KeyError(level)


def identity() -> Dict[str, str]:
    """Every door leads to its own world: the vanilla games."""
    return {level: level for level in LEVELS}


def is_permutation(world_entrances: Mapping[str, str]) -> bool:
    """Does the mapping put each of the eighteen worlds behind one of the eighteen doors?"""
    return set(world_entrances) == set(LEVELS) and sorted(world_entrances.values()) == sorted(LEVELS)


def entry_region(world: str) -> str:
    """The region a door leads into when `world` is behind it: the world's first."""
    return BK_DOOR_OF[world].entry_region if world in BK_DOOR_OF else TOOIE_DOOR_OF[world].name


def door_region(door: str) -> str:
    """The region a door is in, which the way out of the world behind it leads back to."""
    return BK_DOOR_OF[door].door_region if door in BK_DOOR_OF else TOOIE_DOOR_OF[door].zone_region


def tooie_zones(world_entrances: Mapping[str, str]) -> Dict[str, str]:
    """Tooie's loading_zones for a mapping across the games: a mapping of Tooie's own nine, which the stock client
    writes. A Tooie door whose world is BK's is paired with a Tooie world behind a BK door (there are as many of each),
    and the two entries the stock client writes for that pair are the ones cross_exit_maps writes over: the door's
    way in, and that world's way out."""
    _check(world_entrances)
    behind = {world: door for door, world in world_entrances.items()}
    to_bk = [door for door in TOOIE_LEVELS if world_entrances[door] in BK_DOOR_OF]
    from_bk = [world for world in TOOIE_LEVELS if behind[world] in BK_DOOR_OF]
    paired = dict(zip(to_bk, from_bk))
    return {door: paired.get(door, world_entrances[door]) for door in TOOIE_LEVELS}


def cross_exit_maps(world_entrances: Mapping[str, str]) -> Tuple[List[BkEntry], List[TooieEntry]]:
    """The two games' exit maps for a mapping across the games. BK's: every entry of a BK door or a BK world's way
    out that leads elsewhere (worlds/banjo_kazooie/Entrances.py, exit_map, for a BK door into a BK world). Tooie's: the
    entries into BK, which the combined client writes over the stock client's (tooie_zones): a Tooie entrance into a
    BK world (each guard of its Isle o' Hags map that asks for its world), and the way out of a Tooie world behind a BK
    door. Tooie saves first at its stay exit, the spot the way back arrives at: a door's way back on the Isle o' Hags,
    a world's entrance."""
    _check(world_entrances)
    bk: List[BkEntry] = []
    tooie: List[TooieEntry] = []
    for door, world in world_entrances.items():
        if door == world:
            continue
        if door in BK_DOOR_OF:
            d = BK_DOOR_OF[door]
            if world in BK_DOOR_OF:
                w = BK_DOOR_OF[world]
                bk.append((d.lobby, *d.entrance, GAME_BK, *w.entrance))
                bk.append((w.entrance[0], *w.way_out, GAME_BK, *d.way_out))
            else:
                t = TOOIE_DOOR_OF[world]
                bk.append((d.lobby, *d.entrance, GAME_TOOIE, t.world_map, t.entrance))
                tooie.append((t.world_map, t.hag_map, t.way_back, *d.way_out, t.entrance))
        elif world in BK_DOOR_OF:
            t = TOOIE_DOOR_OF[door]
            w = BK_DOOR_OF[world]
            for exit in (t.entrance, *t.extra_exits):
                tooie.append((t.hag_map, t.world_map, exit, *w.entrance, t.way_back))
            bk.append((w.entrance[0], *w.way_out, GAME_TOOIE, t.hag_map, t.way_back))
    return bk, tooie


def _check(world_entrances: Mapping[str, str]) -> None:
    if not is_permutation(world_entrances):
        raise ValueError(f"not a world for each of the eighteen doors: {dict(world_entrances)}")
