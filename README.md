# Lionel Types

A full-screen typing playground for little kids, for Windows and Mac. Every key does
something big, bright and noisy, and it's hard for small hands to get out of it.

- **Every key shows up huge** in the middle of the screen, popping in with a sparkle.
  Letters are shown as capitals to match the keycaps.
- **Special keys become little keycaps**: F1, PRTSC, TAB, ESC, even WIN and SHIFT when
  pressed on their own.
- **The keyboard is a xylophone.** Each key plays its own note from a pentatonic scale,
  rising left to right and bottom row to top, so mashing always sounds nice.
- **It talks.** The computer's own voice says each letter, and reads whole words when
  Space or Enter is pressed. No downloads needed.
- **Enter** starts a new line with a blank line above it. **Backspace** deletes, and the
  **arrow keys** move the cursor.
- **When the page fills up**, the letters tumble off the screen, confetti falls, and the
  voice says "Great job!"
- **Find the letter**: a game where a big letter appears, the voice asks for it, and
  finding the key earns a star.
- The mouse leaves glitter trails, and clicks set off fireworks.

## Getting it onto a computer

### Ready-made app (no Python needed)

Open the latest [release](https://github.com/cwgannon/lionel_types/releases), or the
latest **Build apps** run under [Actions](https://github.com/cwgannon/lionel_types/actions),
and download:

- **Windows:** `Lionel Types.exe`. Double-click it. If SmartScreen warns about an unknown
  publisher, choose *More info* > *Run anyway*.
- **Mac (Apple Silicon):** `Lionel Types for Mac.zip`. Unzip it, then **right-click >
  Open** the first time, because the app isn't signed. If macOS says it's damaged, run
  `xattr -cr "Lionel Types.app"` in Terminal.

To publish a new release, push a tag like `v2.0.0`.

### From this folder (needs Python 3.10 or newer)

Double-click **`Lionel Types for Windows.bat`** or **`Lionel Types for Mac.command`**.
The first run sets itself up, which needs an internet connection and takes under a
minute. After that it starts right away.

If macOS won't open the `.command` file, run `chmod +x "Lionel Types for Mac.command"`
once in Terminal.

## For grown-ups

**Hold Ctrl + Shift + Q for two seconds** (Control + Shift + Q on a Mac) to open the
parent menu. It has to be exactly those three keys, with nothing else pressed, so a
mashing toddler won't trigger it. A ring fills up while you hold. The menu has:

| Key | Setting |
| --- | --- |
| 1 | Sound on/off |
| 2 | Voice on/off |
| 3 | Letters: ABC capitals / abc small / as typed |
| 4 | Colors: rainbow / classic light blue |
| 5 | Text size: big / bigger / biggest |
| 6 | Activity: free typing / find the letter |
| C | Clear the screen |
| Q | Quit |
| Esc | Back to typing |

Settings are remembered between runs. The menu also lists what the keyboard lock is
doing on this computer, and it closes itself after 45 seconds if left open.

### What's locked

**Windows** uses a low-level keyboard hook, active only while Lionel Types is the window
in front. It blocks:

- the Windows key (Start menu, Win+D, Win+L and friends)
- Alt+Tab, Alt+F4 and Alt+Esc
- Ctrl+Esc and Ctrl+Shift+Esc
- Print Screen / Snipping Tool
- media and launch keys (volume, mail, calculator, ...)

The Sticky Keys pop-up (Shift pressed five times) and the Filter Keys pop-up (right Shift
held) are switched off while it runs and put back when it closes.

**Mac** uses kiosk mode: no Dock or menu bar, no Cmd+Tab or Mission Control, no Cmd+Q or
Cmd+H. To also block every other Command shortcut (Cmd+Space, screenshots) and the media
keys, allow the app under **System Settings > Privacy & Security > Accessibility**. Allow
*Terminal* if you use the `.command` file, or *Lionel Types* for the ready-made app.

Both: the mouse can't leave the screen, even with two monitors, and closing the window
is ignored.

**Things no app can block:** Ctrl+Alt+Del on Windows, the power button, and some laptop
Fn-key functions. Those are the grown-ups' emergency exits:

- **Windows:** Ctrl+Alt+Del, then Task Manager > Lionel Types > End task.
- **Mac:** Cmd+Option+Esc (Force Quit) is deliberately left working.

If the screen says **"Click to play!"**, another window has the keyboard. Click anywhere
to bring Lionel Types back.

## Command-line options

```
python -m lionel_types              # full screen, locked
python -m lionel_types --windowed   # in a normal window, no lock: good for trying it out
python -m lionel_types --no-lock    # full screen but leave OS shortcuts alone
python -m lionel_types --mute       # no sound or voice this time
python -m lionel_types --self-test 10   # run 10 s, then report what the lock intercepted
```

## Development

```
python -m venv .venv
.venv\Scripts\activate            # Windows; on Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt pytest
pytest
```

The tests run pygame headless. CI (`.github/workflows/ci.yml`) runs them on Windows, Mac
and Linux. On a real Windows desktop it also runs `tools/check_windows_lock.py`, which
presses the Windows key, Alt+Tab, Print Screen and Shift x5 at the running app and checks
none of them got out. On a real Mac desktop it runs the kiosk-mode self-test.

| File | What it does |
| --- | --- |
| `lionel_types/app.py` | main loop, input routing, parent menu wiring |
| `lionel_types/free_typing.py` | the typing screen |
| `lionel_types/find_letter.py` | the Find the letter game |
| `lionel_types/page.py` | text model: paragraphs, cursor, centered word-wrap (pure Python) |
| `lionel_types/keys.py` | what each key means: character, key name, or command |
| `lionel_types/lockdown/` | keyboard lock for Windows (`windows.py`) and Mac (`macos.py`) |
| `lionel_types/sound.py` | synthesized sounds (no audio files) |
| `lionel_types/speech.py` | the built-in voice (PowerShell on Windows, `say` on Mac) |
| `lionel_types/style.py`, `effects.py` | fonts, colors, keycaps, particles |

The font is [Andika](https://software.sil.org/andika/) from SIL, which is designed for
beginning readers and draws **a** and **g** the way kids learn to write them. It's under
the SIL Open Font License (`lionel_types/assets/OFL.txt`).

`lionel types prompt.txt` holds the original requirements this project started from.
