"""The world doors of both games shuffled together (Entrances.py; the option cross_game_world_entrances)."""

from random import Random
from unittest import TestCase

from worlds.banjo_kazooie_tooie.bk import Entrances as BKEntrances
from worlds.banjo_kazooie_tooie.bk.LogicData import REGIONS
from worlds.banjo_kazooie_tooie.bk.Names import regionName as bk_region
from worlds.banjo_kazooie_tooie.bt.Names import regionName as bt_region

from . import CombinedTestBase, make
from .. import Entrances
from ..Names import BK_LOBBY, HUB_IN


def shuffled(seed: int) -> dict:
    worlds = list(Entrances.LEVELS)
    Random(seed).shuffle(worlds)
    return dict(zip(Entrances.LEVELS, worlds))


SWAP = {**Entrances.identity(), BKEntrances.LEVELS[0]: bt_region.MT, bt_region.MT: BKEntrances.LEVELS[0]}


def stock_keys(zones: dict) -> set:
    """The (on_map, og_map, og_exit) of every entry the stock Tooie client writes for `zones` (client/game.py,
    apply_zone_warps, of the Tooie world)."""
    from worlds.banjo_kazooie_tooie.bt.client.game import WORLD_MAP_ENTRANCES, WORLD_NAME_TO_MAP_ID
    keys = set()
    for orig_name, new_name in zones.items():
        orig_id, new_id = WORLD_NAME_TO_MAP_ID[orig_name], WORLD_NAME_TO_MAP_ID[new_name]
        orig, new = WORLD_MAP_ENTRANCES[orig_id], WORLD_MAP_ENTRANCES[new_id]
        keys.add((orig["exit_map"], orig_id, orig["entrance_id"]))
        keys.add((new_id, new["exit_map"], new["exit_id"]))
        if orig_id == 0xC7:
            keys.add((orig["exit_map"], orig_id, 16))
    return keys


class TestTables(TestCase):
    def test_tooie_names_are_tooies(self):
        names = [bt_region.MT, bt_region.GM, bt_region.WW, bt_region.JR, bt_region.TL, bt_region.GIO, bt_region.HP,
                 bt_region.CC, bt_region.CK]
        zones = [bt_region.MTE, bt_region.GGME, bt_region.WWE, bt_region.JRLE, bt_region.TDLE, bt_region.GIE,
                 bt_region.HFPE, bt_region.CCLE, bt_region.CKE]
        self.assertEqual(list(Entrances.TOOIE_LEVELS), names)
        self.assertEqual([door.zone_region for door in Entrances.TOOIE_DOORS], zones)
        self.assertFalse(set(Entrances.TOOIE_LEVELS) & set(BKEntrances.LEVELS))

    def test_tooie_numbers_are_the_stock_clients(self):
        from worlds.banjo_kazooie_tooie.bt.client.game import WORLD_MAP_ENTRANCES
        for door in Entrances.TOOIE_DOORS:
            data = WORLD_MAP_ENTRANCES[door.world_map]
            self.assertEqual(data["name"], door.name)
            self.assertEqual((data["entrance_id"], data["exit_map"], data["exit_id"]),
                             (door.entrance, door.hag_map, door.way_back), door.name)

    def test_identity_writes_nothing(self):
        self.assertEqual(Entrances.cross_exit_maps(Entrances.identity()), ([], []))
        self.assertEqual(Entrances.tooie_zones(Entrances.identity()), {name: name for name in Entrances.TOOIE_LEVELS})

    def test_refuses_what_is_not_a_permutation(self):
        with self.assertRaises(ValueError):
            Entrances.cross_exit_maps({**Entrances.identity(), bt_region.MT: bt_region.GM})

    def test_a_swap_across_the_games(self):
        mm = BKEntrances.DOOR_OF[BKEntrances.LEVELS[0]]
        bk, tooie = Entrances.cross_exit_maps(SWAP)
        self.assertEqual(bk, [
            (0x69, 0x02, 0x05, Entrances.GAME_TOOIE, 0x0B8, 10),       # MM's door into Mayahem Temple
            (0x02, 0x69, 0x02, Entrances.GAME_TOOIE, 0x14F, 2),        # MM's way out to Wooded Hollow
        ])
        self.assertEqual(tooie, [
            (0x0B8, 0x14F, 2, 0x69, 0x02, 10),      # Mayahem Temple's way out to MM's door; Tooie saves at its entrance
            (0x14F, 0x0B8, 10, 0x02, 0x05, 2),      # Wooded Hollow's entrance into MM; Tooie saves at its way back
        ])
        self.assertEqual(mm.way_out, (0x69, 0x02))
        self.assertEqual(Entrances.tooie_zones(SWAP)[bt_region.MT], bt_region.MT)

    def test_bk_doors_among_themselves_as_bks_own(self):
        mapping = {**Entrances.identity(), **{level: world for level, world in
                                               zip(BKEntrances.LEVELS, BKEntrances.LEVELS[1:] + BKEntrances.LEVELS[:1])}}
        bk, tooie = Entrances.cross_exit_maps(mapping)
        self.assertEqual(sorted(bk), sorted(BKEntrances.exit_map({level: mapping[level] for level in BKEntrances.LEVELS})))
        self.assertEqual(tooie, [])

    def test_any_mapping_fits_and_lands_on_the_stock_entries(self):
        """BK's 32 entries hold any mapping, and every Tooie entry into BK has the key of an entry the stock client
        writes for tooie_zones, so that the client writes it over that one (first match wins in the hack)."""
        for seed in range(300):
            mapping = shuffled(seed)
            bk, tooie = Entrances.cross_exit_maps(mapping)
            self.assertLessEqual(len(bk), 32)
            zones = Entrances.tooie_zones(mapping)
            self.assertEqual(sorted(zones.values()), sorted(Entrances.TOOIE_LEVELS))
            keys = stock_keys(zones)
            for entry in tooie:
                self.assertIn(entry[:3], keys, (seed, entry))
            self.assertEqual(len({entry[:3] for entry in tooie}), len(tooie))
            for entry in bk:
                self.assertIn(entry[3], (Entrances.GAME_BK, Entrances.GAME_TOOIE))
                if entry[3] == Entrances.GAME_BK:
                    self.assertLessEqual(entry[4], 0xFF)

    def test_every_door_and_world_is_one_region(self):
        for level in Entrances.LEVELS:
            self.assertTrue(Entrances.entry_region(level))
            self.assertTrue(Entrances.door_region(level))
        self.assertEqual(Entrances.entry_region(bt_region.JR), bt_region.JR)
        self.assertEqual(Entrances.door_region(bt_region.CK), bt_region.CKE)


class TestCrossWorldEntrances(CombinedTestBase):
    """cross_game_world_entrances: the eighteen doors drawn together, with a stream of their own."""
    options = {"cross_game_world_entrances": True, "bk_randomize_world_entrances": True}

    def setUp(self) -> None:
        if self.auto_construct:
            self.world_setup(1)

    def test_doors_drawn_and_pointed(self):
        world = self.world
        mapping = world.cross_entrances
        self.assertTrue(Entrances.is_permutation(mapping))
        self.assertGreaterEqual(world.cross_draws, 1)
        for level in Entrances.LEVELS:
            self.assertEqual(world.cross_doors[(level, "door")].connected_region.name,
                             world.bk.bk_region(Entrances.entry_region(mapping[level])), level)
        behind = {w: d for d, w in mapping.items()}
        for level in Entrances.LEVELS:
            self.assertEqual(world.cross_doors[(level, "out")].connected_region.name,
                             world.bk.bk_region(Entrances.door_region(behind[level])), level)

    def test_each_games_own_shuffle_is_off(self):
        self.assertFalse(self.world.options.bk_randomize_world_entrances)
        self.assertFalse(self.world.options.randomize_world_entrance_loading_zones)
        self.assertEqual(self.world.bk.world_entrances, BKEntrances.identity())

    def test_slot_data(self):
        data = self.world.fill_slot_data()
        self.assertEqual(data["cross_world_entrances"], self.world.cross_entrances)
        self.assertEqual(data["bk"]["world_entrances"], BKEntrances.identity())
        zones = data["custom_bt_data"]["loading_zones"]
        self.assertEqual({door: zones[door] for door in Entrances.TOOIE_LEVELS},
                         Entrances.tooie_zones(self.world.cross_entrances))
        self.assertEqual(data["contract"], 5)

    def test_bk_reached_from_the_hub_and_the_doors_into_it(self):
        bk_regions = {region for region, _level, _map in REGIONS} - {bk_region.SM}
        allowed = {HUB_IN} | {self.world.cross_doors[key].name for key in self.world.cross_doors}
        for region in self.multiworld.get_regions(self.player):
            if region.name in bk_regions:
                for entrance in region.entrances:
                    self.assertTrue(entrance.parent_region.name in bk_regions or entrance.name in allowed,
                                    entrance.name)
        lobby = self.world.get_region(BK_LOBBY)
        self.assertIn(HUB_IN, [entrance.name for entrance in lobby.entrances])

    def test_spoiler_names_every_door(self):
        import io
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        text = handle.getvalue()
        self.assertIn("World doors of both games", text)
        self.assertEqual(text.count(" -> "), 18)

    def test_tooie_half_draws_the_same(self):
        from test.general import gen_steps
        on = make({"cross_game_world_entrances": True}, seed=2, steps=gen_steps)
        off = make({}, seed=2, steps=gen_steps)
        self.assertEqual(on.worlds[1].random.getstate(), off.worlds[1].random.getstate(),
                         "the doors' draw takes nothing from the world's random")


class TestCrossTracker(TestCase):
    """The Universal Tracker: a slot made again from its slot data (re_gen_passthrough) has the same doors, from
    the slot data and not drawn."""

    def test_doors_from_the_slot_data(self):
        from argparse import Namespace
        from BaseClasses import CollectionState, MultiWorld
        from worlds.AutoWorld import call_all
        from .. import BanjoKazooieTooieWorld
        from ..Names import GAME
        first = make({"cross_game_world_entrances": True}, seed=3, steps=("generate_early", "create_regions",
                                                                         "create_items", "set_rules", "connect_entrances"))
        import json
        from NetUtils import encode
        data = json.loads(encode(first.worlds[1].fill_slot_data()))        # as the tracker gets it, through JSON
        again = MultiWorld(1)
        again.game = {1: GAME}
        again.player_name = {1: "Tester1"}
        again.set_seed(99)      # another seed: a draw would give other doors
        args = Namespace()
        for key, option in BanjoKazooieTooieWorld.options_dataclass.type_hints.items():
            setattr(args, key, {1: option.from_any(option.default)})
        again.set_options(args)
        again.state = CollectionState(again)
        again.re_gen_passthrough = {GAME: data}
        for step in ("generate_early", "create_regions", "create_items", "set_rules", "connect_entrances"):
            call_all(again, step)
        world = again.worlds[1]
        self.assertEqual(world.cross_entrances, data["cross_world_entrances"])
        self.assertEqual(world.cross_draws, 0)
        for level in Entrances.LEVELS:
            self.assertEqual(world.cross_doors[(level, "door")].connected_region.name,
                             world.bk.bk_region(Entrances.entry_region(world.cross_entrances[level])), level)
