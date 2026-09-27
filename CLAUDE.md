# Lionel Types

Full-screen kid typing app (pygame-ce), Windows + Mac. See README.md for features and layout.

## Testing

- `pytest` — headless (SDL dummy drivers via `tests/conftest.py`). Run it after any change.
- Visual checks: drive `App(windowed=True, size=(1920, 1080))` under `SDL_VIDEODRIVER=dummy`,
  post pygame events, call `app.step(dt)`, and `pygame.image.save(app.screen, ...)`.

## Do not take over the developer's screen

The default launch is full screen with an OS keyboard hook. Never run `python -m lionel_types`
(or the launchers, or `tools/check_windows_lock.py --on-my-desktop`) on the developer's
desktop — the user may be working. Use `--windowed` with `SDL_VIDEODRIVER=dummy`, or let CI
run the real-desktop lock checks.

## Conventions

- Keep `page.py` free of pygame so layout stays unit-testable.
- Lockdown code must fail open: any exception in a hook/tap callback lets the key through.
- Mac lockdown code can't be run locally on Windows; CI (`macos-latest`) exercises it.
