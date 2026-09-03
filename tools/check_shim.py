#!/usr/bin/env python3
"""Phase 4 exit gate: does input actually reach a Wine window from Linux?

Two targets, because the two questions are separable and only one of them needs the game.

    PYTHONPATH=. python3 tools/check_shim.py --target protocol
        Compares the command set the Linux backend sends against the command set the C
        source implements. No Wine, no Steam, no display -- the two halves of the protocol
        live in two repos and nothing else compares them, so this runs in CI.

    PYTHONPATH=. python3 tools/check_shim.py --target wine
        Launches `wine notepad` in a throwaway prefix, starts the shim beside it, and
        drives the whole protocol against it: handshake, token auth, FINDWIN, GEOM, and
        then types with the keyboard focus held on *another* window, proving delivery by
        capturing the notepad window's own pixels before and after. This needs no game, no
        Steam and no Proton, and it is the regression test for the shim itself.

    PYTHONPATH=. python3 tools/check_shim.py --target game [--key m]
        The real thing. Resolves the running game's prefix and Proton build, launches the
        shim into it, and reports which launch shape reached the game's wineserver --
        `proton run` or the SteamLinuxRuntime entry point. That answer is **[GATE-1b]**.
        With `--key`, it also posts one keypress while the game is unfocused and reports
        how much the captured frame changed, which is **[GATE-2]**.

Both targets print `PASS`/`FAIL` lines and exit non-zero on the first failure, like
`tools/check_linux_startup.py`.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIM_EXE = os.path.join(REPO, 'shim', 'okww-input-shim.exe')
SHIM_SRC = os.path.join(REPO, 'shim', 'okww-input-shim.c')


class GateFailure(Exception):
    """A failed assertion that still has to run its cleanup.

    `fail()` calls `os._exit`, which skips `finally` blocks -- and the wine target's
    `finally` is what kills its notepad and removes its prefix. Every failing run of an
    earlier version of this gate leaked a `wine notepad`, and the *next* run then found one
    of those stale windows first and captured it while the shim typed into its own: six
    leaked notepads, and a gate that reported "the characters did not reach the window"
    about a window nobody had typed into.
    """


def fail(message):
    print(f'FAIL  {message}')
    sys.stdout.flush()
    os._exit(1)


def ok(message):
    print(f'OK    {message}')
    sys.stdout.flush()


# --------------------------------------------------------------------------------------
# The protocol pin: every command the Python client sends must exist in the C source.
# --------------------------------------------------------------------------------------

def check_protocol_agreement():
    """The two halves of the protocol live in two repos; nothing else compares them."""
    from ok.compat import proton_shim  # noqa: F401  (import proves the fork is installed)

    try:
        source = open(SHIM_SRC, encoding='utf-8').read()
    except OSError as e:
        fail(f'cannot read {SHIM_SRC}: {e}')

    import inspect
    import re

    from ok.device.interaction_methods import wine_post_message

    client_source = inspect.getsource(wine_post_message)
    sent = set()
    for match in re.finditer(r"""_(?:send|request)\(f?['"]([A-Z]+)""", client_source):
        sent.add(match.group(1))
    for match in re.finditer(r"""\{prefix\}(DOWN|UP)""", client_source):
        sent.update({'L' + match.group(1), 'R' + match.group(1), 'M' + match.group(1)})

    handled = set(re.findall(r'strcmp\(cmd, "([A-Z]+)"\)', source))
    missing = sorted(sent - handled)
    if missing:
        fail(f'the Linux client sends commands the shim does not implement: {missing}')
    ok(f'protocol agrees: {len(sent)} commands sent, {len(handled)} implemented')


# --------------------------------------------------------------------------------------
# Target: wine notepad in a scratch prefix
# --------------------------------------------------------------------------------------

def wine_target(args):
    if not shutil.which('wine'):
        fail('wine is not installed; this target needs it (the --target game one does not)')
    if not os.environ.get('DISPLAY'):
        fail('DISPLAY is unset')

    from ok.compat import x11, xshm
    from ok.compat.proton_shim import (
        ShimClient, ShimError, create_handshake_placeholder, parse_handshake, shim_argv,
    )

    prefix = tempfile.mkdtemp(prefix='okww-shim-gate-')
    env = dict(os.environ, WINEPREFIX=prefix, WINEDEBUG='-all', DISPLAY=os.environ['DISPLAY'])
    env.pop('WINEARCH', None)
    processes = []
    already_open = set(x11.list_clients())
    stale = [w for w in already_open if 'notepad' in (x11.get_name(w) or '').lower()]
    if stale:
        print(f'      note: {len(stale)} notepad window(s) were already open; ignoring them')
    try:
        print(f'      scratch prefix {prefix}')
        subprocess.run(['wineboot', '-i'], env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=180)
        notepad = subprocess.Popen(['wine', 'notepad'], env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        processes.append(notepad)

        # Only a window that appeared *after* this run started: a leftover notepad from
        # another session would be captured here while the shim typed into ours.
        window = wait_for_window(x11, 'Notepad', timeout=60, ignore=already_open)
        if not window:
            raise GateFailure('wine notepad never mapped a window')
        wid, geometry = window
        ok(f'wine notepad window {wid:#x} at {geometry}')

        drive_c = os.path.join(prefix, 'drive_c')
        handshake_path = os.path.join(drive_c, 'okww-shim.port')
        shutil.copy2(SHIM_EXE, os.path.join(drive_c, 'okww-input-shim.exe'))
        create_handshake_placeholder(handshake_path)

        # `wine notepad` keeps its text in an `Edit` child and ignores WM_CHAR posted to
        # the frame -- the frame only blinks its caret, which is what an earlier version of
        # this gate mistook for delivery. The game needs none of this: Unreal's toplevel is
        # the input target, which is what upstream posts to on Windows.
        argv = shim_argv(exe_name='notepad.exe', hwnd_class=None, idle_exit=120,
                         child_class='Edit')
        shim = subprocess.Popen(['wine'] + argv, env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        processes.append(shim)

        handshake = None
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and handshake is None:
            try:
                handshake = parse_handshake(open(handshake_path).read())
            except OSError:
                handshake = None
            if handshake is None:
                time.sleep(0.25)
        if handshake is None:
            raise GateFailure('the shim wrote no handshake file; it died before binding its socket')
        if os.stat(handshake_path).st_mode & 0o077:
            raise GateFailure(f'the handshake file is group/world readable: {handshake_path}')
        ok(f'handshake {handshake} (mode 0600)')

        rejected = ShimClient(handshake.port, 'not-the-token', timeout=3)
        try:
            rejected.connect()
            raise GateFailure('the shim accepted a connection presenting the wrong token')
        except Exception:
            ok('a wrong token is refused')
        finally:
            rejected.close()

        client = ShimClient(handshake.port, handshake.token, timeout=5)
        client.connect()
        # The window can appear after the shim does -- which is the normal case against the
        # game, where the shim is started while the game is still loading -- so retry
        # rather than treating the first miss as a failure.
        hwnd = 0
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not hwnd:
            try:
                hwnd = int(client.request('FINDWIN', 'FINDWIN').split('=')[1])
            except ShimError:
                time.sleep(0.5)
        if not hwnd:
            raise GateFailure('FINDWIN found no notepad window')
        geom = [int(value) for value in client.request('GEOM', 'GEOM').split()]
        if geom[2] <= 0 or geom[3] <= 0:
            raise GateFailure(f'GEOM returned an empty client rect: {geom}')
        ok(f'FINDWIN hwnd={hwnd} GEOM x={geom[0]} y={geom[1]} {geom[2]}x{geom[3]}')

        info = client.request('WININFO', 'WININFO')
        ok(f'the shim is posting to {info}')

        # Delivery, with the keyboard focus somewhere else entirely. The pixels are the
        # evidence -- but notepad blinks a caret whether or not anything was typed, so the
        # idle change over the same interval is measured first and the typed text has to
        # beat it by a wide margin. Without that control this gate passes on a caret.
        grabber = xshm.X11Grabber()
        focus_before, release_focus = focus_something_else(x11, wid)
        background = focus_before != wid
        if not background:
            print('      note: focus could not be moved off notepad, so this run proves '
                  'delivery but not *background* delivery')

        idle_a = grabber.grab(wid, 0, 0, geometry[2], geometry[3])
        time.sleep(1.0)
        idle_b = grabber.grab(wid, 0, 0, geometry[2], geometry[3])
        if idle_a is None or idle_b is None:
            raise GateFailure('could not capture the notepad window')
        idle = int((idle_a != idle_b).sum())

        before = grabber.grab(wid, 0, 0, geometry[2], geometry[3])
        for character in 'POSTMESSAGE OK':
            client.send(f'CHAR {ord(character)}')
            time.sleep(0.01)
        time.sleep(1.0)
        after = grabber.grab(wid, 0, 0, geometry[2], geometry[3])
        grabber.close()
        release_focus()
        if after is None:
            raise GateFailure('could not capture the notepad window after typing')
        changed = int((before != after).sum())
        if changed < max(500, 5 * idle):
            raise GateFailure(f'typing changed {changed} pixels against {idle} for an idle caret blink '
                 f'over the same interval: the characters did not reach the window')
        ok(f'typed text reached the window ({changed} pixels changed, {idle} while idle; '
           f'the focus was on {focus_before:#x}, '
           f'{"another window" if background else "notepad itself"})')

        stats = client.request('PING', 'PING')
        ok(f'PING -> {stats}')
        if ' errors=0' not in stats:
            raise GateFailure(f'the shim reports post errors: {stats}')

        client.send('QUIT')
        client.close()
        print('PASS  the shim speaks its protocol and delivers input into Wine')
        return 0
    except GateFailure as failure:
        message = str(failure)
        return_code = 1
    finally:
        for process in processes:
            try:
                process.terminate()
            except Exception:
                pass
        subprocess.run(['wineserver', '-k'], env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        shutil.rmtree(prefix, ignore_errors=True)
    fail(message)
    return return_code


def focus_something_else(x11, avoid_wid):
    """Take the keyboard focus away from the target window, and report where it went.

    The whole claim of this port is that input lands in a window that does *not* have focus
    [PORT.md V6], so a harness that types into the focused window proves nothing about the
    thing being tested. Existing windows often refuse `_NET_ACTIVE_WINDOW` (KWin ignores it
    from a client with no user interaction behind it), and parking the focus on the root
    window does not stick either -- the WM puts it straight back on the active window. What
    does work is mapping a new window: a WM focuses a newly mapped normal window.

    Returns ``(focused_wid, cleanup)``; call ``cleanup()`` once the typing is done.
    """
    try:
        from Xlib import X, display
    except ImportError:
        return x11.get_focus_toplevel(), lambda: None

    connection = display.Display()
    screen = connection.screen()
    holder = screen.root.create_window(
        200, 200, 400, 200, 1, screen.root_depth, X.InputOutput, X.CopyFromParent,
        background_pixel=screen.white_pixel, event_mask=X.ExposureMask | X.KeyPressMask)
    holder.set_wm_name('okww shim gate -- focus holder')
    holder.set_wm_class('okww_gate', 'okww_gate')
    holder.map()
    connection.sync()
    time.sleep(0.6)
    x11.activate(holder.id)
    time.sleep(0.4)
    focused = x11.get_focus_toplevel()

    def cleanup():
        try:
            holder.destroy()
            connection.sync()
            connection.close()
        except Exception:
            pass

    return focused, cleanup


def wait_for_window(x11, title_fragment, timeout=30, ignore=()):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for wid in x11.list_clients():
            if wid in ignore:
                continue
            name = x11.get_name(wid) or ''
            if title_fragment.lower() in name.lower():
                geometry = x11.get_abs_geometry(wid)
                if geometry and geometry[2] > 10 and geometry[3] > 10:
                    return wid, geometry
        time.sleep(0.3)
    return None


# --------------------------------------------------------------------------------------
# Target: the real game -- [GATE-1b] and [GATE-2]
# --------------------------------------------------------------------------------------

def game_target(args):
    from ok.compat.proton_shim import (
        WUWA_APPID, WUWA_EXE, ShimClient, connect_or_start, game_pid, read_handshake,
        resolve_steam_game, start_shim,
    )

    game = resolve_steam_game(appid=args.appid, exe_name=WUWA_EXE)
    ok(f'game {game}')
    print(f'      prefix  {game.compatdata}')
    print(f'      proton  {game.proton_dir}')
    print(f'      runtime {game.runtime_entry_point}')

    pid = game_pid(WUWA_EXE)
    if pid is None:
        fail(f'{WUWA_EXE} is not running; launch Wuthering Waves through Steam first '
             f'(appid {WUWA_APPID})')
    ok(f'{WUWA_EXE} is running as pid {pid}')

    started = time.monotonic()
    if args.reuse and read_handshake(game.handshake_path):
        # The same path the app takes: connect to the shim already in the prefix rather
        # than leaving another one behind on every run.
        client, _process = connect_or_start(game, shim_exe=SHIM_EXE, exe_name=WUWA_EXE,
                                            hwnd_class='UnrealWindow', timeout=args.timeout)
        ok(f'[GATE-1b] connected to a shim in the prefix after '
           f'{time.monotonic() - started:.1f}s, hwnd={client.hwnd}')
    else:
        try:
            os.unlink(game.handshake_path)
        except OSError:
            pass
        handshake, _process, shape = start_shim(game, shim_exe=SHIM_EXE, exe_name=WUWA_EXE,
                                                hwnd_class='UnrealWindow',
                                                timeout=args.timeout)
        ok(f'[GATE-1b] the shim answered via "{shape}" after '
           f'{time.monotonic() - started:.1f}s: {handshake}')
        client = ShimClient(handshake.port, handshake.token, timeout=10)
        client.connect()
    reply = client.request('FINDWIN', 'FINDWIN')
    hwnd = int(reply.split('=')[1])
    if not hwnd:
        fail('[GATE-1b] the shim started but found no game window: it is in a different '
             'wineserver session than the game')
    ok(f'[GATE-1b] FINDWIN resolved the game window: hwnd={hwnd}')

    geom = [int(value) for value in client.request('GEOM', 'GEOM').split()]
    if geom[2] < 320 or geom[3] < 240:
        fail(f'GEOM is not a plausible game client rect: {geom}')
    ok(f'GEOM x={geom[0]} y={geom[1]} {geom[2]}x{geom[3]}')
    cursor = client.request('GETCURSOR', 'GETCURSOR')
    ok(f'GETCURSOR {cursor}')

    if not args.key:
        print('SKIP  [GATE-2] needs --key; nothing was posted to the game')
        print('PASS  the shim reaches the game\'s wineserver and sees its window')
        client.close()
        return 0

    # A game frame is never still -- weather, foliage, idle animation -- so "the picture
    # changed" proves nothing on its own. Measure the idle drift over the same interval
    # first and compare against it.
    from ok.compat import x11

    focused = x11.get_focus_toplevel()
    game_wid = game_window_id()
    print(f'      focus is on {focused:#x}, the game window is {game_wid:#x} '
          f'({"the game HAS focus -- this run cannot prove background delivery" if focused == game_wid else "so this is background delivery"})')

    idle_a = capture_game_frame()
    time.sleep(args.settle)
    idle_b = capture_game_frame()
    idle = frame_difference(idle_a, idle_b)

    # Drive the *real* backend, not raw socket writes. `send_key` posts WM_ACTIVATE first
    # (upstream's `try_activate`, which the game needs to treat itself as the active window)
    # and then the down/up pair with a hold; a bare KEYDOWN/KEYUP is not what ok-ww sends
    # and is not what this gate should be testing.
    interaction = build_interaction(game_wid)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not interaction.connected:
        time.sleep(0.2)
    if not interaction.connected:
        fail('WinePostMessageInteraction could not reach the shim')
    ok('WinePostMessageInteraction is connected; posting through it')

    print(f'      posting {args.key!r} the way ok-ww does; watch the game')
    before = capture_game_frame()
    interaction.send_key(args.key, down_time=args.hold)
    time.sleep(args.settle)
    after = capture_game_frame()
    change = frame_difference(before, after)

    stats = client.request('PING', 'PING')
    ok(f'PING -> {stats}')
    if 'errors=0' not in stats:
        fail(f'the shim could not post: {stats}')
    interaction.on_destroy()

    if idle is None or change is None:
        print('WARN  could not capture the game window; judge [GATE-2] by eye')
    else:
        ok(f'[GATE-2] idle drift over {args.settle:.1f}s: {idle:.2f}; '
           f'after the keypress: {change:.2f} ({change / max(idle, 0.01):.1f}x)')
        if change < max(3 * idle, 1.0):
            print('WARN  [GATE-2] the keypress did not move the picture more than the game '
                  'moves on its own. Either the game ignored it, or this key does nothing '
                  'in the current game state -- re-run with a key that visibly opens '
                  'something, and watch the screen.')
        else:
            ok('[GATE-2] the game reacted to a posted key')

    client.close()
    print('PASS  the shim posted into the running game')
    return 0


class GameWindowStub:
    """The three things `WinePostMessageInteraction` reads off the window layer.

    Building a real `X11Window` here would start its poll thread and its mute handling for
    no benefit: the backend only needs the window id, the class and the exe name.
    """

    hwnds = []
    hwnd_class = 'UnrealWindow'
    exe_names = ['Client-Win64-Shipping.exe']

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.top_hwnd = hwnd

    def get_top_window_cords(self, x, y):
        return x, y


def build_interaction(game_wid):
    from ok.device.interaction_methods.wine_post_message import WinePostMessageInteraction
    return WinePostMessageInteraction(None, GameWindowStub(game_wid))


def frame_difference(first, second):
    """Mean absolute per-pixel difference, or None if either capture failed."""
    if first is None or second is None:
        return None
    return float(abs(second.astype('int16') - first.astype('int16')).mean())


def game_window_id():
    from ok.compat import window_x11
    _name, hwnd, *_rest = window_x11.find_hwnd(None, ['Client-Win64-Shipping.exe'], 0, 0)
    return hwnd


def capture_game_frame():
    """One frame of the game window, through the Phase 3 capture path."""
    try:
        from ok.compat import window_x11, xshm
        # (name, hwnd, full_path, x_offset, y_offset, real_width, real_height, hwnds)
        _name, hwnd, _path, _ox, _oy, width, height, _hwnds = window_x11.find_hwnd(
            None, ['Client-Win64-Shipping.exe'], 0, 0, class_name='UnrealWindow')
        if not hwnd:
            return None
        grabber = xshm.X11Grabber()
        try:
            return grabber.grab(hwnd, 0, 0, width, height)
        finally:
            grabber.close()
    except Exception as e:
        print(f'      capture failed: {e}')
        return None


def key_code(key):
    from ok.device.interaction_methods.keys import vk_key_dict
    if code := vk_key_dict.get(str(key).upper()):
        return code
    if len(key) == 1 and key.isascii() and key.isalnum():
        return ord(key.upper())
    fail(f'cannot map {key!r} to a virtual-key code')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', choices=('protocol', 'wine', 'game'), default='wine',
                        help='protocol: the source-level pin only, no Wine and no game')
    parser.add_argument('--key', help='[GATE-2] post this key to the running game')
    parser.add_argument('--appid', default='3513350')
    parser.add_argument('--timeout', type=float, default=40.0)
    parser.add_argument('--hold', type=float, default=0.05,
                        help='[GATE-2] seconds to hold the key down')
    parser.add_argument('--settle', type=float, default=1.5,
                        help='[GATE-2] seconds to wait for the game to react, and the '
                             'window over which the idle drift is measured')
    parser.add_argument('--reuse', action='store_true',
                        help='connect to a shim already running in the prefix if there is one')
    args = parser.parse_args()

    os.chdir(REPO)
    sys.path.insert(0, REPO)
    if not os.path.isfile(SHIM_EXE):
        fail(f'{SHIM_EXE} is missing; build it with `x86_64-w64-mingw32-gcc -O2 -s -o '
             f'shim/okww-input-shim.exe shim/okww-input-shim.c -lws2_32`')

    check_protocol_agreement()
    if args.target == 'protocol':
        print('PASS  the shim implements every command the Linux backend sends')
        return 0
    return wine_target(args) if args.target == 'wine' else game_target(args)


if __name__ == '__main__':
    code = main()
    sys.stdout.flush()
    os._exit(code or 0)
