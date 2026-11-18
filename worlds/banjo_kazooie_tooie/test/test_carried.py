"""The two worlds the combined world carries (carried.py): run as its subpackages bk and bt, never registered as
worlds, and the only way the combined world reaches their code, so that its apworld works installed alone."""

import importlib
import json
import re
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from worlds import LauncherComponents
from worlds.AutoWorld import AutoWorldRegister

from .. import BanjoKazooieTooieWorld, bk, bt
from ..carried import carry

WORLD = Path(__file__).parents[1]
CARRIED = ("worlds.banjo_kazooie_tooie.bk", "worlds.banjo_kazooie_tooie.bt")


class TestCarried(TestCase):
    def test_built_on_the_carried_tooie(self):
        self.assertIs(BanjoKazooieTooieWorld.__mro__[1], bt.BanjoTooieWorld)
        self.assertEqual(bt.BanjoTooieWorld.world_version.as_simple_string(), "4.13.1")   # what its client checks
        self.assertEqual(bt.BanjoTooieWorld.manifest["game"], "Banjo-Tooie")

    def test_the_carried_bk_is_this_build(self):
        # the two worlds ship at one version (tools/make_apworlds.py), and the combined world carries this build's BK
        self.assertEqual(bk.BanjoKazooieWorld.world_version, BanjoKazooieTooieWorld.world_version)

    def test_nothing_registered(self):
        registered = list(AutoWorldRegister.world_types.values())
        self.assertNotIn(bt.BanjoTooieWorld, registered)
        self.assertNotIn(bk.BanjoKazooieWorld, registered)
        for world in registered:
            self.assertFalse(world.__module__.startswith(CARRIED), world)

    def test_no_launcher_entries(self):
        names = [component.display_name for component in LauncherComponents.components]
        for name in ("Banjo-Kazooie Client", "Banjo-Tooie Client", "Banjo-Kazooie & Tooie Client"):
            self.assertLessEqual(names.count(name), 1, name)
        for component in LauncherComponents.components:
            self.assertFalse(getattr(component.func, "__module__", "").startswith(CARRIED), component.display_name)

    def test_a_first_import_registers_for_real(self):
        """A world that the carried world's __init__ imports for the first time, as BK's rules import the generic
        world when no world loaded before imported it (an AP_TEST_WORLDS run of this world alone), registers for real,
        with its Launcher entry; the carried world's own class and entry still do not. Until 2026-11-17 the first was
        lost with the stand-ins, and the carried world refused to load."""
        side = "_bkbt_test_side_world"
        carried = "_bkbt_test_carried"
        own_world = (
            "from worlds.AutoWorld import World\n"
            "from worlds.LauncherComponents import Component, components\n"
            f"import {side}\n"
            "def launch(*args):\n"
            "    pass\n"
            "components.append(Component('BKBT Test Carried Client', func=launch))\n"
            "class CarriedWorld(World):\n"
            "    game = 'BKBT Test Carried'\n"
            "    item_name_to_id = {}\n"
            "    location_name_to_id = {}\n")
        side_world = (
            "from worlds.AutoWorld import World\n"
            "from worlds.LauncherComponents import Component, components\n"
            "def launch(*args):\n"
            "    pass\n"
            "components.append(Component('BKBT Test Side Client', func=launch))\n"
            "class SideWorld(World):\n"
            "    game = 'BKBT Test Side'\n"
            "    item_name_to_id = {}\n"
            "    location_name_to_id = {}\n")
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / f"{side}.py").write_text(side_world, encoding="utf-8")
            package = Path(root) / carried
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "__world__.py").write_text(own_world, encoding="utf-8")
            (package / "__world__.json").write_text(
                json.dumps({"game": "BKBT Test Carried", "world_version": "0.0.1"}), encoding="utf-8")
            sys.path.insert(0, root)
            try:
                importlib.import_module(carried)
                world = carry(carried, "unused", "BKBT Test Carried")
                self.assertEqual(world.game, "BKBT Test Carried")
                self.assertIs(AutoWorldRegister.world_types.get("BKBT Test Side"), sys.modules[side].SideWorld)
                self.assertNotIn("BKBT Test Carried", AutoWorldRegister.world_types)
                names = [component.display_name for component in LauncherComponents.components]
                self.assertIn("BKBT Test Side Client", names)
                self.assertNotIn("BKBT Test Carried Client", names)
            finally:
                sys.path.remove(root)
                AutoWorldRegister.world_types.pop("BKBT Test Side", None)
                LauncherComponents.components[:] = [component for component in LauncherComponents.components
                                                    if not component.display_name.startswith("BKBT Test ")]
                for module in [m for m in sys.modules if m.split(".")[0] in (side, carried)]:
                    del sys.modules[module]

    def test_only_through_the_carried_packages(self):
        """No module of the world imports worlds.banjo_kazooie or worlds.banjo_tooie: an apworld installed alone has
        neither, or another version."""
        pattern = re.compile(r"^\s*(from|import)\s+worlds\.banjo_(kazooie|tooie)\b", re.M)
        for path in WORLD.rglob("*.py"):
            if "test" in path.relative_to(WORLD).parts:
                continue
            self.assertFalse(pattern.findall(path.read_text(encoding="utf-8")), path)
