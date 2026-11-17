"""The stock Tooie client's code, which the combined client runs while Tooie runs (BKBTClient.py).

The stock monitor task (Archipelago-BanjoTooie/worlds/banjo_tooie/BTClient.py:1358-1583) runs unchanged as a child
task, on the combined client's one emulator connection, a SharedLoader, which attaches with either game resident
and answers the Tooie anchor only while Tooie's is there (as tools/bt_dualboot_client.py does for two slots).
install() patches four of the stock code's functions where it looks them up, the module attributes:
- check_victory (client/game.py:1301): Tooie's goal is reported to the combined goal (client/goal.py) instead of
  finishing the slot (BTClient.py:1479-1482 would send the goal itself);
- write_slot_settings (client/game.py:154): Tooie's settings get the hub door's byte too, which only this client
  writes (HUB_DOOR_SETTING), and with the doors across the games (the slot data's cross_world_entrances) the exit
  map's entries into BK are written over the stock code's (write_cross_doors);
- format_item_message (client/game.py:1055): nothing without the settings pointer, which a switch can take away
  between two reads (the Green Relic's text reads it, :1149-1152);
- write_received_items (client/game.py:717): the items as `tooie_items` gives them, without the traps that went to
  BK (client/traps.py), so that Tooie is written its share of each kind; nothing until the shares are known.
And the stock task's own BTEmuLoaderClient() gives the shared connection.
"""

import logging
from typing import Any, Callable, Iterable, List, Mapping, Optional

from ..bk.client import hack
from ..bk.client.emu import load as load_emu_loader

load_emu_loader()       # before BTClient's `from emu_loader import ...`: without the package, the BK world's copy
from ..bt import BTClient
from ..bt.client import game as emu_game, state as emu_state

from .. import Entrances as Doors
from .resident import TOOIE, resident

logger = logging.getLogger("Client")

StockLoader = BTClient.BTEmuLoaderClient

# Where in Tooie's settings (from the settings pointer) the hub door's byte is: settings.hub_door, in the padding
# byte before silo_requirements, which the stock client never writes (hack/bt/shared/include/ap_memory/pc.h;
# hack/bt/n64/src/door.c asserts the offset at build time). The fork's Tooie hack takes the ruined Lair's entrance
# as the door only while it is 1.
HUB_DOOR_SETTING: Optional[int] = 0x25

# Tooie's exit map, from its pointer (client/state.py, exit_map_ptr): AP_MEMORY_EXIT_MAP_MAX entries of 14 bytes
# (hack/bt/shared/include/ap_memory/pc.h, ap_memory_pc_exit_map_t: u16 on_map, og_map, to_map; u8 og_exit, to_exit;
# u8 access_rules[6]), the stock code's EXIT_MAP_* (client/game.py:242-252), and behind them, since dual-boot contract
# 5, exit_game: a (to_game, stay_exit) pair per entry (hack/bt/n64/src/door.c asserts the offset at build time)
EXIT_MAP_MAX = 63
EXIT_MAP_ENTRY = 0x0E
ON_MAP_AT, OG_MAP_AT, TO_MAP_AT, OG_EXIT_AT, TO_EXIT_AT = 0x00, 0x02, 0x04, 0x06, 0x07
EXIT_GAME_AT = EXIT_MAP_MAX * EXIT_MAP_ENTRY    # 0x372
EXIT_GAME_BK = 1                                # AP_MEMORY_EXIT_GAME_BK


def write_cross_doors(emu, mapping: Optional[Mapping[str, str]]) -> int:
    """The doors into BK of a mapping across the games (Entrances.cross_exit_maps), written over the entries the
    stock code wrote for the slot data's loading_zones (Entrances.tooie_zones: every one of them has such an entry,
    and the hack takes the first entry that matches), and exit_game for all of the table: the game and the stay exit
    of those, 0 for the rest. The entries written; 0 without the exit map's pointer. Raises ValueError for a mapping
    that is not a permutation, or an entry the table does not have."""
    base = emu_state.BTHReader(emu).exit_map_ptr()
    if base is None:
        return 0
    entries = Doors.cross_exit_maps(mapping)[1] if mapping else []
    found = {}
    for i in range(EXIT_MAP_MAX):
        at = base + i * EXIT_MAP_ENTRY
        on_map = emu.read_u16(at + ON_MAP_AT)
        if on_map == 0:
            break
        found.setdefault((on_map, emu.read_u16(at + OG_MAP_AT), emu.read_u8(at + OG_EXIT_AT)), i)
    games = [(0, 0)] * EXIT_MAP_MAX
    for on_map, og_map, og_exit, to_map, to_exit, stay in entries:
        i = found.get((on_map, og_map, og_exit))
        if i is None:
            raise ValueError(f"Tooie's exit map has no entry for map 0x{on_map:X} to (0x{og_map:X}, {og_exit})")
        at = base + i * EXIT_MAP_ENTRY
        emu.write_u16(at + TO_MAP_AT, to_map)
        emu.write_u8(at + TO_EXIT_AT, to_exit)
        games[i] = (EXIT_GAME_BK, stay)
    for i, (game, stay) in enumerate(games):
        emu.write_u8(base + EXIT_GAME_AT + 2 * i, game)
        emu.write_u8(base + EXIT_GAME_AT + 2 * i + 1, stay)
    return len(entries)


def either_game(pm, rdram_base: int) -> bool:
    """EmuLoader's validation: RDRAM with Tooie's anchor or BK's."""
    return BTClient.validate_bt_signature(pm, rdram_base) or hack.validate(pm, rdram_base)


class SharedLoader(StockLoader):
    def __init__(self) -> None:
        # the EmuLoaderClient the stock client found (BTClient.py:16-21), the base of its BTEmuLoaderClient: the
        # emu_loader package, or without one the BK world's copy, which load_emu_loader gave the package's name
        BTClient.EmuLoaderClient.__init__(self, validation_func=either_game, pull_from_web=False)

    def resident(self) -> Optional[str]:
        return resident(self.read_u32)

    def get_anchor(self) -> Optional[int]:
        if self.resident() != TOOIE:
            return None
        return super().get_anchor()


_installed = {}


def install(loader: Callable[[], Any], on_tooie_goal: Callable[[], None],
            tooie_items: Optional[Callable[[Iterable[Any]], Optional[List[Any]]]] = None) -> None:
    """Patch the stock code (once per process; later calls only change where the patches point): `loader` gives the
    shared connection, `on_tooie_goal` is called when Tooie shows its goal reached, `tooie_items` gives the items
    received as Tooie's code should write them (None: not yet)."""
    _installed["loader"] = loader
    _installed["goal"] = on_tooie_goal
    _installed["items"] = tooie_items or list
    if _installed.get("done"):
        return
    _installed["done"] = True
    # the stock functions, called through this dict (a test stands in for them there)
    _installed["stock_victory"] = emu_game.check_victory
    _installed["stock_settings"] = emu_game.write_slot_settings
    _installed["stock_format"] = emu_game.format_item_message
    _installed["stock_items"] = emu_game.write_received_items

    def check_victory(emu, slot_data) -> bool:
        if _installed["stock_victory"](emu, slot_data):
            _installed["goal"]()
        return False

    def write_slot_settings(emu, slot_data, *args, **kwargs):
        result = _installed["stock_settings"](emu, slot_data, *args, **kwargs)
        settings = emu_state.BTHReader(emu).settings_ptr()
        if HUB_DOOR_SETTING is not None and settings is not None:
            emu.write_u8(settings + HUB_DOOR_SETTING, 1 if slot_data.get("hub_door") else 0)
        try:
            if result:      # the stock code wrote the exit map (client/game.py:241)
                write_cross_doors(emu, slot_data.get("cross_world_entrances"))
        except ValueError as exc:
            logger.error(f"This slot's world doors across the games cannot be written ({exc}): generate it again.")
        return result

    def format_item_message(emu, *args, **kwargs):
        if emu_state.BTHReader(emu).settings_ptr() is None:
            return None
        return _installed["stock_format"](emu, *args, **kwargs)

    def write_received_items(emu, items_received, *args, **kwargs):
        items = _installed["items"](items_received)
        if items is None:
            return {"error": -1}    # the trap shares are not known yet: the client asks for a write again then
        return _installed["stock_items"](emu, items, *args, **kwargs)

    emu_game.check_victory = check_victory
    emu_game.write_received_items = write_received_items
    emu_game.write_slot_settings = write_slot_settings
    emu_game.format_item_message = format_item_message
    BTClient.BTEmuLoaderClient = lambda: _installed["loader"]()
