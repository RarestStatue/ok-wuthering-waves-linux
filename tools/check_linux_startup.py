#!/usr/bin/env python3
"""Phase 2, 3 and 4 exit gate: how far does ok-ww's real config get on Linux?

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
5. The capture method it selected is an X11 one -- `config.py` now offers
   `['X11', 'X11_Composite']` on Linux, and selecting anything else means the branch in
   `update_capture_method` did not fire.
6. The interaction it selected is the Wine shim backend -- `config.py` now offers
   `['WinePostMessage', 'Pynput']` on Linux, and selecting anything else means the ladder
   in `DeviceManager` did not fire. This is the half of the Phase 4 criterion that needs
   neither the game nor Wine: whether the backend is *reachable* from ok-ww's own config.
   Whether it then reaches the game's wineserver is `tools/check_shim.py --target game`.
7. If the game is running, that capture method produces a frame of the right size. This is
   the Phase 3 exit criterion, and it is the only step that needs the game: with no game
   window there is nothing to capture and the step reports itself skipped, which is what
   CI sees.
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

    # `do_start` needs a *preferred* device, and on a first run there is none: it calls
    # `set_preferred_device()` and returns, having selected nothing. The real app recovers
    # because that branch emits `communicate.adb_devices`, which re-enters start once the
    # UI reacts. A gate that calls it once therefore only passes on a machine that has run
    # the app before -- `configs/` is gitignored, so a developer has `devices.json` and CI
    # does not, and the whole check silently depended on that. Drive both passes.
    def start(label):
        try:
            device_manager.do_start(notify=False)
        except Exception as e:
            traceback.print_exc()
            fail(f'do_start() raised {type(e).__name__}: {e} ({label})')

    start('first pass')
    if device_manager.capture_method is None:
        if device_manager.get_preferred_device() is None:
            fail('do_start() selected nothing and set no preferred device either')
        print('OK    first do_start only set the preferred device; re-entering as the app does')
        start('second pass')

    if device_manager.capture_method is None:
        fail('do_start() selected no capture method')
    if device_manager.interaction is None:
        fail('do_start() selected no interaction backend')
    capture = device_manager.capture_method
    print(f'OK    do_start selected {capture.get_name()} + '
          f'{type(device_manager.interaction).__name__}')

    interaction_name = type(device_manager.interaction).__name__
    if interaction_name != 'WinePostMessageInteraction':
        fail(f'do_start selected {interaction_name}, not the Wine shim backend; '
             f'config.py offers {config["windows"]["interaction"]}')
    print(f'OK    interaction backend is {interaction_name} '
          f'(connected={device_manager.interaction.connected})')

    if capture.get_name() not in ('X11', 'X11_Composite'):
        fail(f'do_start selected {capture.get_name()}, not an X11 capture method; '
             f'config.py offers {config["windows"]["capture_method"]}')
    print(f'OK    capture backend is {type(capture).__name__}')

    if not running:
        print('SKIP  no game window, so there is nothing to capture; '
              'startup itself is proven above')
        print('PASS  startup reaches capture-method selection')
        return 0

    hwnd_window.do_update_window_size()
    frame = capture.get_frame()
    if frame is None:
        fail(f'{capture.get_name()} produced no frame for hwnd {hwnd_window.hwnd}')
    if frame.ndim != 3 or frame.shape[2] != 3 or str(frame.dtype) != 'uint8':
        fail(f'frame is not an (h, w, 3) uint8 BGR array: {frame.shape} {frame.dtype}')
    if (frame.shape[1], frame.shape[0]) != (hwnd_window.width, hwnd_window.height):
        fail(f'frame is {frame.shape[1]}x{frame.shape[0]}, the window is '
             f'{hwnd_window.width}x{hwnd_window.height}')
    if frame.std() == 0:
        fail('every pixel of the frame is identical; this is a blank capture, not the game')
    print(f'OK    captured {frame.shape[1]}x{frame.shape[0]} of the game '
          f'(mean {frame.mean():.1f}, std {frame.std():.1f})')

    print('PASS  startup reaches capture-method selection and captures the game')
    return 0


if __name__ == '__main__':
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
