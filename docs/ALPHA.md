# Banjo-Kazooie & Tooie Archipelago: alpha guide

Thanks for testing this! It's Banjo-Kazooie and Banjo-Tooie in one Archipelago slot. You play both games on one ROM,
and the entrance to Gruntilda's Lair in Tooie's Spiral Mountain takes you into Banjo-Kazooie's Lair. There's also a
Banjo-Kazooie world by itself, if you only want to play BK.

This is an alpha, so stuff will break. That's kind of the point, so please report it when it does (there's a section
on that at the bottom).

## What you need

- Archipelago 0.6.7 or newer. If you don't have it, get the Windows installer from the
  [Archipelago releases page](https://github.com/ArchipelagoMW/Archipelago/releases).
- The alpha's files:
  - `banjo_kazooie_tooie.apworld`, both games in one slot
  - `banjo_kazooie.apworld`, BK by itself
  - `Banjo-Kazooie & Tooie - Alpha.yaml` and `Banjo-Kazooie - Alpha.yaml`, the settings

  Each apworld works by itself, so you only need the one for the slot you're playing. The combined one brings its
  own copy of Banjo-Tooie AP (jjjj12212's V4.13.1), so you don't need the regular Banjo-Tooie world for it. If you
  already have Banjo-Tooie AP installed, any version, you can leave it, they don't get in each other's way.
- Your own ROMs: Banjo-Kazooie (USA) version 1.0, and Banjo-Tooie (USA) for the combined slot. `.z64`, `.v64` and
  `.n64` all work. You don't patch them yourself, the client does that.
- Project64 3.0.1 or ares v148. Those are the two it's been tested on, both with their default settings. Other
  emulators might work, but nobody's tried them yet.

## Installing

1. Install Archipelago if you haven't already.
2. Double-click the `.apworld` file for your slot (or both, if you want both). The Archipelago Launcher opens and
   installs it (you can also open the Launcher and pick "Install APWorld").
3. Close the Launcher and open it again. You should see "Banjo-Kazooie & Tooie Client" or "Banjo-Kazooie Client"
   (or both) in the list.

If you're the one hosting, install both apworlds, so you can generate either kind of slot.

## Your yaml

A yaml is the file with your settings in it. The alpha's settings are already set up, so all you have to do is put
your name in.

1. Open `Banjo-Kazooie & Tooie - Alpha.yaml` in a text editor (Notepad is fine). Use `Banjo-Kazooie - Alpha.yaml`
   instead if you're playing BK by itself.
2. Near the top, change `name: Player{number}` to your name, like `name: Banjo`. 16 characters max. This is also
   your slot name when you connect, so remember it.
3. Send it to whoever's hosting.

You can change other settings if you want, but it's best to leave them alone for the alpha so everyone's testing
the same thing. If you do change one, each setting lists its choices with a number next to them, and the one with
50 is what you get. Move the 50 to the choice you want and put a 0 on the old one.

The alpha's settings for the combined slot:

- The goal is both games: you're done when you've beaten Hag 1 in Tooie and Gruntilda in BK. It's a long one.
- You start with BK's Spiral Mountain moves (Climb, Swim, Feathery Flap, Flap Flip, Rat-a-tat Rap, Beak Barge,
  Roll, Claw Swipe and Tall Jump). The other nine BK moves are out in the multiworld. Those nine are also enough to
  get through the door into BK right away.
- Tooie's moves are shuffled, like normal Tooie AP.
- Tooie's note nests are checks.
- No entrance shuffle, every world is behind its own door.

For BK by itself it's the same moves deal (Spiral Mountain's nine to start, the rest shuffled), and the goal is
beating Gruntilda.

## Playing the combined slot

1. Open the Launcher and click "Banjo-Kazooie & Tooie Client".
2. The first time, it asks for your Banjo-Kazooie ROM, then your Banjo-Tooie ROM, and makes
   `Banjo-Kazooie & Tooie AP 0.1.0.z64` in your Archipelago folder. It takes about 15 seconds and the client tells
   you where it put it. It only does this again when a new version needs a new ROM.
3. Type the server address the host gives you into the bar at the top of the client, hit Connect, and enter your
   slot name.
4. Open `Banjo-Kazooie & Tooie AP 0.1.0.z64` in your emulator. The client finds the emulator by itself.
5. Tooie comes up first. Start a new file (every seed needs its own new file).
6. To get to BK, walk into the entrance of Gruntilda's Lair in Tooie's Spiral Mountain. The screen goes black for a
   few seconds while it saves and switches games, that's normal. You come out in BK's Lair. To go back, walk out of
   BK's Lair the way you'd leave for Spiral Mountain, and you're back in Tooie outside the Lair.

Keep the client connected the whole time you play. Your items come in through it, and when you switch games the
black screen waits for it (after ten seconds without it, it gives up and shows you a file select).

If you want, `/autostart` in the client picks your emulator once and then opens it with the ROM for you.

## Playing BK by itself

Same idea with the Banjo-Kazooie Client:

1. Open the Launcher and click "Banjo-Kazooie Client". The first time it asks for your BK ROM and makes
   `Banjo-Kazooie AP 0.1.0.z64`.
2. Connect and enter your slot name.
3. Open the ROM in your emulator and start a new game on BK's file select. It won't start a game until the client
   is connected, and a file only loads with the seed it was started with.

## What's different from the normal games

- Moves are shared in the combined slot. Learn a move once and you have it in both games. BK's moves use Tooie's
  names when they're the same move: Swim is Dive, Feathery Flap is Flutter, Flight is Flight Pad, Turbo Talon Trot
  is Turbo Trainers, Wading Boots is Stilt Stride, Eggs is Third Person Egg Shooting, Claw Swipe is Ground Rat-a-tat
  Rap and Rat-a-tat Rap is Air Rat-a-tat Rap. Shock Spring Jump is the only one that stays BK's.
- BK's Jiggies, Mumbo Tokens and Empty Honeycombs are called Lair Jiggy, Lair Mumbo Token and Lair Empty Honeycomb,
  so you can tell them apart from Tooie's. Picking one up in BK is a check, and the ones you can spend come from the
  items you get.
- BK's Spiral Mountain isn't in the combined slot, BK starts you in the Lair. Tooie's ruined Lair isn't in either,
  since that's where the door is.
- Cheato is in King Jingaling's zombified throne room in Jinjo Village (go through the palace door, he's on the
  right as you come in). 5, 10, 15, 20 and 25 Cheato Pages get you his five rewards.
- BK's note doors open when their item shows up (Note Door 2 and so on), just walk up to the door. Having enough
  notes for a door is a check.
- Notes you pick up in BK stay picked up, even after you leave the level, so you never grab them twice.
- Mumbo's forms come off when you go into or out of a BK world. To get one back in the Lair, stand right next to
  that world's door and press D-pad left (once you've paid Mumbo for it). Inside a world where you've paid Mumbo,
  D-pad left changes you anywhere.
- No game over in BK, your lives are infinite.
- Save and Quit in BK takes you back to Tooie's title screen.
- Egg Nest and Feather Nest items refill whichever game you're playing when they show up.

A few client commands that help: `/game` says which game is running, `/goal` shows which of the two goals you've
finished, and `/bk` shows what the client is giving BK.

## Known issues and stuff that hasn't been tested

- It's only been played on Project64 3.0.1 and ares v148, on Windows. BizHawk, RMG, RetroArch and the rest might
  work, but nobody's tried them. No Everdrive or real console either, even though regular Banjo-Tooie AP supports
  them.
- Savestates haven't been tested at all, especially across the door, so it's best to stay away from them.
- Resetting the emulator while you're in BK isn't well tested. Use Save and Quit instead.
- Getting your Mumbo form back at a Lair door needs you to stand really close to the door, closer than you'd think.
- Some flight pads and shock spring pads in BK (from Clanker's Cavern on) work even if you don't have the move yet.
  That's how the original game is. It won't break anything, you're just ahead of the logic.
- BK by itself fails to generate once in a while (about 1 in 200 seeds with these settings). If that happens, the
  host just generates again.

Banjo-Tooie AP's [setup guide](https://github.com/jjjj12212/Archipelago-BanjoTooie/blob/V4.13.1/worlds/banjo_tooie/docs/setup_en.md)
has some emulator tips that apply here too, like lowering Counter Factor in Project64 if it lags.

## If something breaks

Report it! Send as much of this as you can:

- What you were doing and where (which game, which level).
- Which emulator.
- The client's log. It's in your Archipelago folder under `logs`, the newest `BanjoKazooieTooieClient_...txt` (or
  `BanjoKazooieClient_...txt` for BK by itself).
- A screenshot or a clip if something looks wrong.

If the game freezes, it's fine to close the emulator and start again from your last save. The server keeps every
check you already sent, and the client gives you your items again.
