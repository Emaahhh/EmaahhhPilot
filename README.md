<p align="center"><img src="assets/emaahhhpilot_logo.png" width="128" alt="EmaahhhPilot logo"></p>

# EmaahhhPilot

**EmaahhhPilot** is a renamed version of **AresPilot** by **AresEmu**, a Clash of Clans autopilot built for the **new Clash of
Clans UI (October 2026)**.

It is **based on [BasePilot](https://github.com/efebolukbasi/BasePilot) by Efe Bolukbasi**
(MIT license). The original project was written for the previous UI; most of its screen
detection, the builder menu and the wall upgrade flow stopped working after the update.
EmaahhhPilot rewrites those parts, adds a new interface and new features on top (Builder Base
Trophy mode, Baby Dragon edge deploy, ...).

Credit for the original design and code goes to the BasePilot author. EmaahhhPilot is not an
official BasePilot release and is not supported by them.

> ⚠️ **Personal educational project — not a cheating tool, not endorsed by the author for
> real play.** EmaahhhPilot is a study in computer vision, OCR and desktop UI automation. The
> author **does not condone cheating** or any violation of Supercell's Terms of Service, and
> does not encourage anyone to use it on a real account. It is **not affiliated with,
> endorsed by or connected to Supercell** in any way. Read the [Disclaimer](#disclaimer).

Technically, it is a Windows desktop app that works on **Clash of Clans on Google Play
Games (PC)** through screen capture, image recognition and mouse clicks only. No memory
reading, no packet manipulation, no modified client, and **no network access** of its own:
everything it stores (settings, logs) stays on the local PC.

---

## Feature status

| Status | Meaning |
|---|---|
| ✅ Working | Implemented and verified against the new UI |
| 🧪 Not fully tested | Implemented, but only briefly or not yet tested live |
| 🚧 Work in progress | Being rewritten for the new UI, not usable yet |
| 📋 Planned | Not started yet, to be released |

### ✅ Working (new UI, 16:9)

- **New UI support (16:9 profile).** All Home Village templates re-cropped at 2560×1440
  for the October 2026 UI.
- **New interface.** Dark navy and cream "liquid glass" desktop app at 120 fps: sidebar with
  icons, Start (green) / Stop (red) in the page header, glass switches and segmented
  controls. Every option and button has a description (what Off / Dry run / Maxer / Rusher,
  each army and each Builder Base mode really do) and a tooltip.
- **History, logs and notifications.** History page (totals, loot per hour, yield per army),
  log filters and search, Windows notifications, notification-area icon, F12 to stop,
  scheduled start, live game preview.
- **Auto-collect resources.** Taps the collector bubbles every 4 minutes while farming.
- **Alchemist (Helper Hut).** When the Alchemist is free (the hand bubble above the hut, or
  the "Convert Resources" button in the hut's bar), converts what is selected in its window
  and confirms. Set the conversion by hand once: the game remembers it. Spends the source
  resource; off by default.
- **Skip poor bases.** Reads the scouting screen's Available Loot and presses Next until gold +
  elixir reach the minimum you set (Settings → Attack), at most 8 times per attack.
- **Clan Castle treasury.** Collects the Treasury every 30 minutes; the Castle's look is learned
  once with Settings → Clan Castle → Learn Clan Castle.
- **Matchmaking clouds.** After Attack! the bot waits through the white cloud screen (it can
  last minutes) without tapping anything.
- **Windowed game.** A game window with a title bar is cropped to its client area, so the
  16:9 check and the click positions stay correct.
- **Builder Base on the new UI.** Village detection, boat, Find Now, attack, battle end,
  Return Home and the Star Bonus popup use templates re-cropped for the
  new UI. Baby Dragon army with the Battle Machine / Flying Machine.
- **Builder Base wall upgrades.** Same flow as the Home Village (Build panel + Upgrade
  More), with its own threshold in millions (one decimal, e.g. 1.3M).
- **Builder Base loot modes.** *Gold* (end the battle at 2 stars), *Both* (at 1 star),
  *Elixir* (surrender right after deploying).
- **Auto upgrade via the new Build panel ("Buildings & Heroes").** Opens the panel with
  the Build button, scans the whole list, reads names and costs, and confirms upgrades.
  Modes: **Maxer**, **Rusher**, **Dry run** (logs only, clicks nothing).
- **Wall upgrades via the Build panel.** Triggered by the full-storage icon. Finds the
  Wall row, picks the cheapest payable wall level, uses **Upgrade More** to batch walls
  in the multi-select bar, pays with gold or elixir and confirms the "Upgrade Walls"
  popup. Up to two rounds per check; the second round only runs if a wall level is still
  payable after re-reading the HUD. Wall prices are re-read every time (never cached to
  disk). The number of walls recorded is taken from the actual HUD drop (cost ÷ price per
  wall), so the summary stays correct even if the batch counter is off.
- **New price and HUD reader.** Prices and gold/elixir/dark elixir amounts are read with a
  dedicated digit-glyph matcher instead of Tesseract, with thousands-grouping checks and
  red-text detection (unaffordable prices).
- **Both confirm dialog layouts.** Works with and without the Gold Pass (discounted price
  layout vs yellow banner layout).
- **Safe popup handling.** Gem-spend dialogs, panels and unknown popups are closed via their
  X / Cancel buttons — never a blind Okay/Confirm.
- **End-of-run summary.** When a run ends, a summary window and log entry show run time,
  number of attacks, farmed gold/elixir/dark elixir, and walls upgraded grouped by level
  with their cost.
- **Robust loot tracker.** HUD amounts are only accepted when two frames agree. A sudden
  "collapse" (e.g. 9,000,000 read as 6) triggers a re-read, and if it persists the previous
  value is held for one cycle instead of counting a fake loss or a fake gain. Real spends
  (walls, upgrades) are not counted as farmed loot.
- **Varied attack patterns.** Heroes are dropped at random points of the perimeter and
  hero abilities fire 0–10 s after each hero is deployed. Troop placement
  (Valkyrie, Super Minion, Sneaky Goblin) was reworked:
  - troops follow random waypoints inside a **3.5-tile band** along each side, joined by a
    half-smoothed curve (a gentle, irregular wave rather than a perfect spline);
  - drops land **between tiles** too, not only on tile centres (irregular spacing of
    0.2–0.45 tiles);
  - drag speed changes **±30% per hop**, and each side takes ±10% of its share of time;
  - **corners are crossed faster** (≈1.4× with its own ±30% variation each time) to avoid
    big troop clumps where two sides meet;
  - **Valkyrie** deploy lasts **7 s**; **Super Minion** deploy lasts a new random
    **2.8–4.2 s** every attack.
- **Full zoom-out before attacking**, so the first attack after the menus is not zoomed in.
- **Faster template matching.** Coarse-to-fine matching with a template cache
  (~4× faster per call).
- **Reliable list scrolling.** The Build panel list is checked to have actually moved and
  stopped before it is read.
- **Settings auto-save** on every change; Duration field fixed.
- **EmaahhhPilot data folder.** Settings, logs and debug frames live in
  `%LOCALAPPDATA%\EmaahhhPilot`; on the first start, settings from an older `BasePilot`
  install are copied over automatically (the old folder is left untouched).
- **Separate test logs.** Unit tests write to `%LOCALAPPDATA%\EmaahhhPilot\test_logs`
  (see `EMAAHHHPILOT_LOG_DIR`) so they never pollute the real run log.

### 🧪 Implemented but not fully tested

- **Builder Base Trophy mode.** Never ends the battle early: plays the first village to
  100%, then attacks the second village with the surviving dragons and the fresh cards,
  and waits for the battle to finish before Return Home.
- **Baby Dragon edge deploy (Builder Base, both stages).** Full zoom-out, then the bot reads
  the red "no deploy" border around the village and drops one dragon per zone in six zones
  around it, a random **2–8 tiles** outside the border, all within ~3 s. Zones never land
  off the playable floor, on the HUD, on the troop bar or on the buttons: a blocked zone
  comes closer to the border or slides along it. The machine is dropped with one of the
  dragons; all abilities fire together after a random 10–25 s. In the second village the
  bot first taps a building with a dragon selected to make the game show the border.
- **Missed-drop retries.** Dragons the game did not take (their card still shows the troop
  switch button) are dropped again closer to the border, up to 5 rounds.
- **Last run remembered.** Village, army, Builder Base mode, duration and all switches of
  the Run page come back as they were at the last Start.
- **Rusher mode** on the new Build panel.
- **Timed event "Pick a Reward!" overlay** (33/66/100% damage): the bot now clicks the
  right-hand card (gold or grey, whatever it contains) instead of waiting ~12 s for the
  countdown. When the event is over and the overlay never shows up, attacks run as before.
  See [docs/event-rewards.md](docs/event-rewards.md).
- **Sneaky Goblin** with the new troop placement (shares the Valkyrie/Super Minion code,
  not run live yet).
- **Earthquake "Random Placement"** after the fix.
- **Gem dialog recovery** in rare cases (seen once during a large elixir batch, cause not
  confirmed).
- **Faster Stop.** Waits between clicks and mouse-wheel steps end as soon as Stop is
  pressed, no click is sent after Stop, and hero / earthquake drops stop mid-way.
  A single OCR pass still finishes before the bot stops.
- **Stuck-screen guard.** When the Attack button is not reached 5 cycles in a row, a
  timed run stops with a message (run until maxed waits 5 minutes and tries again)
  instead of retrying the same recovery forever.
- **Wall batch counter** now counts the wall selected by the row click too.
- **Run until maxed / idling** logic with the new panel (inherited from upstream, not
  re-verified over long sessions).

### 🚧 Work in progress

- **Faster wall rounds.** Remember where the Wall row is during a run (not on disk) and
  start the scan from there, cutting most of the list scrolling (~+10% attacks/h
  expected with walls on).
- **Player list / multi-run.** The Players page shows "Work in progress" while the
  player list and multi-run are reworked.
- **Night Witches** (Builder Base): listed in the UI, not implemented yet.

### 📋 Planned / to be released

- **Laboratory chip on the new UI** (lab status in Live status, max 2 labs).
- **Multi-account** support (the Players page stays "work in progress": the account-switch
  screens do not match the current game UI yet).
- **Skipping low-loot bases** (needs a reading of the loot shown while searching).
- **Night Witches** and the **16:10 profile** (both need real captures from the game).

Done since: **scheduled start**, **auto-collect resources**, **history page**, **log filters**,
**game preview**, **notifications**, **notification-area icon** and the **F12 stop key** —
see the [CHANGELOG](CHANGELOG.md).
- **16:10 profile** update for the new UI (only the 16:9 profile is updated for now).

Not automated (as upstream): starting laboratory research and Pet House upgrades.

## Safety rails

Automation that spends resources has to be careful, so EmaahhhPilot:

- Never confirms a purchase whose price shows red (unaffordable → gem-spend risk).
- Checks that the confirm dialog matches the picked row (name, price and resource) before
  clicking Confirm.
- Verifies every upgrade actually started by checking the builder counter afterwards.
- Closes unknown dialogs via their close button or empty ground — never a blind "Okay".
- Keeps a gold buffer so matchmaking entry fees are never spent on walls.
- Saves screenshots of anything it couldn't verify to `%LOCALAPPDATA%\EmaahhhPilot\debug\`
  instead of retrying blindly.

## Download

Builds are on the
[Releases page](https://github.com/Emaahhh/EmaahhhPilot/releases) — a single file, no
install needed (Tesseract is bundled). Windows SmartScreen may warn about an unsigned exe.
They are provided for studying the code in action, **not as a tool to play the game**:
read the [Disclaimer](#disclaimer) first. On its first start the app shows the same
disclaimer and runs only after you accept it.
What changed in each version: [CHANGELOG](CHANGELOG.md).

## Setup

Follow the steps in order. Each one says what to do and how to check it worked.

### 1. What you need

- A **Windows 10 or 11** PC.
- A **16:9 monitor** (1920×1080, 2560×1440, 3840×2160, ...). An ultrawide or 16:10 monitor
  also works, with one extra step ([step 5](#5-ultrawide-or-1610-monitor-only)).
  EmaahhhPilot is tested at **2560×1440**; other 16:9 sizes are scaled from it.
- **Clash of Clans on Google Play Games for PC**, with the October 2026 UI.
- **Python 3.11 or newer** (tested with 3.13) and **Tesseract OCR 5**: both are free, and
  step 3 explains how to install them.

### 2. Prepare the game

1. Install [Google Play Games for PC](https://play.google.com/googleplaygames), sign in and
   install Clash of Clans from it.
2. **Set the game language to English**: in Clash of Clans open *Settings → Language →
   English*. EmaahhhPilot recognises buttons by their English text (Attack, Find Now, Surrender,
   Okay, ...) and reads English names in the Build panel. With any other language it finds
   almost nothing.
3. Google Play Games draws the game with the shape of your monitor, decided **when the game
   starts**. On a 16:9 monitor there is nothing to do. On an ultrawide or 16:10 monitor, do
   [step 5](#5-ultrawide-or-1610-monitor-only) before playing.
4. While the bot runs, keep the game window open and **do not minimise it**: a minimised
   window cannot be captured. EmaahhhPilot sends its clicks straight to the game window, so your
   mouse pointer is not moved.

### 3. Install Python and Tesseract

1. **Python:** download the installer from [python.org](https://www.python.org/downloads/windows/).
   On the first installer screen, tick **"Add python.exe to PATH"**, then click *Install Now*.
2. **Tesseract:** open *PowerShell* and run:

   ```
   winget install UB-Mannheim.TesseractOCR
   ```

   Or use the installer from the [UB-Mannheim page](https://github.com/UB-Mannheim/tesseract/wiki).
   Keep the default folder, `C:\Program Files\Tesseract-OCR`, where EmaahhhPilot looks for it.
   If you install it somewhere else, set the `TESSERACT_CMD` environment variable to the
   full path of `tesseract.exe`.
3. **Check:** close and reopen PowerShell, then run `python --version`. It must print
   `Python 3.11` or newer.

### 4. Download and start EmaahhhPilot

1. Download the code: on the [repository page](https://github.com/AresEmu/AresPilot) click
   *Code → Download ZIP* and extract it (for example to `C:\EmaahhhPilot`), or with Git:

   ```
   git clone https://github.com/AresEmu/AresPilot.git
   ```

2. Open PowerShell **in that folder** (in File Explorer: open the folder, type `powershell`
   in the address bar and press Enter) and install the dependencies, once:

   ```
   pip install -r requirements.txt
   ```

3. Start EmaahhhPilot:

   ```
   python main.py
   ```

4. On the first start EmaahhhPilot shows the disclaimer: read it and accept it, or the app
   closes.

From then on, starting EmaahhhPilot only needs step 3, from the same folder. Settings and logs
are stored in `%LOCALAPPDATA%\EmaahhhPilot`.

### 5. Ultrawide or 16:10 monitor only

Skip this step on a 16:9 monitor.

1. In EmaahhhPilot open **Settings** and click **Switch display to 16:9**. Your screen changes
   resolution.
2. **Fully close** Clash of Clans (close its Google Play Games window), then open it again.
3. Click **Restore my display**. The screen goes back to normal, and the game, already
   running, stays 16:9.
4. **Check:** in the window list of Settings select the Clash of Clans window and press
   **Test**. The result must show `(16:9)` and `Surface OK to use.`

Repeat this step every time you restart the game.

### 6. Prepare your army in the game

**Home Village.** Choose one of the four strategies of the Run page and bring that army:

| Strategy | Main troop | Extra setup |
|---|---|---|
| **Valkyries** | Valkyries | Save the army as a recipe whose first troop is the Valkyrie, and keep it at the top of *Saved Recipes*. If the army screen shows no Valkyries, the bot loads that recipe before attacking. |
| **Sneaky Goblins** | Sneaky Goblins | — |
| **Super Minions** | Super Minions | — |
| **Edrags** | 12 Electro Dragons | — |

With every strategy the bot also uses, when they are in the army:
- **Heroes:** Barbarian King, Archer Queen, Grand Warden, Royal Champion, Minion Prince and
  Dragon Duke, with their abilities;
- **Siege machine:** Log Launcher or Siege Barracks;
- **Super Dragon;**
- **Earthquake spells.**

Other troops and spells are not deployed. Keep the game's default deploy bar order (do not
rearrange the slots). [docs/armies.md](docs/armies.md) explains how each army is dropped.

**Builder Base.** Fill every camp with **Baby Dragons** and bring the **Battle Machine** or the
**Flying Machine**. Other troops are not supported: after 4 battles in a row without Baby
Dragons a timed run stops.

### 7. Start a run

Leave the game on the village screen. On the **Run** page of EmaahhhPilot:

1. **Village:** *Home Village* or *Builder Base*. If the game is in the other village, the bot
   takes the boat by itself.
2. **Attack Strategy:** the army you prepared in step 6.
3. **Schedule:**
   - **Duration** in minutes; or
   - **Run until maxed:** no time limit, it runs until you press Stop. With full storages and
     nothing to upgrade it waits and checks again every 5 minutes; or
   - **Star Bonus:** stops when the daily Star Bonus is claimed (at most 15 minutes).
4. **Modes (Home Village):**
   - **Auto upgrade:** *Off*, *Maxer* (cheapest affordable upgrade, never the Town Hall),
     *Rusher* (Town Hall first) or *Dry run* (only writes in the log what it would upgrade).
   - **Upgrade walls:** spends gold and elixir on walls. The threshold that triggers it is in
     *Settings*, together with the builders kept free for walls.
   - **Ranked attack fill:** uses your **ranked** attacks. Leave it off unless you want that.
5. **Modes (Builder Base):** *Prioritise* Gold, Both, Elixir or Trophy (the **?** button
   explains each one) and *Upgrade walls* (threshold in *Settings*).
6. Press **Start** at the top of the page. **Stop** ends the run; a summary shows run time,
   attacks, loot farmed and walls upgraded.

The **Logs** page shows what the bot is doing while it runs.

### Common problems

- **"Clash of Clans window not found"**: open the game first. If it is open, go to
  **Settings**, select the Clash of Clans window in the list, press **Test**, then **Use this
  window**.
- **Test does not show `(16:9)`**: the game was started with a different screen shape. Do
  [step 5](#5-ultrawide-or-1610-monitor-only).
- **Test says "Could not read the window size"**: the game window is minimised. Restore it.
- **The log is full of `... .png not found`**: the game is not in English, not 16:9, or not
  on the October 2026 UI (steps 2 and 5).
- **The log says "Tesseract not configured"**: Tesseract is not installed in
  `C:\Program Files\Tesseract-OCR` and `TESSERACT_CMD` is not set (step 3).
- **"Troops not found 4 times in a row — stopping"**: the army in the game does not match
  the strategy chosen on the Run page (step 6).
- The log file is `%LOCALAPPDATA%\EmaahhhPilot\emaahhhpilot.log`. The **Open in Explorer** button
  on the Logs page opens its folder.

### Changing the logo

```
python tools/set_logo.py path\to\image.png --crop --round 22 --preview preview.png
```

Writes `assets/emaahhhpilot_logo.png` (512×512) and `assets/emaahhhpilot_logo.ico`
(16–256 px). A non-square image is centred on a transparent square; `--crop`
centre-crops it instead, `--round 22` rounds the corners like an app icon. The current
logo's original is `assets/emaahhhpilot_logo_source.png`. Rebuild the exe afterwards to see the new icon on the exe file.

### Building the exe (optional)

The exe is a single file that runs without Python or Tesseract installed.

1. Fill a `tesseract_bundle` folder inside the EmaahhhPilot folder from
   `C:\Program Files\Tesseract-OCR`: `tesseract.exe`, all the `*.dll` files, and in
   `tesseract_bundle\tessdata` the files `eng.traineddata`, `osd.traineddata` and the
   `configs` / `tessconfigs` folders. The folder is not in the repository (about 175 MB).
2. In PowerShell, in the EmaahhhPilot folder:

   ```
   pip install pyinstaller
   python tools/build_exe.py
   ```

3. The exe is `EmaahhhPilot.exe` in the EmaahhhPilot folder itself. Close the app before
   building again: a running exe cannot be replaced.

## License

MIT — see [LICENSE](LICENSE).

- Original BasePilot: © 2026 Efe Bolukbasi.
- AresPilot (October 2026 UI update, new interface and all later changes): © 2026 AresEmu,
  released under the same MIT license.

If you reuse this code, keep both copyright notices, as the MIT license requires. Tesseract, bundled into the exe, ships
under the Apache 2.0 license.

## Disclaimer

**Educational purpose only.** EmaahhhPilot is a personal project, made to learn and
experiment with computer vision, OCR and desktop UI automation on an animated, complex
target. It is shared as source code for that purpose only.

**The author does not condone cheating.** Automating Clash of Clans violates Supercell's
Terms of Service and can get an account permanently banned. The author does not approve
of, encourage or support using EmaahhhPilot — or any other bot — to play the game, gain an
advantage over other players, or break the Terms of Service, for any reason. If you choose
to run it anyway, you do so on your own initiative, at your own risk, and you alone are
responsible for the consequences. **No warranty of any kind** (see [LICENSE](LICENSE)).

**No affiliation with Supercell.** EmaahhhPilot is not affiliated with, endorsed, sponsored or
approved by, or in any way connected to Supercell Oy. Clash of Clans, its name, logos,
characters and in-game graphics are trademarks and copyrighted material of Supercell Oy.
The small image crops in `templates/` are screenshots of the game's interface, used only
so the software can recognise what is on screen; all rights to them remain with Supercell.

**No support for gameplay use.** The author does not provide help for using EmaahhhPilot on
an account, and issues or requests about evading detection, bans or anti-cheat systems
will not be answered or accepted.

**Removal on request.** If Supercell or any rights holder has a concern about this
repository, please open an issue or contact the author through GitHub and the content will
be reviewed and removed where appropriate.
