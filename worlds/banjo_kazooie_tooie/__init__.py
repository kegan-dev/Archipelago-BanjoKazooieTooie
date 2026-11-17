"""Banjo-Kazooie & Tooie: both games in one Archipelago slot, played in the dual-boot image (hack/DUALBOOT.md) with one
client (docs/ROADMAP.md, "The way there", step 2).

The world is the stock Tooie world V4.13.1 (Archipelago-BanjoTooie/worlds/banjo_tooie) with Banjo-Kazooie's world
(worlds/banjo_kazooie) layered in through Part.BkPart, both carried inside this one as its subpackages bt and bk
(carried.py), so that its apworld installs alone; joined by the hub door: Tooie's
Spiral Mountain - Gruntilda's Lair leads into BK's Lair, whose exit leads back to Tooie's Spiral Mountain. BK's
Spiral Mountain is not in the slot, nor the ruined Lair that the door replaces (Names.RUINED_LAIR): Cheato gives his
rewards in King Jingaling's zombified throne room instead (Names.CHEATO_HOME). Moves the games share are one item,
Tooie's (Moves.py); BK's collectables that share Tooie's names are "Lair ..." (Names.RENAMED).

Tooie's own steps run first and unchanged wherever they can, so that Tooie's half of a slot is what a standalone
Tooie world makes of the same seed and options; the overrides below say what each changes and why. With the option
cross_game_world_entrances the world doors of both games are shuffled together (Entrances.py).
"""

import logging
from collections import Counter
from random import Random
from typing import Any, ClassVar, Dict, Optional, Set, TextIO, Tuple

import settings
from BaseClasses import CollectionState, Entrance, Item, ItemClassification, Location, Region, Tutorial
from Options import OptionError
from worlds.AutoWorld import WebWorld
from worlds.LauncherComponents import Component, Type, components, launch

from .bk import Regions as BKRegions, Rules as BKRules, slot_data as bk_slot_data
from .bk.Entrances import identity as bk_identity, is_permutation as bk_is_permutation
from .bk.Items import (ItemData, SM_TUTORIAL_MOVES, all_item_table as bk_item_table, filler_table,
                                        moves_table, trap_table as bk_trap_table)
from .bk.Locations import all_location_table as bk_location_table
from .bk.LogicData import GOAL_EVENT as BK_GOAL_EVENT
from .bk.Names import itemName as bk_item
from .bk.Pool import create_pool
from .bt import BanjoTooieWorld
from .bt.Hints import Hint
from .bt.Items import BanjoTooieItem
from .bt.Locations import (BanjoTooieLocation, CCLoc_table, CKLoc_table, GILoc_table, GMLoc_table,
                                          HPLoc_table, JRLoc_table, MTLoc_Table, TLLoc_table, WWLoc_table)
from .bt.Names import itemName as bt_item, regionName as bt_region
from .bt.Options import HintClarity
from .bt.Rules import BanjoTooieRules, BanjoTooieUniversalTrackerRules

from . import Entrances as Doors, Moves
from .Names import BK_LOBBY, CHEATO_HOME, CHEATO_REWARDS, GAME, HUB_IN, HUB_OUT, RENAMED, RUINED_LAIR, TOOIE_HUB, \
    TOOIE_SM
from .Options import BanjoKazooieTooieOptions, Goal, RandomizeBKMoves, option_groups
from .Part import BkPart, combined_name
from .Presets import options_presets

# The moves each choice of randomize_bk_moves starts with, in both games, by BK's names (Options.RandomizeBKMoves).
# Flight Pad, or Flap Flip and Climb, open Tooie's way from Spiral Mountain to Gruntilda's Lair, the hub door (Tooie's
# SM_to_GL, Rules.py:3406-3412)
START_MOVES = {
    RandomizeBKMoves.option_none: tuple(moves_table),
    RandomizeBKMoves.option_mcjiggy_special: (bk_item.TALON_TROT, bk_item.TALL_JUMP),
    RandomizeBKMoves.option_all: (),
    RandomizeBKMoves.option_mcjiggy_special_flight_pad: (bk_item.TALON_TROT, bk_item.TALL_JUMP, bk_item.FLIGHT),
    RandomizeBKMoves.option_spiral_mountain: tuple(SM_TUTORIAL_MOVES),
}
# What Tooie's half plays the combined world's own choices as: a choice of Tooie's own, which its world has every
# code path for (its pool, rules, world order and client). The McJiggy special knows Talon Trot and Tall Jump for
# free, as the Flight Pad choice starts with them; Spiral Mountain's start knows none for free, as All
TOOIE_PLAYS = {
    RandomizeBKMoves.option_mcjiggy_special_flight_pad: RandomizeBKMoves.option_mcjiggy_special,
    RandomizeBKMoves.option_spiral_mountain: RandomizeBKMoves.option_all,
}
# How many mappings of the eighteen doors connect_entrances tries before it gives up (cross_game_world_entrances)
CROSS_DRAWS = 500
# Tooie's locations by the world they are in, for the hints (extend_hint_information, as Tooie's own: __init__.py:1142-1178)
TOOIE_WORLD_LOCATIONS = {
    bt_region.MT: MTLoc_Table, bt_region.GM: GMLoc_table, bt_region.WW: WWLoc_table, bt_region.JR: JRLoc_table,
    bt_region.TL: TLLoc_table, bt_region.GIO: GILoc_table, bt_region.HP: HPLoc_table, bt_region.CC: CCLoc_table,
    bt_region.CK: CKLoc_table,
}


def run_client(*args: str) -> None:
    from .BKBTClient import main  # lazy, so that generating needs nothing the client needs
    launch(main, name="Banjo-Kazooie & Tooie Client", args=args)


components.append(Component("Banjo-Kazooie & Tooie Client", func=run_client, component_type=Type.CLIENT,
                            game_name=GAME, supports_uri=True,
                            description="Connects an Archipelago server to the dual-boot image of Banjo-Kazooie "
                                        "and Banjo-Tooie in an emulator."))


class BanjoKazooieTooieItem(BanjoTooieItem):
    game = GAME


class BanjoKazooieTooieLocation(BanjoTooieLocation):
    game = GAME


# BK's items in the combined game, by their names there: every BK item but the shared moves, which are Tooie's, and
# the traps: Tooie's five play in whichever game runs (BKBTClient.py), and BK's have the same names.
BK_ITEMS: Dict[str, ItemData] = {combined_name(name): data for name, data in bk_item_table.items()
                                 if name not in Moves.SHARED and name not in bk_trap_table}


def _without_ruined_lair(rules: BanjoTooieRules) -> None:
    """Drop the ruined Lair's locations from every rule table of Tooie's rules: Tooie's set_rules looks each up by
    name (Rules.py:581-583 the Lair's nests), and they are not in this world."""
    for key, value in list(vars(rules).items()):
        if isinstance(value, dict) and any(name in value for name in RUINED_LAIR):
            setattr(rules, key, {name: rule for name, rule in value.items() if name not in RUINED_LAIR})


class _CombinedTooieRules(BanjoTooieRules):
    def __init__(self, world) -> None:
        super().__init__(world)
        _without_ruined_lair(self)


class _CombinedTrackerRules(BanjoTooieUniversalTrackerRules):
    def __init__(self, world) -> None:
        super().__init__(world)
        _without_ruined_lair(self)


class BanjoKazooieTooieSettings(settings.Group):
    """The client makes the dual-boot image it plays from your own Banjo-Kazooie and Banjo-Tooie ROMs
    (worlds/banjo_kazooie/client/rom.py): these say where they are, where the image goes and what to start it in."""

    class BKRomPath(settings.OptionalUserFilePath):
        """File path of the Banjo-Kazooie (USA) ROM, version 1.0. Blank: the Banjo-Kazooie world's rom_path, if it is
        installed."""

    class TooieRomPath(settings.OptionalUserFilePath):
        """File path of the Banjo-Tooie (USA) ROM. Blank: the Banjo-Tooie world's rom_path, if it is installed."""

    class PatchPath(settings.OptionalUserFolderPath):
        """Folder path of where to save the dual-boot image."""

    class ProgramPath(settings.OptionalUserFilePath):
        """
        File path of the program to automatically run (your emulator).
        Leave blank to disable.
        """

    class ProgramArgs(str):
        """
        Arguments to pass to the automatically run program.
        Leave blank to disable.
        """

    bk_rom_path: BKRomPath | str = ""
    tooie_rom_path: TooieRomPath | str = ""
    patch_path: PatchPath | str = ""
    program_path: ProgramPath | str = ""
    program_args: ProgramArgs | str = ""


class BanjoKazooieTooieWeb(WebWorld):
    theme = "jungle"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Banjo-Kazooie & Tooie for Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Kegan McIlwaine"],
    )]
    option_groups = option_groups
    options_presets = options_presets


class BanjoKazooieTooieWorld(BanjoTooieWorld):
    """
    Banjo-Kazooie and Banjo-Tooie in one slot: one cartridge image with both games, where the entrance to
    Gruntilda's Lair in Tooie's Spiral Mountain leads into Banjo-Kazooie's Lair, and Bottles' and Jamjars' moves
    are learned in both games at once.
    """

    game = GAME
    web = BanjoKazooieTooieWeb()
    topology_present = True
    settings: ClassVar[BanjoKazooieTooieSettings]

    options_dataclass = BanjoKazooieTooieOptions
    options: BanjoKazooieTooieOptions

    item_name_to_id: ClassVar[Dict[str, int]] = {
        **BanjoTooieWorld.item_name_to_id, **{name: data.bkid for name, data in BK_ITEMS.items()}}
    location_name_to_id: ClassVar[Dict[str, int]] = {
        **{name: code for name, code in BanjoTooieWorld.location_name_to_id.items() if name not in RUINED_LAIR},
        **{name: data.bkid for name, data in bk_location_table.items()}}
    item_name_groups: ClassVar[Dict[str, Set[str]]] = {
        # Tooie's own groups unchanged: its prefills place their items by them (__init__.py:762-787)
        **{group: set(names) for group, names in BanjoTooieWorld.item_name_groups.items() if group != "Everything"},
        "Shared Moves": set(Moves.SHARED.values()),
        "Banjo-Kazooie Moves": {combined_name(move) for move in moves_table},
        "Lair Collectables": set(RENAMED.values()) | {bk_item.NOTE},
        "Note Doors": set(bk_item.NOTE_DOORS),
        "Banjo-Kazooie Jinjos": set(bk_item.JINJOS),
        "Banjo-Kazooie Filler": set(filler_table),
    }
    location_name_groups: ClassVar[Dict[str, Set[str]]] = {
        **{group: set(names) - set(RUINED_LAIR) for group, names in BanjoTooieWorld.location_name_groups.items()
           if group != "Everywhere" and set(names) - set(RUINED_LAIR)},
        "Banjo-Kazooie": set(bk_location_table),
    }

    def __init__(self, multiworld, player) -> None:
        super().__init__(multiworld, player)
        self.bk: Optional[BkPart] = None
        self.bk_moves_choice = RandomizeBKMoves.default
        self.cross_entrances: Optional[Dict[str, str]] = None   # door -> world across the games (Entrances.py)
        self.cross_doors: Dict[Tuple[str, str], Entrance] = {}  # their 36 connections (_find_cross_doors)
        self.cross_draws = 0

    # -- generation steps ---------------------------------------------------------------------------------

    def generate_early(self) -> None:
        # randomize_bk_moves: the world keeps the choice, and Tooie's half plays it as TOOIE_PLAYS says; create_items
        # gives the choice's moves as start items, and pre_output puts the choice back. Taken again after Tooie's
        # step when it took the options of the slot data, for the Universal Tracker (__init__.py:561-577).
        self._take_bk_moves_choice()
        self._take_cross_choice()       # before Tooie's draws, which its own shuffle's option changes
        super().generate_early()        # Tooie's validation, starting egg and attack, world order (__init__.py:561-584)
        passthrough = getattr(self.multiworld, "re_gen_passthrough", {})
        if self.game in passthrough:
            self._take_bk_moves_choice()
        self.bk = BkPart(self)
        if self.game in passthrough:
            # the Universal Tracker: BK's doors as the slot has them (connect_regions makes them so, and
            # connect_entrances draws nothing), and the doors across the games (connect_entrances points them)
            doors = (passthrough[self.game].get("bk") or {}).get("world_entrances")
            if doors and bk_is_permutation(doors):
                self.bk.world_entrances = dict(doors)
            cross = passthrough[self.game].get("cross_world_entrances")
            if cross and Doors.is_permutation(cross):
                self.cross_entrances = dict(cross)

    def _take_cross_choice(self) -> None:
        """cross_game_world_entrances shuffles the world doors of both games: each game's own shuffle is off with it,
        for the draws, the logic and what the slot data says (Options.CrossGameWorldEntrances)."""
        if not self.options.cross_game_world_entrances:
            return
        for option in (self.options.randomize_world_entrance_loading_zones, self.options.bk_randomize_world_entrances):
            if option.value:
                logging.info(f"{self.player_name}: {option.display_name} is off: World Entrances Across the Games "
                             f"shuffles both games' world entrances")
                option.value = 0

    def _take_bk_moves_choice(self) -> None:
        option = self.options.randomize_bk_moves
        self.bk_moves_choice = option.value
        option.value = TOOIE_PLAYS.get(option.value, option.value)

    def create_regions(self) -> None:
        super().create_regions()        # Tooie's regions, connections and prefills
        for location in self.multiworld.get_locations(self.player):
            location.__class__ = BanjoKazooieTooieLocation
        # Cheato's rewards: from the ruined Lair, where Tooie's create_regions puts them, to the throne room
        home = self.get_region(CHEATO_HOME)
        for name in CHEATO_REWARDS:
            location = self.get_location(name)
            location.parent_region.locations.remove(location)
            location.parent_region = home
            home.locations.append(location)
        BKRegions.create_region_shells(self.bk)
        BKRegions.create_events(self.bk)
        BKRegions.connect_regions(self.bk)
        # The hub door. The Lobby's way out is there for the player; the logic never needs it, every BK region
        # being reached through the Lobby.
        self.get_region(TOOIE_HUB).connect(self.get_region(BK_LOBBY), HUB_IN)
        self.get_region(BK_LOBBY).connect(self.get_region(TOOIE_SM), HUB_OUT)
        # Tooie's way from Mayahem Temple into its Kickball Stadium asks whether the Jade Snake Grove is reached
        # (MT_to_KS and humbaMT, Rules.py:5151-5155, 6246-6247), and Tooie's world registers no indirect condition
        # for it (Regions.py:2252-2280): AP's test_explicit_indirect_conditions_spheres failed now and then on the
        # Kickball jiggy, the standalone Tooie world's too (2026-11-03). Upstream's; registered here for this world.
        to_ks = next(e for e in self.get_region(bt_region.MT).exits if e.connected_region.name == bt_region.MTKS)
        self.multiworld.register_indirect_condition(self.get_region(bt_region.MTJSG), to_ks)

    def connect_entrances(self) -> None:
        super().connect_entrances()
        tracker = self.game in getattr(self.multiworld, "re_gen_passthrough", {})
        if self.options.cross_game_world_entrances:
            self._find_cross_doors()
            if not tracker:
                self.cross_draws = self._draw_cross(Random(f"cross-world-entrances-{self.multiworld.seed}-{self.player}"))
            elif self.cross_entrances is not None:
                self._apply_cross(self.cross_entrances)
            return
        # BK's doors, drawn as the BK world draws them (worlds/banjo_kazooie/Regions.py, draw_world_entrances), with a
        # stream of their own: the world's would leave Tooie's half other than a standalone Tooie's.
        if self.bk.options.randomize_world_entrances and not tracker:
            rng = Random(f"bk-world-entrances-{self.multiworld.seed}-{self.player}")
            self.bk.entrance_draws = BKRegions.draw_world_entrances(self.bk, rng)

    # -- the doors across the games (Entrances.py) --------------------------------------------------------

    def _find_cross_doors(self) -> None:
        """The 36 connections the shuffle across the games points, by (name, "door") for a door's way into the world
        behind it and (name, "out") for a world's way out to the door it is behind. BK's are BK's connect_regions'
        (world_doors); Tooie's its Regions.py's (:2143-2167): a loading zone's into the world loading_zones puts
        behind it, and that world's way back to the zone."""
        doors = {key: entrance for key, entrance in self.bk.world_doors.items()}
        behind = {world: door for door, world in self.loading_zones.items() if door in Doors.TOOIE_DOOR_OF}
        for door in Doors.TOOIE_DOORS:
            zone = self.get_region(door.zone_region)
            doors[(door.name, "door")] = next(e for e in zone.exits
                                              if e.connected_region.name == self.loading_zones[door.name])
            front = Doors.TOOIE_DOOR_OF[behind[door.name]].zone_region
            doors[(door.name, "out")] = next(e for e in self.get_region(door.name).exits
                                             if e.connected_region.name == front)
        self.cross_doors = doors

    def _apply_cross(self, mapping: Dict[str, str]) -> None:
        """Point the 36 connections as `mapping` (door -> the world behind it) says. The rules stay the doors' own:
        a Lair door's picture and podium, a Tooie entrance's unlock, which are on the connections into the doors'
        regions or on the doors' own (Tooie's way into a world has none: Regions.py:2153)."""
        behind = {world: door for door, world in mapping.items()}
        for level in Doors.LEVELS:
            self._repoint(self.cross_doors[(level, "door")], Doors.entry_region(mapping[level]))
            self._repoint(self.cross_doors[(level, "out")], Doors.door_region(behind[level]))
        self.cross_entrances = dict(mapping)
        # Tooie's half of it for the stock client, which writes Tooie's own pairs; the client writes the doors into
        # BK over them (Entrances.tooie_zones, cross_exit_maps)
        self.loading_zones.update(Doors.tooie_zones(mapping))
        state = getattr(self.multiworld, "state", None)
        if state is not None:
            state.stale[self.player] = True     # its regions reached were worked out with the old doors

    def _repoint(self, entrance: Entrance, to: str) -> None:
        region = self.get_region(self.bk.bk_region(to))
        if entrance.connected_region is region:
            return
        entrance.connected_region.entrances.remove(entrance)
        entrance.connect(region)

    def _draw_cross(self, rng: Random) -> int:
        """A mapping of the eighteen doors drawn with `rng` until every one of the player's locations is reached
        with all of the player's items, as BK's own shuffle draws (worlds/banjo_kazooie/Regions.py,
        draw_world_entrances), and applied. The draws taken; OptionError after CROSS_DRAWS."""
        multiworld, player = self.multiworld, self.player
        pool = [item for item in multiworld.itempool if item.player == player]
        locations = multiworld.get_locations(player)
        for draw in range(1, CROSS_DRAWS + 1):
            worlds = list(Doors.LEVELS)
            rng.shuffle(worlds)
            self._apply_cross(dict(zip(Doors.LEVELS, worlds)))
            state = CollectionState(multiworld)
            for item in pool:
                state.collect(item, True)
            state.sweep_for_advancements(locations)
            if all(location.can_reach(state) for location in locations):
                return draw
        self._apply_cross(Doors.identity())
        raise OptionError(f"{self.player_name}: no order of the world doors of both games reached every place in "
                          f"{CROSS_DRAWS} draws")

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        super().write_spoiler(spoiler_handle)
        if self.cross_entrances is not None:
            spoiler_handle.write(f"\n\nWorld doors of both games ({self.multiworld.player_name[self.player]}):\n")
            for door, world in self.cross_entrances.items():
                spoiler_handle.write(f"    {_door_label(door)} -> {world}\n")
        elif self.bk.world_entrances != bk_identity():
            spoiler_handle.write(f"\n\nBanjo-Kazooie world doors ({self.multiworld.player_name[self.player]}):\n")
            for door, world in self.bk.world_entrances.items():
                spoiler_handle.write(f"    {door} door -> {world}\n")

    @classmethod
    def stage_write_spoiler(cls, multiworld, spoiler_handle) -> None:
        # Tooie's lists its loading zones (__init__.py:1013-1026): with the doors across the games, each Tooie
        # entrance with the world really behind it, which may be BK's, not the pair of Tooie's own the stock client
        # writes (Entrances.tooie_zones)
        kept = {}
        for player in multiworld.get_game_players(cls.game):
            world = multiworld.worlds[player]
            if world.cross_entrances is not None:
                kept[player] = world.loading_zones
                world.loading_zones = {**world.loading_zones,
                                       **{door: world.cross_entrances[door] for door in Doors.TOOIE_LEVELS}}
        try:
            super().stage_write_spoiler(multiworld, spoiler_handle)
        finally:
            for player, zones in kept.items():
                multiworld.worlds[player].loading_zones = zones

    def extend_hint_information(self, hint_data: Dict[int, Dict[int, str]]) -> None:
        super().extend_hint_information(hint_data)
        if self.cross_entrances is None:
            return
        # A place in a world behind another door is hinted with that door, as Tooie hints its own shuffle's
        hints = hint_data.setdefault(self.player, {})
        behind = {world: door for door, world in self.cross_entrances.items()}
        for world, table in TOOIE_WORLD_LOCATIONS.items():
            if behind[world] != world:
                for data in table.values():
                    hints[data.btid] = _door_label(behind[world])
        for location in self.multiworld.get_locations(self.player):
            if location.address is None or location.name not in bk_location_table:
                continue
            level = bk_location_table[location.name].region.split(":")[0]
            if level in BK_LEVELS_SET and behind[level] != level:
                hints[location.address] = _door_label(behind[level])

    def create_items(self) -> None:
        # Tooie's half first, while only Tooie's locations exist: it pads its pool with its filler to the locations
        # it sees (__init__.py:408-415), as a standalone Tooie would. BK's locations only then, and BK's pool.
        super().create_items()
        self._start_with_bk_moves()
        BKRegions.create_locations(self.bk)
        pool = create_pool(self.bk)     # BK's half then finds those held (Part.BkPart.bk_place_moves)
        mine = [item for item in self.multiworld.itempool if item.player == self.player]
        missing = len(self.multiworld.get_unfilled_locations(self.player)) - len(mine) - len(pool)
        if missing < 0:
            # BK's half brings more items than places (Spiral Mountain's moves stay items, their molehills gone):
            # they take the places of filler Tooie's half padded its pool with, the last first.
            filler = [item for item in mine if item.classification == ItemClassification.filler]
            if len(filler) < -missing:
                raise OptionError(f"{self.player_name}: {-missing - len(filler)} more items than locations.")
            for item in filler[missing:]:
                self.multiworld.itempool.remove(item)
            missing = 0
        pool.extend(self.create_filler() for _ in range(missing))
        self.multiworld.itempool += pool

    def _start_with_bk_moves(self) -> None:
        """The moves the choice of randomize_bk_moves starts with (START_MOVES), as start items, so that both games
        know them: BK learns a move only from its item (Moves.py). A shared move is taken from Tooie's pool, its own
        item or a progressive item whose first copy teaches it (each of these moves is a chain's first, if in one),
        or made here where Tooie's half knows it for free and left it out (None, the McJiggy special:
        __init__.py:446-454 of Tooie's world); Shock Spring Jump is BK's own item. A move already held stays so:
        Tooie's starting attack (choose_starter_attack, __init__.py:691-735) may be one."""
        pool = self.multiworld.itempool
        held = Counter(item.name for item in self.multiworld.precollected_items[self.player])
        for move in START_MOVES[self.bk_moves_choice]:
            tooie = Moves.SHARED.get(move)
            grants = Moves.grants(tooie, self.bk.chains) if tooie is not None else [(move, 1)]
            if any(held[name] >= copies for name, copies in grants):
                continue
            found = next((item for name, copies in grants if copies == 1
                          for item in pool if item.player == self.player and item.name == name), None)
            if found is not None:
                pool.remove(found)
                self.multiworld.push_precollected(found)
            else:
                self.multiworld.push_precollected(self.bk.create_item(move))

    def set_rules(self) -> None:
        rules = (_CombinedTrackerRules if hasattr(self.multiworld, "generation_is_fake") else _CombinedTooieRules)(self)
        rules.set_rules()
        tooie_goal = self.multiworld.completion_condition[self.player]
        BKRules.set_location_rules(self.bk)
        player = self.player
        goal = self.options.goal.value
        if goal == Goal.option_tooie:
            completion = tooie_goal
        elif goal == Goal.option_banjo_kazooie:
            completion = lambda state: state.has(BK_GOAL_EVENT, player)
        else:
            completion = lambda state: tooie_goal(state) and state.has(BK_GOAL_EVENT, player)
        self.multiworld.completion_condition[player] = completion

    # -- items and locations ------------------------------------------------------------------------------

    def create_item(self, name: str) -> Item:
        data = BK_ITEMS.get(name)
        if data is not None:
            return BanjoKazooieTooieItem(name, data.classification, data.bkid, self.player)
        item = super().create_item(name)    # Tooie's, with Tooie's classification and pool counters
        return BanjoKazooieTooieItem(item.name, item.classification, item.code, item.player)

    def create_event_item(self, name: str) -> Item:
        return BanjoKazooieTooieItem(name, ItemClassification.progression, None, self.player)

    def new_location(self, name: str, address: Optional[int], region: Region) -> Location:
        return BanjoKazooieTooieLocation(self.player, name, address, region)

    def banjo_pre_fills(self, itemNameOrGroup: str, group: Optional[str], useGroup: bool) -> None:
        """Tooie's prefills (__init__.py:940-956) for this world's table: a group's items go to their places if
        this world has them (all of Tooie's but the ruined Lair's), and a kind of item to its places among Tooie's own
        locations, which the original reads from the whole table and so would look BK's locations up in Tooie's
        groups. It still makes one item per Tooie location, as the original does, since Tooie counts them."""
        from .bt.Items import all_item_table as bt_item_table
        if useGroup:
            for name in self.item_name_groups.get(itemNameOrGroup, ()):
                item = self.create_item(name)
                place = bt_item_table[name].default_location
                if place in self.location_name_to_id:
                    self.get_location(place).place_locked_item(item)
        else:
            for name in BanjoTooieWorld.location_name_to_id:
                item = self.create_item(itemNameOrGroup)
                if BanjoTooieWorld.location_name_to_group.get(name) == group and name in self.location_name_to_id:
                    self.get_location(name).place_locked_item(item)

    def post_fill(self) -> None:
        # Tooie's turns its useful jiggies, notes and doubloons back into progression once placed, behind a flag
        # on its class that every Tooie world of the multiworld shares (__init__.py:1045-1052): do it for ours.
        for location in self.multiworld.get_locations():
            item = location.item
            if item is not None and item.player == self.player and item.game == self.game \
                    and item.name in (bt_item.NOTE, bt_item.DOUBLOON, bt_item.JIGGY):
                item.classification = ItemClassification.progression

    def pre_output(self) -> None:
        # The choice of randomize_bk_moves back, for the slot data (the stock client gives free moves only for none
        # and the McJiggy special, client/game.py:236-239, and every choice's moves come as start items) and the
        # spoiler. Here, before the output's threads: Tooie's rules answer the same for it as for what Tooie's half
        # played it as, its moves being held (Rules.py:5975-5986).
        self.options.randomize_bk_moves.value = self.bk_moves_choice
        # Tooie's cryptic hints share caches on a class that the last cryptic world of each game empties
        # (Hints.py:134-145, :268-274). With a standalone Tooie world in the same multiworld, keep them for the
        # Tooie worlds after this one, and fill them again if one before has emptied them.
        if self.options.hint_clarity.value != HintClarity.option_cryptic:
            super().pre_output()
            return
        family = [world for world in self.multiworld.worlds.values() if isinstance(world, BanjoTooieWorld)
                  and world.options.hint_clarity.value == HintClarity.option_cryptic]
        if not Hint.submitted_cryptic_hinted_locations:
            for world in family:
                Hint.submit_hinted_locations(world.hinted_locations)
        Hint.compute_item_requirement_cache(self)
        kept = (Hint.item_requirement_cache, Hint.submitted_cryptic_hinted_locations, Hint.final_state)
        super().pre_output()
        if any(world.player > self.player for world in family):
            Hint.item_requirement_cache, Hint.submitted_cryptic_hinted_locations, Hint.final_state = kept

    def fill_slot_data(self) -> Dict[str, Any]:
        data = super().fill_slot_data()
        # The stock Tooie client asserts the Tooie world's version (BTClient.py:560-564), not this world's.
        data["custom_bt_data"]["version"] = BanjoTooieWorld.world_version.as_simple_string()
        # BK's settings, as the BK world sends them (its seed drawn here, after every draw of Tooie's half)
        self.bk.client_seed = self.random.randrange(1, 1 << 32)
        data["bk"] = bk_slot_data(self.bk)
        data["goal"] = self.options.goal.value
        data["hub_door"] = 1
        if self.cross_entrances is not None:
            data["cross_world_entrances"] = dict(self.cross_entrances)     # the client's exit maps (Entrances.py)
        data["contract"] = 5    # the dual-boot contract of the image this slot plays (hack/DUALBOOT.md); for people
                                # reading the slot data, nothing checks it
        return data


BK_LEVELS_SET = set(Doors.BK_LEVELS)


def _door_label(door: str) -> str:
    """A door as the spoiler and the hints name it: a Lair door by its level, a Tooie entrance by its loading zone."""
    return f"{door} Door" if door in BK_LEVELS_SET else Doors.TOOIE_DOOR_OF[door].zone_region
