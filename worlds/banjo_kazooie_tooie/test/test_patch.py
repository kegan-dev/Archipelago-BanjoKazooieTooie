"""The dual-boot image from the player's retail ROMs (assets/, BKBTClient.image_target, worlds/banjo_kazooie/patch/).
The round trip needs both retail ROMs in the repository's roms/ (or BKBT_ROMS) and is skipped without them."""

import hashlib
import json
import os
import pkgutil
import unittest
from pathlib import Path

from worlds.banjo_kazooie_tooie.bk.patch import make

from .. import BKBTClient

ROMS = Path(os.environ.get("BKBT_ROMS") or Path(__file__).resolve().parents[3] / "roms")
RETAIL_BK = ROMS / "Banjo-Kazooie (USA).z64"
RETAIL_TOOIE = ROMS / "Banjo-Tooie (USA).z64"


def asset(name: str) -> bytes:
    return pkgutil.get_data("worlds.banjo_kazooie_tooie", f"assets/{name}")


class TestImagePatchFiles(unittest.TestCase):
    def setUp(self):
        self.info = json.loads(asset("image-patch.json"))

    def test_the_image_is_named_ap(self):
        """The image says it is AP, not the stock Tooie AP ROM's "RANDO TOOIE" (2026-11-12; tools/rom_name.py)."""
        self.assertEqual(self.info["header_name"], "BK & Tooie AP")

    def test_description_names_its_files(self):
        self.assertEqual(self.info["format"], 1)
        self.assertEqual(hashlib.sha1(asset("tooie.bsdiff4")).hexdigest(), self.info["tooie"]["patch_sha1"])
        self.assertEqual(hashlib.sha1(asset("bk-payload.bin")).hexdigest(), self.info["payload_sha1"])
        self.assertEqual(hashlib.sha1(asset("bkbt-info.bin")).hexdigest(), self.info["info_block_sha1"])
        self.assertEqual(self.info["tooie"]["retail_md5"], make.TOOIE_RETAIL_MD5)

    def test_made_with_the_bk_worlds_patch(self):
        bk = json.loads(pkgutil.get_data("worlds.banjo_kazooie_tooie.bk", "assets/bk-patch.json"))
        self.assertEqual(self.info["bk_rom_sha1"], bk["rom_sha1"],
                         "the two worlds' patches come from one build (tools/make_patches.py)")

    def test_the_info_block_is_the_tools(self):
        block = asset("bkbt-info.bin")
        self.assertEqual(block[:8], b"BKBTINFO")
        info = json.loads(block[12:12 + int.from_bytes(block[8:12], "big")])
        self.assertEqual(info["contract"], 5)
        self.assertEqual(info["rom_sha1"], self.info["bk_rom_sha1"])

    def test_the_payload_is_the_launcher(self):
        payload = asset("bk-payload.bin")
        self.assertLess(len(payload), 0x10000)

    def test_target(self):
        target = BKBTClient.image_target("9.9.9")
        self.assertEqual(target.file_name, "Banjo-Kazooie & Tooie AP 9.9.9.z64")
        self.assertEqual(target.sha1, self.info["image_sha1"])
        self.assertEqual([source.key for source in target.sources], ["bk_rom_path", "tooie_rom_path"])
        self.assertEqual([key for source in target.sources for _group, key in source.fallbacks],
                         ["rom_path", "rom_path"])


@unittest.skipUnless(RETAIL_BK.is_file() and RETAIL_TOOIE.is_file(), f"no retail ROMs in {ROMS}")
class TestImageFromTheRetailRoms(unittest.TestCase):
    def test_the_patch_gives_the_builds_image(self):
        target = BKBTClient.image_target("0")
        roms = {"bk_rom_path": RETAIL_BK.read_bytes(), "tooie_rom_path": RETAIL_TOOIE.read_bytes()}
        image = target.make(roms)
        self.assertEqual(len(image), make.IMAGE_SIZE)
        self.assertEqual(hashlib.sha1(image).hexdigest(), target.sha1)

    def test_the_roms_are_not_swapped(self):
        target = BKBTClient.image_target("0")
        with self.assertRaises(make.WrongRom):
            target.make({"bk_rom_path": RETAIL_TOOIE.read_bytes(), "tooie_rom_path": RETAIL_BK.read_bytes()})
