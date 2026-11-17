# Setup Guide for Banjo-Kazooie & Tooie Archipelago

Both games in one slot, played in one cartridge image: the entrance to Gruntilda's Lair in Banjo-Tooie's Spiral
Mountain leads into Banjo-Kazooie's Lair, and its way out leads back. Playable for testing, not yet released.

## What you need

- Your own Banjo-Kazooie (USA) ROM, version 1.0, and Banjo-Tooie (USA) ROM (`.z64`, `.v64` or `.n64`). The client
  makes the image you play from them.
- The Banjo-Kazooie & Tooie world installed. It needs no other world: it carries the two it is built on, the
  Banjo-Kazooie world of the same release and jjjj12212's Banjo-Tooie world V4.13.1 (MIT), and registers neither,
  so either can be installed beside it, the Banjo-Tooie world at any version.
- Project64 3.0.1 or ares v148, with the Expansion Pak.
- The Banjo-Kazooie & Tooie Client, from the Archipelago Launcher. It reaches the emulator with the EmuLoader that
  the Banjo-Kazooie apworld carries.

## Making the image

The first time the Banjo-Kazooie & Tooie Client starts, it asks for your two ROMs (or takes the ones the
Banjo-Kazooie and Banjo-Tooie worlds' settings already name) and makes `Banjo-Kazooie & Tooie AP <version>.z64` from
them, in about fifteen seconds; its log says where (Archipelago's folder, unless you set another with
`/patch_path`). It makes it again only when a new version of the world needs a new image. `/patch` makes it if it is
missing, `/bk_rom_path` and `/tooie_rom_path` change which ROMs it is made from, and `/autostart` starts your
emulator with it.

## Playing

1. Connect the Banjo-Kazooie & Tooie Client to the server (`/connect <address>`) and enter your slot name.
2. Start `Banjo-Kazooie & Tooie AP <version>.z64` in the emulator. Banjo-Tooie comes up first: start a file.
3. In Spiral Mountain, walk into the entrance of Gruntilda's Lair: the console saves and switches to Banjo-Kazooie,
   behind a black screen, and starts your Banjo-Kazooie game in its Lair. Leaving the Lair takes you back.

Cheato, whose ruined Lair the door replaces, is in King Jingaling's zombified throne room in Jinjo Village, to the right as
you come in. Bring him Cheato Pages there: 5, 10, 15, 20 and 25 pages give his five rewards.

`/game` in the client shows which game runs, `/goal` the slot's goal, and `/bk` what Banjo-Kazooie gets.
