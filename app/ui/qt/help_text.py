'''Every explanatory text of the interface in one place, so wording stays consistent.

Each option of a selector has a description: it is shown under the selector (the chosen
option) and as a tooltip on its button. The texts describe what the bot really does — see
docs/armies.md and app/core/upgrade_policy.py before changing them.
'''

VILLAGES = {
    'Home Village': 'Farms loot in the main village: attacks other bases and can collect resources, '
                    'upgrade buildings and upgrade walls between attacks.',
    'Builder Base': 'Plays Builder Base battles with Baby Dragons and can upgrade its walls. If the game is '
                    'in the other village, the bot takes the boat by itself.',
}

STRATEGIES = {
    'Valkyries': 'Drags your Valkyries along the base edges in one continuous gesture, then drops the siege '
                 'machine, the heroes (and fires their abilities) and the Earthquake spells. Keep a saved '
                 'recipe starting with the Valkyrie on top of Saved Recipes.',
    'Sneaky Goblins': 'Drags your Sneaky Goblins along the base edges (about 15 s), then the siege machine, '
                      'the heroes with their abilities and the Earthquake spells.',
    'Super Minions': 'Drags your Super Minions along the base edges (a new random 2.8–4.2 s every raid), then '
                     'the siege machine, the heroes with their abilities and the Earthquake spells.',
    'Edrags': 'Drops 12 Electro Dragons one by one around the village (0.2 s apart), then the heroes with '
              'their abilities and the Earthquake spells.',
}

BB_STRATEGIES = {
    'Baby Dragon': 'Zooms out, reads the red no-deploy border and drops one Baby Dragon per zone, 2–8 tiles '
                   'outside it, with the Battle Machine or Flying Machine. All abilities fire together after '
                   '10–25 s. Fill every camp with Baby Dragons.',
    'Night Witches': 'Not available yet: it is still under development.',
}

AUTO_UPGRADE = {
    'Off': 'The bot only attacks. It never opens the builder menu to start upgrades.',
    'Dry run': 'Scans the builder menu and writes in the log what Maxer would start, but never presses Upgrade. '
               'Use it first to check that the bot reads your prices correctly.',
    'Maxer': 'Starts upgrades with your loot and never touches the Town Hall. Dark elixir upgrades (heroes) go '
             'first, then the biggest or the cheapest job as set in Settings → Upgrade order. Keeps the builders '
             'you reserved for walls and a gold buffer for matchmaking fees.',
    'Rusher': 'Same rules as Maxer, but starts the Town Hall upgrade the moment you can afford it. Use it to '
              'climb to the next Town Hall level quickly; defences fall behind.',
}

BB_PRIORITISE = {
    'Gold': 'Plays the battle until 2 stars, then ends it: the fastest way to fill Builder Base gold.',
    'Both': 'Plays the battle until 1 star, then ends it: a balance between gold and elixir.',
    'Elixir': 'Surrenders right after deploying, which gives elixir quickly but lowers your trophies.',
    'Trophy': 'Never ends a battle early: plays the first village to 100%, then attacks the second one '
              'with the surviving Baby Dragons and the fresh cards.',
}

ALCHEMIST = ('When the hand bubble shows the Alchemist is free, opens the Helper Hut and presses Convert '
             'with the resources selected in its window (the game remembers your last choice: set it once '
             'by hand). Checked every 5 minutes. This spends the source resource.')

TREASURY = ('Every 30 minutes, selects the Clan Castle, opens its Treasury (Star Bonus and war loot) and '
            'collects everything into your storages. If the Castle is not recognised (new level or '
            'scenery) nothing is pressed and the log says so.')

CASTLE_LEARN = ('Teaches the bot what your Clan Castle looks like (any level or scenery). In the game, '
                'tap your Clan Castle so its buttons (Treasury…) show, then press this and do not touch '
                'the mouse. Repeat after upgrading the Castle.')

SKIP_RUN = ('While scouting, reads the base\'s Available Loot and presses Next (costs 1 400 gold each time) '
            'until gold + elixir reach the minimum set in Settings, up to 8 times per attack. '
            'If the loot cannot be read the base is attacked.')
SKIP_SETTING = ('Minimum gold + elixir (in thousands) a base must have to be attacked when "Skip poor bases" '
                'is on. Dark elixir is not counted.')
HERO_UPGRADE = ('Upgrades your heroes by itself, even with Auto upgrade off (then ONLY heroes are upgraded). '
                'It looks at the Build list every few minutes, picks the cheapest hero you can afford and starts it. '
                'The reserved builder (Settings → Reserve builders) always stays free.')
HERO_WHICH = 'Only the ticked heroes are upgraded by the bot. Untick a hero you want to level yourself.'
HERO_WHEN = ('A hero upgrade starts only when at least this many builders are free. 2 = one builder for the hero '
             'and one kept free for walls; raise it to keep more builders available.')

# Single controls (tooltips)
START = 'Start the bot with the options on this page. The game must be open, in English and in 16:9.'
STOP = 'Stop the bot. It finishes the click in progress and writes the run summary. F12 does the same.'
CHIP = 'Set the duration to {minutes} minutes.'
STEPPER_UP = 'Add one minute.'
STEPPER_DOWN = 'Remove one minute.'
MINUTES = 'Length of a timed run, in minutes (1–999).'
SCHEDULE_TIME = 'Time of day the scheduled run starts.'
HELP_BB = 'What each Prioritise option does.'

NAV = {
    'run': 'Choose what to farm, then start and watch the bot.',
    'history': 'Every finished run, with totals, a loot-per-hour chart and the yield of each army.',
    'settings': 'Wall and upgrade rules, notifications, the game window and the display.',
    'players': 'Accounts for multi-run (work in progress).',
    'logs': 'What the bot is doing, live. Filter warnings and errors or search the text.',
}

SETTINGS_BUTTONS = {
    'refresh': 'Look for open windows again.',
    'test': 'Check the size and shape of the selected window (it must read 16:9).',
    'info': 'Show every child window under the selected one, to find the game surface.',
    'use': 'Always use the selected window as the game window.',
    'auto': 'Forget the pinned window and find the game automatically.',
    'switch169': 'Change the screen resolution to a 16:9 mode so the game starts in 16:9. '
                 'Close the game completely before using it, then press Restore.',
    'restore': 'Put your screen back to the resolution it had before.',
}

LOGS = {
    'clear': 'Empty the list on screen. The log file is not touched.',
    'open': 'Open the folder that holds the log file.',
    'search': 'Show only lines containing this text.',
    'all': 'Every line of the log.',
    'issues': 'Only warnings, errors and the lines that belong to them.',
}

HISTORY = {
    'clear': 'Delete every saved session. This cannot be undone.',
}
