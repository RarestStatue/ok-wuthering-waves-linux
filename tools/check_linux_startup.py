#!/usr/bin/env python3
"""Phase 2 exit gate: how far does ok-ww's real config get on Linux?

The Phase 1 gate (`check_linux_imports.py`, in the ok-script fork) resolves every lazily
mapped symbol, which proves the tree *imports*. It cannot prove the app *starts*: the
window layer is only reached once `DeviceManager` builds an `HwndWindow`, and on Linux
that is `X11Window`. PORT.md deferred the second half of the Phase 1 criterion -- a
headless `OK(config)` construction that reaches the point where `do_start` selects a
capture method -- into Phase 2's exit gate, because startup used to stop earlier, in
`get_monitors_bounds()`.

This runs that gate. It needs ok-ww's own config (hence living here rather than in the
fork) and a display, and it does not need the game: the window is simply not found, which
is a state the poll has to handle anyway.

    PYTHONPATH=. python3 tools/check_linux_startup.py

What it asserts, in startup order:

1. `OK(config)` constructs -- config load, game-install detection, the single-instance
   lock, the whole lazy-import graph, `DeviceManager`.
2. The device layer got the X11 window class, and RandR answered with real monitors.
3. `update_pc_device()` -- i.e. `find_hwnd` -- produces a PC device entry. Without it the
   `windows` branch of `do_start` is never taken and no capture ever starts.
4. `do_start()` runs to completion and selects a capture method and an interaction.

Step 4 does *not* assert *which* capture method. Until ok-ww's own `config.py` gets its
Linux overrides (PORT.md Phase 5b) the list is still `['WGC', 'BitBlt_RenderFull']`, so
what gets selected here is the Windows BitBlt backend -- importable on Linux, harmless,
and never able to produce a frame. Phase 3 adds `X11`/`X11_Composite`; this gate then
starts naming them, without needing a change here.
"""

import os
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(message):
    print(f'FAIL  {message}')
    sys.stdout.flush()
    # Threads started by OK() are not all daemons, and the executor's are already running.
    os._exit(1)


def main():
    if sys.platform == 'win32':
        print('SKIP  this gate is about the Linux startup path')
        return 0
    if not os.environ.get('DISPLAY'):
        fail('DISPLAY is unset; the X11 window layer needs X11 or Xwayland')

    os.chdir(REPO)
    sys.path.insert(0, REPO)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    # `parse_arguments()` reads sys.argv, and a stray pytest/CI argument would land in the
    # app's own option parser.
    sys.argv = [sys.argv[0], '--headless']

    from config import config
    from ok import OK

    ok = OK(config)
    print('OK    OK(config) constructed')

    device_manager = ok.device_manager
    hwnd_window = device_manager.hwnd_window
    if type(hwnd_window).__name__ != 'X11Window':
        fail(f'DeviceManager built a {type(hwnd_window).__name__}, expected X11Window')
    print(f'OK    device layer uses {type(hwnd_window).__name__}')

    if not hwnd_window.monitors_bounds:
        fail('get_monitors_bounds() returned nothing; RandR enumeration failed')
    for left, top, right, bottom in hwnd_window.monitors_bounds:
        if right <= left or bottom <= top:
            fail(f'monitor rect is not (left, top, right, bottom): {(left, top, right, bottom)}')
    print(f'OK    monitors {hwnd_window.monitors_bounds}')

    imei = device_manager.update_pc_device()
    if not imei or imei not in device_manager.device_dict:
        fail(f'update_pc_device() produced no device entry (returned {imei!r})')
    device = device_manager.device_dict[imei]
    running = bool(device.get('real_hwnd'))
    print(f'OK    pc device {imei}: connected={device["connected"]} '
          f'{device["width"]}x{device["height"]} '
          f'({"game window found" if running else "game not running, which is a valid state"})')

    try:
        device_manager.do_start(notify=False)
    except Exception as e:
        traceback.print_exc()
        fail(f'do_start() raised {type(e).__name__}: {e}')

    if device_manager.capture_method is None:
        fail('do_start() selected no capture method')
    if device_manager.interaction is None:
        fail('do_start() selected no interaction backend')
    print(f'OK    do_start selected {device_manager.capture_method.get_name()} + '
          f'{type(device_manager.interaction).__name__}')

    print('PASS  startup reaches capture-method selection')
    return 0


if __name__ == '__main__':
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
