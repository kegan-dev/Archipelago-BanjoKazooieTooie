"""The combined client without an emulator or a server: what BK gets of the items received (client/items.py), the
goal (client/goal.py and the context's send filter), the patches of the stock Tooie code (client/bridge.py), and
the dispatcher (BKBTClient.emulator_loop) on a fake emulator that switches games."""

import asyncio
import unittest
from typing import List, Optional

from NetUtils import ClientStatus, NetworkItem

from worlds.banjo_kazooie_tooie.bk.Items import all_item_table as bk_item_table
from worlds.banjo_kazooie_tooie.bk.Names import itemName as bk_item
from worlds.banjo_kazooie_tooie.bk.client import hack, ids
from worlds.banjo_kazooie.test.test_client import SETTINGS_AT, bk_game
from worlds.banjo_kazooie_tooie.bt.Items import all_item_table as bt_item_table

from .. import BanjoKazooieTooieWorld
from ..Moves import SHARED, active_chains
from ..client import goal, items
from ..client.resident import BK, TOOIE

ABILITY = ids.MOVE_OF       # a BK move's name -> the hack's ability byte
SEED = 0x5EED0C0C


def tooie_id(name: str) -> int:
    return bt_item_table[name].btid


def bk_id(name: str) -> int:
    return bk_item_table[name].bkid


class TestItems(unittest.TestCase):
    def test_bk_items_by_bk_id(self):
        got, _ = items.bk_items([bk_id(bk_item.JIGGY)] * 3 + [bk_id(bk_item.NOTE_DOORS[0])], {})
        self.assertEqual((got.jiggies, got.note_doors), (3, frozenset({1})))

    def test_shared_moves_from_tooies_items(self):
        got, _ = items.bk_items([tooie_id("Talon Trot"), tooie_id("Flight Pad")], {})
        self.assertEqual(got.moves, frozenset({ABILITY[bk_item.TALON_TROT], ABILITY[bk_item.FLIGHT]}))

    def test_progressive_copies(self):
        chains = active_chains(lambda name: name == "progressive_flight")
        one, _ = items.bk_items([tooie_id("Progressive Flight")], chains)
        two, _ = items.bk_items([tooie_id("Progressive Flight")] * 2, chains)
        self.assertEqual(one.moves, frozenset({ABILITY[bk_item.FLIGHT]}))
        self.assertEqual(two.moves, frozenset({ABILITY[bk_item.FLIGHT], ABILITY[bk_item.BEAK_BOMB]}))

    def test_every_chain_every_copy(self):
        """Each progressive item that holds a shared move gives BK, after n copies, the shared moves among its chain's
        first n, by BK's names: the advanced chains too, and Progressive Shoes' Wading Boots before Turbo Talon Trot."""
        from worlds.banjo_kazooie_tooie.bt.Items import progressive_ability_breakdown
        bk_of = {tooie: bk_name for bk_name, tooie in SHARED.items()}
        tried = []
        for name, chain in progressive_ability_breakdown.items():
            if not any(move in bk_of for move in chain):
                continue        # Progressive Eggs: the egg types, Tooie's alone
            tried.append(name)
            for n in range(len(chain) + 2):
                got, _ = items.bk_items([tooie_id(name)] * n, {name: list(chain)})
                want = frozenset(ABILITY[bk_of[move]] for move in chain[:n] if move in bk_of)
                self.assertEqual(got.moves, want, (name, n))
        self.assertEqual(len(tried), 8)     # beak buster, shoes, water training both ways, bash, flight, egg aim twice

    def test_tooies_own_items_give_bk_nothing(self):
        got, _ = items.bk_items([tooie_id("Jiggy"), tooie_id("Glide")], {})
        self.assertEqual(got, hack.Items())

    def test_every_id_of_the_slot_is_known_to_a_half(self):
        for name, code in BanjoKazooieTooieWorld.item_name_to_id.items():
            self.assertTrue(code in items.BK_NAME_OF_ID or code in items.TOOIE_NAME_OF_ID, name)
        for tooie in SHARED.values():
            self.assertIn(tooie_id(tooie), items.TOOIE_NAME_OF_ID)


class TestGoal(unittest.TestCase):
    def test_truth_table(self):
        for setting, needs in ((0, {TOOIE}), (1, {BK}), (2, {TOOIE, BK})):
            for reached in (set(), {TOOIE}, {BK}, {TOOIE, BK}):
                self.assertEqual(goal.met(setting, reached), needs <= reached, (setting, reached))


def run_with_context(test, scenario):
    """CommonContext starts a task when it is made, so it is made inside the loop the scenario runs in."""
    async def main():
        from ..BKBTClient import BanjoKazooieTooieContext
        ctx = BanjoKazooieTooieContext(None, None)
        ctx.slot, ctx.team, ctx.auth, ctx.items_ready = 1, 0, "Both", True
        ctx.slot_data = {"goal": 2, "bk": {"seed": SEED, "skip_intro": True, "notesanity": False, "layout": [0, 16]},
                         "options": {}, "custom_bt_data": {}}
        ctx.sent_msgs = []

        async def network(msgs):
            ctx.sent_msgs.extend(msgs)

        from CommonClient import CommonContext
        ctx._network = network
        CommonContext_send = CommonContext.send_msgs

        async def send(self, msgs):     # CommonContext.send_msgs without a server
            await self._network(msgs)

        CommonContext.send_msgs = send
        try:
            await scenario(ctx)
        finally:
            CommonContext.send_msgs = CommonContext_send
            ctx.keep_alive_task.cancel()
    asyncio.run(main())


class TestGoalSending(unittest.TestCase):
    def test_both_needed(self):
        async def scenario(ctx):
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])  # someone else's try
            await ctx.reach_goal(TOOIE)
            self.assertNotIn(ClientStatus.CLIENT_GOAL, [m.get("status") for m in ctx.sent_msgs])
            await ctx.reach_goal(BK)
            goals = [m for m in ctx.sent_msgs if m.get("status") == ClientStatus.CLIENT_GOAL]
            self.assertEqual(len(goals), 1)
            sets = [m for m in ctx.sent_msgs if m.get("cmd") == "Set"]
            self.assertEqual([m["operations"][0]["value"] for m in sets], [{TOOIE: True}, {BK: True}])
        run_with_context(self, scenario)

    def test_a_goal_reached_earlier_counts(self):
        async def scenario(ctx):
            ctx.stored_data[ctx.goal_key()] = {TOOIE: True}     # kept on the server from an earlier session
            await ctx.reach_goal(BK)
            self.assertIn(ClientStatus.CLIENT_GOAL, [m.get("status") for m in ctx.sent_msgs])
        run_with_context(self, scenario)


class TestBridge(unittest.TestCase):
    def test_patch_points_exist(self):
        from worlds.banjo_kazooie_tooie.bt import BTClient
        from worlds.banjo_kazooie_tooie.bt.client import game, state
        for module, name in ((game, "check_victory"), (game, "write_slot_settings"), (game, "format_item_message"),
                             (game, "drain_item_messages"), (BTClient, "BTEmuLoaderClient"),
                             (BTClient, "emu_loader_monitor_task"), (BTClient, "validate_bt_signature"),
                             (state, "BTHReader")):
            self.assertTrue(callable(getattr(module, name)), name)


class TestHubDoorSetting(unittest.TestCase):
    def test_the_byte_the_stock_client_leaves_alone(self):
        """+0x25: after the jiggy requirements (11 bytes from 0x1A) and before the silo requirements, which the
        stock client writes from 0x26 (its SETTING_* offsets); the fork's door.c asserts the same offset."""
        from worlds.banjo_kazooie_tooie.bt.client import game
        from ..client import bridge
        self.assertEqual(bridge.HUB_DOOR_SETTING, game.SETTING_JIGGY_REQUIREMENTS_BASE + 11)
        self.assertEqual(bridge.HUB_DOOR_SETTING + 1, game.SETTING_SILO_REQUIREMENTS_BASE)
        offsets = {value for name, value in vars(game).items() if name.startswith("SETTING_")}
        self.assertNotIn(bridge.HUB_DOOR_SETTING, offsets)

    def test_patches(self):
        """The patched stock functions: the hub door's byte after the settings, Tooie's goal reported instead of
        sent, and no item text without the settings pointer."""
        from worlds.banjo_kazooie_tooie.bt.client import game, state
        from ..client import bridge
        bridge.install(lambda: None, lambda: reached.append("tooie"))
        reached, writes, calls = [], [], []
        settings_at = [0x80420000]

        class Reader:
            def __init__(self, emu):
                pass

            def settings_ptr(self):
                return settings_at[0]

        class Emu:
            def write_u8(self, address, value):
                writes.append((address, value))

        saved = dict(bridge._installed), state.BTHReader
        bridge._installed.update(stock_settings=lambda emu, data: calls.append("settings"),
                                 stock_victory=lambda emu, data: True,
                                 stock_format=lambda emu, *a: "text")
        state.BTHReader = Reader
        try:
            game.write_slot_settings(Emu(), {"hub_door": 1})
            self.assertEqual((calls, writes), (["settings"], [(0x80420025, 1)]))
            self.assertFalse(game.check_victory(Emu(), {}))
            self.assertEqual(reached, ["tooie"])
            self.assertEqual(game.format_item_message(Emu(), 1230923, "Green Relic", "x", True, 110), "text")
            settings_at[0] = None
            self.assertIsNone(game.format_item_message(Emu(), 1230923, "Green Relic", "x", True, 110))
        finally:
            bridge._installed.clear()
            bridge._installed.update(saved[0])
            state.BTHReader = saved[1]


class TestTrapShares(unittest.TestCase):
    """client/traps.py: a trap or a nest goes to the game whose half asks first, once, and the split survives the
    server."""
    trip, slip, tip = tooie_id("Trip Trap"), tooie_id("Slip Trap"), tooie_id("Tip Trap")
    egg, feather, golden = tooie_id("Egg Nest"), tooie_id("Feather Nest"), tooie_id("Golden Egg Nest")
    KNOWN = {"bk": [0] * 7, "tooie": [0] * 7}

    def test_each_trap_once(self):
        from ..client import traps
        shares = traps.TrapShares(self.KNOWN)
        self.assertTrue(shares.take("bk", traps.received([self.trip, self.trip, self.tip, tooie_id("Jiggy")])))
        self.assertEqual(shares.share("bk"), (2, 0, 0, 0, 1, 0, 0))
        self.assertFalse(shares.take("tooie", traps.received([self.trip, self.trip, self.tip])))
        self.assertEqual(shares.share("tooie"), (0,) * 7)
        self.assertTrue(shares.take("tooie", traps.received([self.trip, self.trip, self.tip, self.trip, self.slip])))
        self.assertEqual((shares.share("bk"), shares.share("tooie")), ((2, 0, 0, 0, 1, 0, 0), (1, 1, 0, 0, 0, 0, 0)))
        self.assertEqual(traps.TrapShares(shares.to_storage()).to_storage(), shares.to_storage())

    def test_each_nest_once(self):
        """Egg and Feather Nests are split as the traps are; Golden Egg Nests are not counted (they stay Tooie's)."""
        from ..client import traps
        shares = traps.TrapShares(self.KNOWN)
        self.assertTrue(shares.take("bk", traps.received([self.egg, self.egg, self.feather, self.golden])))
        self.assertEqual(shares.share("bk")[traps.EGG_NEST:], (2, 1))
        self.assertTrue(shares.take("tooie", traps.received([self.egg, self.egg, self.feather, self.egg])))
        self.assertEqual((shares.share("bk")[5:], shares.share("tooie")[5:]), ((2, 1), (1, 0)))
        self.assertEqual(traps.received([self.golden]), [0] * 7)

    def test_nests_before_the_split_are_tooies(self):
        """Shares stored before the nests were split (five counts) or none at all: the nests received so far are
        Tooie's, which the stock client gave them all to and whose hack must never see its total go down."""
        from ..client import traps
        for stored in (None, {"bk": [1, 0, 0, 0, 0], "tooie": [0] * 5}):
            shares = traps.TrapShares(stored)
            self.assertFalse(shares.nests_known, stored)
            self.assertTrue(shares.take("bk", traps.received([self.trip, self.egg, self.egg, self.feather])), stored)
            self.assertEqual(shares.share("tooie")[5:], (2, 1), stored)
            self.assertEqual(shares.share("bk"), (1, 0, 0, 0, 0, 0, 0), stored)
            self.assertTrue(shares.take("bk", traps.received([self.trip, self.egg, self.egg, self.feather, self.egg])))
            self.assertEqual(shares.share("bk")[5:], (1, 0), stored)
            self.assertEqual(len(shares.to_storage()["bk"]), 7)

    def test_what_the_server_holds_is_checked(self):
        from ..client import traps
        none = {"bk": [0] * 7, "tooie": [0] * 7}
        for stored in (None, {}, {"bk": [1, 2]}, {"bk": "1"}, {"bk": [-1, 0, 0, 0, 0]}, {"bk": [0.5, 0, 0, 0, 0]},
                       {"bk": [0] * 7}, {"bk": [0] * 7, "tooie": [0] * 5}):
            shares = traps.TrapShares(stored)
            self.assertEqual(shares.to_storage(), none, stored)
            self.assertFalse(shares.nests_known, stored)
        self.assertEqual(traps.TrapShares({"tooie": [0, 0, 3, 0, 0]}).share("tooie"), (0, 0, 3, 0, 0, 0, 0))
        self.assertTrue(traps.TrapShares(self.KNOWN).nests_known)

    def test_tooie_writes_its_share(self):
        """The stock writer counts each trap and nest id it is given: BK's share, the first of each kind, is taken
        out."""
        from ..client import traps
        jiggy = tooie_id("Jiggy")
        items = [NetworkItem(i, 1, 1, 1) for i in (self.trip, jiggy, self.trip, self.tip, self.trip, self.egg,
                                                   self.feather, self.egg)]
        shares = traps.TrapShares({"bk": [2, 0, 0, 0, 0, 1, 0], "tooie": [1, 0, 0, 0, 1, 1, 1]})
        self.assertEqual([item.item for item in shares.for_tooie(items)], [jiggy, self.tip, self.trip, self.feather,
                                                                           self.egg])

    def test_tooie_keeps_every_progressive_copy(self):
        """A progressive item teaches both games: the split takes none of its copies from the stock writer."""
        from ..client import traps
        progressive = [tooie_id(name) for name in ("Progressive Flight", "Progressive Shoes", "Progressive Beak Buster",
                                                   "Progressive Water Training", "Progressive Egg Aim",
                                                   "Progressive Bash Attack")]
        received = [self.trip, *progressive, self.egg, *progressive]
        items = [NetworkItem(i, 1, 1, 1) for i in received]
        shares = traps.TrapShares({"bk": [1, 0, 0, 0, 0, 1, 0], "tooie": [0] * 7})
        self.assertEqual([item.item for item in shares.for_tooie(items)], progressive * 2)

    def test_the_stock_writer_waits_for_the_shares(self):
        from worlds.banjo_kazooie_tooie.bt.client import game
        from ..client import bridge
        written = []
        share = [None]
        saved = dict(bridge._installed)
        try:
            bridge.install(lambda: None, lambda: None, lambda items: share[0])
            bridge._installed["stock_items"] = lambda emu, items: written.append(list(items)) or {"items": len(items)}
            self.assertEqual(game.write_received_items(object(), [1, 2, 3]), {"error": -1})
            self.assertEqual(written, [])
            share[0] = [1, 3]
            self.assertEqual(game.write_received_items(object(), [1, 2, 3]), {"items": 2})
            self.assertEqual(written, [[1, 3]])
        finally:
            bridge._installed.clear()
            bridge._installed.update(saved)


class TestLinkInContext(unittest.TestCase):
    """The combined context's half of the link: the traps' shares from data storage, Tooie's pending death and tag
    taken by BK while it runs and handed back when it stops."""

    def test_shares_from_the_server(self):
        async def scenario(ctx):
            trip = tooie_id("Trip Trap")
            ctx.items_received = [NetworkItem(trip, 1, 1, 1), NetworkItem(trip, 1, 1, 1)]
            self.assertIsNone(ctx.bk_traps())               # not read yet: nothing given
            self.assertIsNone(ctx.tooie_items(ctx.items_received))
            ctx.on_package("Retrieved", {"keys": {ctx.trap_key(): {"bk": [0] * 5, "tooie": [1, 0, 0, 0, 0]}}})
            self.assertEqual(ctx.emu_last_items_count, -1)  # Tooie's items written again, with its share
            self.assertEqual(ctx.bk_traps(), (1, 0, 0, 0, 0))   # the trip no game had
            await asyncio.sleep(0)
            sets = [m for m in ctx.sent_msgs if m.get("cmd") == "Set" and m["key"] == ctx.trap_key()]
            self.assertEqual(sets[-1]["operations"][0]["value"], {"bk": [1, 0, 0, 0, 0, 0, 0],
                                                                  "tooie": [1, 0, 0, 0, 0, 0, 0]})
            self.assertEqual([i.item for i in ctx.tooie_items(ctx.items_received)], [trip])
        run_with_context(self, scenario)

    def test_nothing_stored_is_none_given(self):
        async def scenario(ctx):
            ctx.on_package("Retrieved", {"keys": {ctx.trap_key(): None}})
            self.assertEqual(ctx.shares.to_storage(), {"bk": [0] * 7, "tooie": [0] * 7})
        run_with_context(self, scenario)

    def test_nests_become_bk_refills(self):
        """BK's share of the nests is its refills: an Egg Nest the blue eggs', a Feather Nest the less full
        feather's. wanted_items only reads the shares; BK's poll takes the nests no game has (bk_traps)."""
        async def scenario(ctx):
            egg, feather = tooie_id("Egg Nest"), tooie_id("Feather Nest")
            ctx.items_received = [NetworkItem(i, 1, 1, 1) for i in (egg, feather, egg)]
            self.assertEqual(ctx.wanted_items().refills, (0, 0, 0, 0))      # not read yet
            ctx.on_package("Retrieved", {"keys": {ctx.trap_key(): {"bk": [0] * 7, "tooie": [0] * 7}}})
            self.assertEqual(ctx.wanted_items().refills, (0, 0, 0, 0))      # read, none taken yet
            self.assertEqual(ctx.bk_traps(), (0,) * 5)                       # BK's poll takes the nests
            self.assertEqual(ctx.wanted_items().refills, (2, 0, 0, 1))
            self.assertEqual(ctx.tooie_items(ctx.items_received), [])        # none left for Tooie
            ctx.items_received.append(NetworkItem(egg, 1, 1, 1))
            self.assertEqual([i.item for i in ctx.tooie_items(ctx.items_received)], [egg])   # Tooie asked first
            self.assertEqual(ctx.wanted_items().refills, (2, 0, 0, 1))
        run_with_context(self, scenario)

    def test_deaths_and_tags_go_to_the_game_running(self):
        async def scenario(ctx):
            ctx.deathlink_enabled = ctx.taglink_enabled = True
            ctx.deathlink_pending, ctx.pending_tag_link = True, True    # as Tooie's code keeps them
            ctx.bk_link_inbox()                                         # BK runs: BK takes them
            self.assertEqual((ctx.deathlink_pending, ctx.pending_tag_link), (False, False))
            self.assertEqual((ctx.link_driver.deaths_owed, ctx.link_driver.tags_owed), (1, 1))
            ctx.bk_left()                                               # BK stopped before giving them
            self.assertEqual((ctx.deathlink_pending, ctx.pending_tag_link), (True, True))
            ctx.deathlink_enabled = False
            ctx.bk_link_inbox()                                         # death link off: Tooie's code keeps it
            self.assertTrue(ctx.deathlink_pending)
        run_with_context(self, scenario)


class FakeLoader:
    """An emulator showing, at each look, the next game of `script` (TOOIE, BK or None); BK's memory a booted BK."""

    def __init__(self, script: List[Optional[str]], ctx) -> None:
        self.script, self.ctx, self.ram = list(script), ctx, bk_game()
        self.now: Optional[str] = None
        self.seen: List[Optional[str]] = []
        self.emulator_info = type("Info", (), {"readable_emulator_name": "a fake emulator"})()

    def is_connected(self) -> bool:
        return True

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def resident(self) -> Optional[str]:
        if not self.script:
            self.ctx.exit_event.set()
            return None
        self.now = self.script.pop(0)
        self.seen.append(self.now)
        return self.now

    def read_u32(self, address: int) -> int:
        assert self.now == BK, "BK's memory read while BK does not run"
        return self.ram.read_u32(address)

    def write_u32(self, address: int, value: int) -> None:
        assert self.now == BK, "BK's memory written while BK does not run"
        self.ram.write_u32(address, value)

    def write_u8(self, address: int, value: int) -> None:
        assert self.now == BK, "BK's memory written while BK does not run"
        self.ram.write_u8(address, value)


class TestDispatcher(unittest.TestCase):
    def test_each_half_only_while_its_game_runs(self):
        from worlds.banjo_kazooie_tooie.bt import BTClient
        from .. import BKBTClient
        script = [TOOIE] * 3 + [None] * 2 + [BK] * 4 + [None] * 2 + [TOOIE] * 3 + [BK] * 2

        async def scenario(ctx):
            loader = FakeLoader(script, ctx)
            tooie_runs = []         # (what ran when the stock monitor did a step)

            async def stock_monitor(c):
                while True:
                    tooie_runs.append(loader.now)
                    await asyncio.sleep(0)

            saved = (BKBTClient.bridge.SharedLoader, BTClient.emu_loader_monitor_task, BKBTClient.POLL)
            BKBTClient.bridge.SharedLoader = lambda: loader
            BTClient.emu_loader_monitor_task = stock_monitor
            BKBTClient.POLL = 0.01
            try:
                await asyncio.wait_for(BKBTClient.emulator_loop(ctx), timeout=10)
            finally:
                BKBTClient.bridge.SharedLoader, BTClient.emu_loader_monitor_task, BKBTClient.POLL = saved
            self.assertEqual(loader.seen, script)
            self.assertTrue(tooie_runs)
            self.assertEqual(set(tooie_runs), {TOOIE}, "the stock monitor ran while Tooie did not")
            self.assertEqual(hack.read_settings(loader.ram, hack.find(loader.ram))[0], SEED)   # BK committed
        run_with_context(self, scenario)


class FakeTooieRam:
    """Tooie's exit map in a fake RAM, big-endian, for the stock code's writer and the combined client's."""
    BASE = 0x80450000

    def __init__(self) -> None:
        self.mem = {}

    def read_u8(self, address: int) -> int:
        return self.mem.get(address, 0)

    def read_u16(self, address: int) -> int:
        return self.read_u8(address) << 8 | self.read_u8(address + 1)

    def write_u8(self, address: int, value: int) -> None:
        self.mem[address] = value & 0xFF

    def write_u16(self, address: int, value: int) -> None:
        self.write_u8(address, value >> 8)
        self.write_u8(address + 1, value)

    def lookup(self, on_map: int, og_map: int, og_exit: int):
        """What the hack's exits_can_pass takes for a guard's load: the first entry that matches, its destination,
        and its exit_game record (hack/bt/n64/src/exits.c); None for no entry."""
        from ..client import bridge
        for i in range(bridge.EXIT_MAP_MAX):
            at = self.BASE + i * bridge.EXIT_MAP_ENTRY
            if self.read_u16(at) == 0:
                return None
            if self.read_u16(at) == on_map and self.read_u16(at + 2) == og_map and self.read_u8(at + 6) == og_exit:
                game = self.BASE + bridge.EXIT_GAME_AT + 2 * i
                return self.read_u16(at + 4), self.read_u8(at + 7), self.read_u8(game), self.read_u8(game + 1)
        return None


class TestCrossDoors(unittest.TestCase):
    """The doors across the games in both exit maps: BK's from the client's bk_exits, Tooie's from the stock code's
    apply_zone_warps for the slot data's loading_zones and then the combined client's write over it
    (client/bridge.py, write_cross_doors), as Tooie's hack then matches them."""

    def shuffled(self, seed):
        from random import Random
        from .. import Entrances
        worlds = list(Entrances.LEVELS)
        Random(seed).shuffle(worlds)
        return dict(zip(Entrances.LEVELS, worlds))

    def tooie_table(self, mapping):
        from worlds.banjo_kazooie_tooie.bt.client import game, state
        from worlds.banjo_kazooie_tooie.bt.Names import regionName as bt_region
        from .. import Entrances
        from ..client import bridge
        ram = FakeTooieRam()

        class Reader:
            def __init__(self, emu):
                pass

            def exit_map_ptr(self):
                return FakeTooieRam.BASE

        bosses = (bt_region.MTBOSS, bt_region.GMBOSS, bt_region.WWBOSS, bt_region.JRBOSS, bt_region.TLBOSS,
                  bt_region.GIBOSS, bt_region.HPFBOSS, bt_region.HPIBOSS, bt_region.CCBOSS)
        zones = {**Entrances.tooie_zones(mapping), **{boss: boss for boss in bosses}}
        saved = game.BTHReader, state.BTHReader
        game.BTHReader = state.BTHReader = Reader
        try:
            written = game.apply_zone_warps(ram, {"custom_bt_data": {"loading_zones": zones}})
            crossed = bridge.write_cross_doors(ram, mapping)
        finally:
            game.BTHReader, state.BTHReader = saved
        self.assertEqual(written, 37)
        return ram, crossed

    def test_every_door_and_way_out_in_tooies_table(self):
        from worlds.banjo_kazooie_tooie.bk.Entrances import DOOR_OF as BK_DOOR_OF
        from .. import Entrances
        for seed in range(40):
            mapping = self.shuffled(seed)
            behind = {world: door for door, world in mapping.items()}
            ram, crossed = self.tooie_table(mapping)
            self.assertEqual(crossed, len(Entrances.cross_exit_maps(mapping)[1]))
            for t in Entrances.TOOIE_DOORS:
                world = mapping[t.name]
                for exit in (t.entrance, *t.extra_exits):
                    if world in BK_DOOR_OF:
                        want = (*BK_DOOR_OF[world].entrance, 1, t.way_back)
                    else:
                        v = Entrances.TOOIE_DOOR_OF[world]
                        want = (v.world_map, v.entrance, 0, 0)
                    self.assertEqual(ram.lookup(t.hag_map, t.world_map, exit), want, (seed, t.name, exit))
                # the way out of the Tooie world t.name, to the door it is behind
                door = behind[t.name]
                if door in BK_DOOR_OF:
                    want = (*BK_DOOR_OF[door].way_out, 1, t.entrance)
                else:
                    d = Entrances.TOOIE_DOOR_OF[door]
                    want = (d.hag_map, d.way_back, 0, 0)
                self.assertEqual(ram.lookup(t.world_map, t.hag_map, t.way_back), want, (seed, t.name))

    def test_no_doors_across_leaves_the_games_records_zero(self):
        from .. import Entrances
        ram, crossed = self.tooie_table(Entrances.identity())
        self.assertEqual(crossed, 0)
        from ..client import bridge
        self.assertTrue(all(ram.read_u8(FakeTooieRam.BASE + bridge.EXIT_GAME_AT + i) == 0
                            for i in range(2 * bridge.EXIT_MAP_MAX)))

    def test_bk_exits_across_the_games(self):
        from types import SimpleNamespace
        from worlds.banjo_kazooie_tooie.bk.Entrances import LEVELS as BK_LEVELS
        from worlds.banjo_kazooie_tooie.bt.Names import regionName as bt_region
        from .. import BKBTClient, Entrances
        mapping = {**Entrances.identity(), BK_LEVELS[0]: bt_region.MT, bt_region.MT: BK_LEVELS[0]}
        ctx = SimpleNamespace(slot_data={"cross_world_entrances": mapping, "bk": {}}, told=set())
        ctx.bk_data = lambda: ctx.slot_data["bk"]
        exits = BKBTClient.BanjoKazooieTooieContext.bk_exits(ctx)
        self.assertEqual(exits, [hack.Exit(0x69, 0x02, 0x05, hack.GAME_TOOIE, 0x0B8, 10),
                                 hack.Exit(0x02, 0x69, 0x02, hack.GAME_TOOIE, 0x14F, 2)])
        self.assertEqual(len(hack.exits_block(exits)), hack.EXITS_SIZE)
        ctx.slot_data = {"cross_world_entrances": {**mapping, bt_region.MT: bt_region.GM}, "bk": {}}
        self.assertIsNone(BKBTClient.BanjoKazooieTooieContext.bk_exits(ctx))
