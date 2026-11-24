# Changelog

## 1.2.3 - EmaahhhPilot

### Added
- **Automatic hero upgrades** (Settings -> Upgrades & walls). Pick which heroes, and how many builders must be free before one starts; the reserved builder always stays free. Works even with Auto upgrade off (then only heroes are upgraded).

### Changed
- **History page redesigned.** Summary of the last run, total gold / elixir / time played, readable dates (Today, Yesterday), coloured tables and clearer titles.

## 1.2.2 - EmaahhhPilot

### Changed
- **Faster.** Buttons are polled every 0.25 s (was 0.4-0.5 s) and several fixed pauses were shortened: after Next, Claim, Continue and in screen recovery.

### Fixed
- **Stop key busy.** If F12 is used by another program, Ctrl+Shift+F12 is registered instead.
- Treasury: an empty treasury no longer logs a warning.

## 1.2.1 — EmaahhhPilot

### Fixed
- **Star Bonus chest scene.** After Claim the game shows a chest ("Tap!") that the bot could not pass: it now taps through it up to Continue (checked live).
- **Clan Castle learning now works.** The Castle is located from its name label ("Clan Castle (0/45)") and probed below it, each tap proven by the Treasury button; several frames are compared to survive animations. Checked live 3 times out of 3, then the automatic Treasury collected 4.8 M gold and 4.8 M elixir. The treasury also tries a few nearby taps instead of one.
- Live run (7 attacks, skip, collect, Alchemist) found no other problems.

## 1.2.0 — EmaahhhPilot

### Changed
- **Renamed to EmaahhhPilot.** App name, exe (`EmaahhhPilot.exe`), spec file, logo files,
  log file (`emaahhhpilot.log`), data folder (`%LOCALAPPDATA%\EmaahhhPilot`) and the
  `EMAAHHHPILOT_LOG_DIR` variable. Settings from an older `AresPilot` install are copied over
  on the first start. Copyright notices of BasePilot and AresPilot are kept (MIT).

### New (bot)
- **Auto-collect resources** (Run page → Modes, Home Village): every 4 minutes, on the
  home screen and zoomed out, taps the gold / elixir / dark elixir bubbles of the
  collectors. The resource bars, side and bottom buttons are excluded, at most 24 taps,
  and the loot tracker is rebased afterwards so collected resources are not booked as
  battle loot. Checked on a real village frame: 7 + 7 + 3 bubbles found, none on the HUD.
- **Wall order** (Settings): *Lowest level first* is now the default for walls and is
  independent from the building "Upgrade order".
- **Last wall of a level is upgraded too.** With one wall left, "Upgrade More" is greyed
  out (its text turns red) and never matched, so the bot gave up. It now pays the single
  wall directly — only when the bar title reads "Wall" (checked on real frames: a wall
  bar passes, a Giant Bomb bar is refused) and the confirm dialog asks exactly the wall
  row's price. New reference image: `templates/16_9/singleupgrade.png`.

- **Alchemist** (Run page → Modes, opt-in): when the hand bubble above the Helper Hut shows a
  helper is free, the bot taps it, opens "Convert Resources" and presses Convert with the
  resources selected in the Alchemist window (the game remembers the last choice). Checked
  every 5 minutes on the home screen; the loot tracker is rebased afterwards. When the hand
  bubble is hidden (it blinks) the bot taps the Helper Hut itself: the bar shows
  "Convert Resources" only when the Alchemist is ready. Convert opens a "Convert Resources?"
  dialog, which the bot confirms. Checked live: Dark Elixir 20 000 → Gold 3 120 000, then the
  Alchemist showed "Available in 20h" and the next check pressed nothing. New reference
  images: `helper_free.png`, `helperhut.png`, `alchemist_btn.png`, `convert.png`,
  `convert_confirm.png`. Other helpers: to follow.

- **Clan Castle treasury** (Run page → Modes, opt-in): every 30 minutes selects the Clan Castle,
  opens Treasury, presses Collect and confirms with Okay (flow checked live). The Castle is
  found from its own look, learned once with **Settings → Clan Castle → Learn Clan Castle**
  (tap the Castle in the game, press the button; the bot compares the village with and
  without the selection, taps candidates until Treasury shows up and saves that crop), so it
  works at any Castle level or scenery. Repeat after upgrading the Castle. New reference
  images: `treasury_btn.png`, `treasury_collect.png`, `clancastle.png` (fallback).

- **Skip poor bases** (Run page → Modes, opt-in; minimum in Settings → Attack, default 600 k):
  when the battle screen opens the bot reads the "Available Loot" box (same glyph reader as
  the HUD; checked live: 482 082 / 523 127 / 6 158 and three more bases, all exact) and presses
  Next (1 400 gold) while gold + elixir are below the minimum, up to 8 times per attack. An
  unreadable loot, a missing Next button or the limit means the base is attacked. Not used
  in Ranked or the Builder Base. New reference image: `nextbtn.png`.

### New (app)
- **A description for every option and button.** Selecting Off / Dry run / Maxer / Rusher,
  an army, Builder Base mode or Prioritise shows what it really does right under the
  selector, and every button, chip, stepper and sidebar item has a tooltip
  (`app/ui/qt/help_text.py` holds all texts). Settings has an About card (version,
  credits, open data folder).
- **History page**: every finished run is saved (`history.json`, last 500): totals, a loot
  per hour chart, yield per army (gold / elixir per attack, attacks per hour) and the
  recent sessions.
- **Logs**: filter "Warnings and errors" and a search box.
- **Game preview** on the Run page: what the bot sees, refreshed every 3 s while the page is
  visible (the bot's own last capture while it runs).
- **Notifications** (run ended by itself, bot stuck, error), **notification-area icon** (menu:
  Show / Start / Stop / Quit; optional "keep running when the window is closed") and
  **F12 stops the bot** (registered only while a run is active). Settings → App.
- **Scheduled start** (Run → Schedule): one run at a time of day. A scheduled start never opens
  a dialog: Ranked fill, Builder Base Elixir priority and a missing / non-16:9 game window
  are refused with a notification instead.

### Fixed
- **Continue pressed ~20 s late** (live 23/11). The post-battle step waited up to 10 s for an
  Okay popup even when Continue / Claim Reward / Return Home was already on screen, and the
  attack wait spent another 10 s on the Battle button that the reward screen hides. Both
  now react to a reward screen at once (Continue, Claim Reward with the chest tap-through).
- **Stuck on the "Star Bonus received!" popup** (live 23/11, 4x bonus). Its Claim button was
  unknown to the bot, and with the popup open the Battle button was never found (5 stuck
  cycles, then a 5 minute back-off). New reference image `starbonus_claim.png` (searched at
  nearby UI scales); the attack wait and the recovery press Claim first.
- **Stuck on a reward screen: Continue not pressed** (live 23/11: "2x Battle Bake / Item
  delivered to the Temporary Storage" after an attack). The recovery looked for Continue,
  Claim Reward and Return Home only at the reference scale, but that Continue renders at
  1.12x (match 0.89): it was never seen and the bot looped on "Battle button not found". The
  recovery now searches the nearby UI scales (sweep) for all three buttons.
- **Windowed game: "Unsupported capture aspect (~2388x1380)".** A game window with a title
  bar was captured whole, so it was not 16:9 and click positions were shifted by the title
  bar. The capture is now cropped to the client area, only when the whole window is not a
  supported aspect but the client area is (windows that already work are untouched).
- **F12 "already used by another program" right after a run.** Stopping and starting the bot
  a second apart tried to register the key before the previous run released it; it now
  retries for about 1.5 s.
- "Multi-run: Home Village collect" was logged when troops were missing in a normal run; it
  now says "Troops missing".
- **Match never starts / "Battle did not start" loop** (live 22/11). After Attack! the game
  shows the white matchmaking clouds, which can last minutes (measured: ~170 s). The bot gave
  up after 30 s, tapped recovery buttons over the clouds and then could not find the village
  again (5 failed cycles, run stopped). While the clouds are on screen it now waits without
  tapping (up to 5 minutes). New log lines trace each step of an attack (Battle button, army
  screen, battle started, clouds). Checked live: 9 attacks in 5 minutes, auto-collect tapped
  the collectors.
- **No attack when the picked army is not the trained one** (live 22/11: Super Minions
  trained, Valkyries picked). The failed Valkyrie-recipe step closed the army window with
  its X and Attack! was then pressed on the village: no battle, then "Troop not found".
  Now Attack! is looked up again (reopening Battle → Find a Match → army window if
  needed), a battle that never starts is a "stuck" cycle with no deploy, and when the
  picked troop is not on the bar but another supported army is, that army is used for
  this battle (with a log line saying which strategy to pick).
- Popup buttons remember their scale one by one (live: Okay 1.04x, Return Home 1.00x).
- **Claim Reward (and other end-of-battle buttons) not pressed.** On some game-window
  sizes these buttons render a few % smaller than the reference crops: "Claim Reward"
  scored 0.76 against a 0.80 threshold, so the bot waited on the Victory screen and
  timed out. Popup buttons (Claim Reward, Continue, Return Home, Okay, X) are now also
  searched at nearby scales (0.80x-1.24x) after a near miss; the scale that works is
  remembered. Where a button is expected (end of battle) every scale is tried even
  without a near miss (live: Continue only matched at 1.10x). A Continue already on
  screen, and further Continue screens after the first, are pressed too; recovery also
  presses Claim Reward / Continue when stuck on a reward screen.
- **Cheaper wall levels never upgraded (e.g. walls 12-13).** With "Priciest first" the
  wall walk stops at the first payable row from the top, so only the top level's price
  (e.g. 4M) was remembered. When the loot dropped below it, the pre-check concluded
  "no known wall level is payable" and never opened the Build panel again — the cheaper
  levels further down were never seen nor bought. The pre-check now says "no" only
  when the whole wall list has been walked; otherwise it opens the panel and looks.
- **Stuck screen.** When the Attack button was never reached the cycle counted as a normal
  attack, so the bot retried the same recovery forever. It is now a "stuck" cycle: after 5
  in a row a timed run stops with a message (run until maxed backs off 5 minutes), and no
  20 s post-battle wait runs when no battle started. Recovery logs when it gives up.
- **Faster Stop.** Click pauses and mouse-wheel steps are cut short by Stop, no click is
  sent after Stop, and hero / earthquake drops stop mid-way.
- **Player list (multi-run).** Opening or saving the list crashed when no `player_list.json`
  existed yet (it tried to copy a legacy file that wasn't there — or looped forever), and
  every valid name was discarded on load (a lost `not`), so the list always came back empty.
  A corrupt file now gives an empty list instead of `None`.
- **Game window selection.** A corrupt `window.json` returned `None` and crashed the
  callers; it now falls back to auto-detect. Clearing the selection no longer fails when the
  file is locked.
- **OCR without Tesseract.** Word and character OCR returned `None` instead of an empty list
  when Tesseract was missing, crashing the caller instead of logging the problem.
- **Template matching.** `find_all_template_centers` crashed when the matcher hit an error.
- **Per-glyph OCR confidence (debug).** Crashed on every call (broken `zip` unpacking) and
  picked the wrong glyph (lost priority logic).
- **OCR debug files.** Writing the TSV / box overlays had a `while` instead of an `if` and
  misplaced error handling; failures are now logged.
- **Config loading.** An invalid `data.json` is now logged as such.
- Removed ~50 dead lines left by the decompiler (`e = None` / `del e` after `return`).
- Temporary taskbar icon files are always deleted.

### New
- `tools/set_logo.py` turns any image into the app logo (PNG + multi-size ICO).
- **New look.** Softer cards, iOS-style segmented controls and switches. Run page: Live status card on top with run time and
  gold / elixir / dark elixir tiles, options as titled rows with a description, one
  Start / Stop button, Last session as tiles. Sidebar shows the bot state and version.
  Settings are grouped (Attack, Upgrades & walls, Game window, Display) and the redundant
  Save / Reset buttons are gone (changes were already saved on edit). Logs are coloured
  by level.

- **New logo and dark blue & cream theme.** The ivory 3D "e" on navy is the app and exe
  icon (`assets/emaahhhpilot_logo_source.png` is the original). The theme follows it:
  deep navy background, cream accent buttons with navy text and a tan "extrusion" lip
  underneath, warm beige secondary text.
- `tools/set_logo.py --round N` makes a rounded-square icon.
- **Liquid glass look.** Translucent glass panels with a bright top edge over a navy
  backdrop with soft cream / blue / violet glows; the 3D lips are gone. The selected
  segment is a clear glass lens that stretches like a droplet while it slides, and the
  switch knob does the same. Popups and dialogs stay opaque (separate windows).
- **120 fps animations.** A small engine (`app/ui/qt/motion.py`) drives every UI
  animation from one precise timer paced against a fixed schedule (measured ~118 fps;
  Qt's own animations tick at ~60). The 1 ms Windows timer resolution is requested only
  while something animates. The segment lens is painted at sub-pixel positions.
- **Start is green glass, Stop red glass**, each with a matching hover glow.
- **Smooth animations.** Switches slide, the cream pill slides between segment choices,
  pages cross-fade, loot and last-session numbers count up, the live state and the
  sidebar "Running" dot breathe while the bot works, and Start / Stop glow on hover.
  All 180–700 ms, UI-only (the bot thread is never slowed).
- **The exe now sits in the project folder** (`EmaahhhPilot.exe`, no more `dist\`):
  `python tools/build_exe.py` builds it there and stops with a clear message when the
  running app keeps it locked.

### Fixed (UI)
- Settings: the pinned game window was never highlighted in the list; errors were
  logged as "None".
- Players: moving a player up / down duplicated one row instead of swapping two.
- UI choices from an older AresPilot install are now migrated too.

- **Log file.** Every module had its own rotating handler on `arespilot.log`; at 5 MB the
  rotation failed on Windows (file in use) and from then on log lines were lost. All
  modules now share one handler.
- **Logs page.** Opening it again appended the whole file a second time and could freeze
  the window on a big log; it now loads only the end of the file, shows complete lines and
  follows the log after a rotation.
- **Builder Base without Baby Dragons.** A battle that opened with no dragon on the bar
  was left running, and the recovery looked for Surrender only (the button is End Battle
  before any troop is down): the bot waited minutes for the Battle button. The battle is
  now ended at once, and after 4 such battles in a row a timed run stops (run until maxed
  waits 5 minutes and tries again).
- **Deploy check.** The check after the last re-drop round ran before the game had time to
  take the dragons, so it could warn about dragons that were in fact placed.
- **Lost game window.** A window handle that died (game or Google Play Games restarted) is
  searched again instead of failing every capture; waits no longer spin when there is no
  capture.
- Closing the app during a run waits up to 3 s for the bot to stop, so the run summary is
  still written.

### Faster
- Screenshots: the capture is converted in one step (about 14 ms less per frame at
  2560×1440, same image).
- Builder Base troop-bar reads look at the card row only, not at the whole frame.

## 1.1.0 — AresPilot

First release under the **AresPilot** name (based on
[BasePilot](https://github.com/efebolukbasi/BasePilot) by Efe Bolukbasi, MIT).

### New
- **New name and logo.** The app, the exe (`AresPilot.exe`) and the data folder
  (`%LOCALAPPDATA%\AresPilot`) are renamed; settings from an older `BasePilot` install are
  copied over on the first start.
- **New interface.** Black, Apple-style design with a sidebar, header Start / Stop and
  iOS-style switches.
- **Builder Base Trophy mode.** Plays the first village to 100%, then attacks the second
  village with the surviving dragons and the fresh cards, and waits for the battle to end.
- **Baby Dragon edge deploy.** Reads the red border around the village and drops the dragons
  in six zones 2–8 tiles outside it, kept on the playable floor; machine with one dragon,
  abilities together after 10–25 s.
- **Missed-drop retries.** Dragons still on the bar after the deploy are dropped again, up to
  5 rounds.
- **Last run remembered.** The Run page restores village, army, Builder Base mode, duration
  and switches.

### Fixed
- Cards were tapped near the troop-switch button, which sometimes switched the troop
  instead of selecting it; the card select also needed more time to register.
- In the second village the Overall Damage stars were read as part of the red border,
  sending drops inside the village.
- Number fields in the interface were not centred.

### Changed
- The Players page shows "Work in progress" while the player list and multi-run are
  reworked.
- Clearer disclaimer: AresPilot is a personal educational project, not affiliated with
  Supercell, and the author does not condone cheating. The app shows it on the first start
  and runs only after it is accepted.
- The log no longer contains the account name from the game window title.
- README: removed the farming statistics section.

## 1.0.1 — BasePilot fork

October 2026 UI update of BasePilot: Home Village templates, Build panel auto upgrade, wall
upgrades, price/HUD reader and the other changes listed in the README.
