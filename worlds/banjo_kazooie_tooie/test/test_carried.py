"""The two worlds the combined world carries (carried.py): run as its subpackages bk and bt, never registered as
worlds, and the only way the combined world reaches their code, so that its apworld works installed alone."""

import re
from pathlib import Path
from unittest import TestCase

from worlds import LauncherComponents
from worlds.AutoWorld import AutoWorldRegister

from .. import BanjoKazooieTooieWorld, bk, bt

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

    def test_only_through_the_carried_packages(self):
        """No module of the world imports worlds.banjo_kazooie or worlds.banjo_tooie: an apworld installed alone has
        neither, or another version."""
        pattern = re.compile(r"^\s*(from|import)\s+worlds\.banjo_(kazooie|tooie)\b", re.M)
        for path in WORLD.rglob("*.py"):
            if "test" in path.relative_to(WORLD).parts:
                continue
            self.assertFalse(pattern.findall(path.read_text(encoding="utf-8")), path)
