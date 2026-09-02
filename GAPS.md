# GAPS

> **Resolved 2026-09-01.** Every Phase 2 finding below was fixed and each fix verified by
> execution, on this machine's real KWin/Xwayland desktop. The code fixes are in
> ok-script-linux `9b33a03` (branch `linux-port`); the CI job and the lock repin are in
> this repo.
>
> | | Outcome |
> |---|---|
> | P2-1 | fixed — `resize_window` honours the outer contract. Measured against a 28px-title-bar window: `try_resize_to` now lands content at exactly 500x300 and reports success (was 500x328 + `resize hwnd failed`), and four re-centre iterations leave the window at 500x328 (was +28px each). Centring lands the frame exactly on the monitor centre, which is why the "secondary" subtraction below is **not** part of the fix — see the note in P2-1 |
> | P2-2 | fixed — `_pactl` runs with `LC_ALL=C, LANGUAGE=''`. Re-measured under `LC_ALL=de_DE.UTF-8 LANGUAGE=de`: unpinned parses `[]`, pinned parses both sink inputs. `set_mute_state` also skips a stream already in the requested state |
> | P2-3 | fixed — `activate()` polls `is_active` for 0.5s and returns that. Live: a real window returns True, `0x7fffffff` returns False (was True) |
> | P2-4 | fixed — the gate now AST-walks upstream for Win32-reaching methods and asserts each is in `vars(X11Window)`, with a test that simulates the drift the old one claimed to catch |
> | P2-5 | fixed — `_init_attributes` walks `AnnAssign` and recurses into tuple/list targets, with a test over all three shapes |
> | P2-6 | fixed — every rejected window is reported with its reason, rate-limited to once per 30s because this runs on the 0.2s poll thread (the unthrottled version emitted five lines a second for the whole time the game is not running) |
> | P2-7 | fixed, and the proposed one-liner was **not enough**. Unioning the WM_STATE walk would not have found an override-redirect window either: `WM_STATE` is a property the *WM* sets, so both source 1 and source 2 see only managed clients. The root-children source is unioned in instead, and keeps override-redirect windows. Still unverified against the real game — the live test creates its own override-redirect toplevel and asserts the WM does not list it |
> | P2-8 | fixed — and the numbers moved anyway: the file is 60 tests, 11 of them live, `49 passed, 11 skipped` with no `DISPLAY` |
> | P2-9 | fixed — `.github/workflows/linux.yml` in this repo runs the gate on `ubuntu-latest` under `xvfb-run` |
> | P2-10 | fixed — `WM_NAME` decodes as Latin-1, `_NET_WM_NAME` stays UTF-8 |
>
> Two things the fixes cost, both measured and both accepted: `list_clients` went 0.05ms ->
> 1.8ms and `find_hwnd` 0.68ms -> 2.45ms per call (~1.2% of the 0.2s poll), because the
> root-children scan is a round trip per child; and `bring_to_front` can now spend up to
> 0.5s per candidate before reporting a refusal, which is the price of the refusal being
> true. The expensive WM_STATE walk (6.0ms) stays a fallback for a non-EWMH WM.

Findings from reviewing the port implementation against `PORT.md`. Organised by the phase
that owns the code, mirroring the plan's own structure.

Everything below was **executed**, not read. Reproduction environment (already on this
machine):

```sh
V=/home/max/vsCODE/okport-venv          # python 3.12.14, ok-script-linux installed -e
$V/bin/python -m pytest tests           # from /home/max/vsCODE/ok-script-linux
```

State reviewed: ok-script-linux `c396113` (branch `linux-port`), ok-ww `3696dca` (`master`).
Session had a real KWin/Xwayland desktop (`DISPLAY=:0`), two monitors, no game running.

---

# Phase 2 — the X11 window layer

## What checks out

Every load-bearing claim in `PORT.md` §10 and in `LINUX.md`'s Phase 2 section reproduces.
Re-measured independently:

| Claim | Result |
|---|---|
| Fork suite | **419 passed / 6 failed / 1 skipped / 10 subtests** — exactly §10's number, and the 6 are §9b's Windows-only set, no new ones |
| `tests/test_x11_window.py` | **43 passed**; with `DISPLAY` unset, 35 passed / 8 skipped (see P2-8) |
| `tools/scan_module_level_win32.py --check` | exit 0 — 27 offenders, same 4 calling a loader at import |
| `tools/check_linux_imports.py` | exit 0 — **70/70** resolved |
| `tools/check_linux_startup.py` (Phase 2 exit gate) | **PASS**, and prints exactly what §10 records, including `BitBlt_True + PostMessageInteraction` and the two monitor rects |
| §10's CI arithmetic (416 passed / 3 skipped / 6 deselected) | self-consistent: the 1 local skip is `test_web_task_tabs` needing `httpx`, present in CI; the 3 CI skips are the WM-dependent live tests |
| `X11Window` really is what `DeviceManager` builds | verified via `capture.HwndWindow is x11_window.X11Window` and through the live gate |
| D7 — `activate()` de-iconifies like `ShowWindow(SW_RESTORE)` | verified live: `xdotool windowminimize` → `is_minimized True`, `WM_STATE 3`; after `x11.activate` → `is_minimized False`, `is_active True` |
| The `ok/util/window.py` shadow is complete and no wider | `capture_methods/__init__.py:23` is genuinely the only importer of the five-helper group; the 8 shadowed names all resolve to `ok.compat.window_x11` |
| `_NET_FRAME_EXTENTS` order `(left, right, top, bottom)` | correct — measured `(0, 0, 28, 0)` for a title-bar-only KWin decoration |
| Error containment | every `x11.*` entry point returns its documented empty value for a bogus window id; 4 threads × 200 iterations of `list_clients`/`get_monitors`/`find_hwnd` on the shared display: 0 errors |
| `find_hwnd` cost | 0.68 ms/call, `list_clients` 0.05 ms — comfortable inside the 0.2 s poll |

Two extra checks the plan did not ask for, both clean:

* `psutil.ZombieProcess` subclasses `psutil.NoSuchProcess`, so `_exe_candidates`' handler
  covers it — a zombie Wine helper cannot escape `find_hwnd`.
* `find_annotation_font()` (D6) resolves in 2.3 ms on this machine and early-returns on the
  first-choice CJK face; the recursive walk is not a startup cost worth worrying about.

---

## P2-1 — `resize_window` sizes the **client** rect where every caller passes **window** (outer) dimensions [correctness, fix first]

`ok/compat/window_x11.py:192` `resize_window(hwnd, width, height)`. Upstream's Windows body
(`ok/util/window.py:218-248`) is unambiguous about the contract:

```python
user32.SetWindowPos(hwnd, None, 0, 0, width, height, ...)     # SetWindowPos sizes the WINDOW rect
...
left, top, right, bottom = win32gui.GetWindowRect(hwnd)       # and the settle check reads the WINDOW rect
if n_width == width and n_height == height and ...: break
```

The Linux body uses client dimensions on **both** halves:

* `window_x11.py:212` → `x11.resize(hwnd, width, height, ...)` → `win.configure(width=..., height=...)`
  on the client window (`ok/compat/x11.py:467`).
* `window_x11.py:218` settle check compares `x11.get_abs_geometry(hwnd)[2:4]`, which is also
  the client size — so the function self-consistently reports success while the outer rect
  is wrong by exactly the frame extents.

Both callers pass outer dimensions.

**Consequence 1 — `try_resize_to` overshoots and then always reports failure.**
`ok/device/capture_methods/x11_window.py:306-323` derives `border = window_width - width`
and `title_height = window_height - height` (i.e. the frame extents, correctly), computes
`resize_width = resolution[0] + border`, and hands that outer size to `resize_window`.
Reproduced against a real KWin-decorated window (28 px title bar), asking for 500×300 of
content:

```
frame_extents (l,r,t,b): (0, 0, 28, 0)
get_window_bounds      : (2900, 512, 600, 428, 600, 400, 1.0)
border=0 title_height=28
try_resize_to computes resize_window(hwnd, 500, 328)
resize_window returned True
after get_window_bounds: (2950, 584, 500, 356, 500, 328, 1.0)
try_resize_to success test: window_height(356) == resize_height(328) -> False
CONTENT is 500x328, wanted 500x300, error 0x28
```

So the content ends up `title_height` too tall, `try_resize_to` logs
`resize hwnd failed` and returns `None`, and `start_controller.check_resolution`
(`ok/core/start_controller.py:263-268`) therefore raises the
`Resolution … check failed` alert even though the WM honoured the request.

**Consequence 2 — the re-centre path grows the window without bound.**
`ok/core/start_controller.py:312` calls
`resize_window(hwnd_window.hwnd, hwnd_window.window_width, hwnd_window.window_height)`
— outer dims again — every time `pos_valid` is False. Each call sets the client to the
previous outer size. Reproduced, same window:

```
iter 0: window=600x428  client=600x400
iter 1: window=600x456  client=600x428
iter 2: window=600x484  client=600x456
iter 3: window=600x512  client=600x484
final : window=600x540  client=600x512
```

+28 px per invocation, monotonically, until the WM clamps it.

**Reachability.** `'Auto Resize Game Window': True` is the default
(`ok/util/GlobalConfig.py:54`), and `check_resolution` runs on every start whose resolution
does not match `supported_resolution`. Dormant only while the frame extents are all zero —
i.e. a borderless-fullscreen Proton window. A *windowed* Wine game is decorated: §10's own
live evidence (`wine notepad`) recorded a 28 px title bar.

**Fix:** make `resize_window` honour the outer contract. Inside it, read
`left, right, top, bottom = x11.get_frame_extents(hwnd)` and configure the client to
`(width - left - right, height - top - bottom)`, clamping at 1; change the settle check to
compare `client + extents` against the requested `width`/`height`. Keep the `(0,0,0,0)`
case a no-op so the undecorated path is byte-identical to today.

**Also, same function, secondary:** the centring is off by the frame extents in the same
direction — requested `center_y = 556`, the client landed at `584 = 556 + 28`, because
`x11.resize` passes root-absolute coordinates that the WM applies with gravity to the
*frame*. Subtract `top`/`left` from `center_y`/`center_x` in the same patch.

> **Correction, on measurement: do not subtract.** The gravity behaviour is exactly what
> makes centring right once the *outer* dimensions are the ones being centred. ICCCM
> `win_gravity` is `NorthWest` by default, so the WM places the **frame** at the requested
> coordinates and the client lands `left`/`top` inside it. With `width`/`height` outer, the
> centred rectangle is the window rect, which is what `SetWindowPos` centres on Windows.
> Verified after the fix, same window: requested centre `(2950, 556)`, frame origin
> `(2950, 556)`, client origin `(2950, 584)`. Subtracting the extents would have moved the
> window off-centre by one title bar. Covered by
> `test_resize_window_centres_the_window_rect_not_the_client`, which skips when the WM
> draws no decorations.

**Also add a regression test.** `tests/test_x11_window.py` has no coverage of
`resize_window` against a frame-extents-bearing window — `test_resize_window_reaches_the_requested_size`
(line 776) runs against an undecorated live window, which is exactly the case where the bug
is invisible.

## P2-2 — `pactl` output is localized, so mute silently never works outside an English locale [correctness]

`ok/device/capture_methods/x11_window.py:66` `_pactl` runs `subprocess.run(('pactl',) + args, …)`
with no `env`, so pactl inherits the user's locale and translates its own output.
`_parse_sink_inputs` (line 85) matches the English literals `'Sink Input #'` (line 97) and
`'Mute:'` (line 104).

Reproduced on this machine (PipeWire's `pactl`):

```
$ pactl list sink-inputs | head -2          $ LC_ALL=de_DE.UTF-8 pactl list sink-inputs | head -2
Sink Input #72                              Ziel-Eingabe #72
	Driver: PipeWire                            Treiber: PipeWire

$ LC_ALL=zh_CN.UTF-8 pactl list sink-inputs | head -1
信宿输入 #72
```

and through the parser itself:

```
EN parsed: [('72', 0, False), ('415', 32472, False)]
DE parsed: []
```

`Mute:` becomes `Stumm:` in de_DE, so even a translated header would not save the mute flag.

Failure is **silent**: `_pactl` returns `returncode 0` and non-empty stdout, so no warning
fires; `_sink_inputs_for_hwnd` returns `[]`, `set_mute_state` iterates nothing,
`get_mute_state` returns `0`. The `Mute Game while in Background` option appears to work and
does nothing. ok-ww's primary userbase is zh_CN, which is one of the affected locales.

**Fix:** pass `env={**os.environ, 'LC_ALL': 'C', 'LANGUAGE': ''}` to `subprocess.run` in
`_pactl` (`LANGUAGE` overrides `LC_ALL` for gettext and must be cleared too). `import os` is
already needed — the module does not currently import it, so add it.

**Add a regression test:** `TestMute` (line 445) feeds captured English text only. Feed it a
localized capture as well, and assert `_pactl` builds an env that pins `LC_ALL=C`.

**Minor, same function, no action required unless convenient:** with the option on,
`handle_mute` spawns `pactl` at least twice every 2 s for the life of the run (measured
7.6 ms per `pactl list sink-inputs`, on the 0.2 s poll thread) and re-issues
`set-sink-input-mute` even when the stream is already in the requested state. Upstream's
pycaw equivalent is in-process. Skipping the write when `muted` already equals the target is
a one-line change in `set_mute_state`.

## P2-3 — `x11.activate()` can never report a refusal, so `bring_to_front()` reports success unconditionally [contract]

`ok/compat/x11.py:427`. The docstring promises *"Raise and focus. False if the WM refused"*,
and `PORT.md` §4 Phase 2 specifies the same shape. The body issues `MapWindow`, a
`_NET_ACTIVE_WINDOW` `ClientMessage` and a `ConfigureWindow` — three requests that carry no
reply — then `d.sync()` and `return True`. Errors from replyless requests are routed to
`_on_async_error` (`x11.py:81`, a `logger.debug`), never raised, so `_call` never sees them.
A WM that simply ignores the ClientMessage (KDE and GNOME focus-stealing prevention, which
the docstring itself anticipates) is indistinguishable from success.

Proven — a window id that does not exist:

```
x11.exists(0x7fffffff)   -> False
x11.activate(0x7fffffff) -> True        # and x11.resize(0x7fffffff, 100, 100) -> True
```

`X11Window.bring_to_front` (`x11_window.py:258`) guards with `x11.exists(hwnd)` first, so the
dead-window case is covered by luck rather than by the primitive; the refusal case is not
covered at all. `errors.append(f'{hwnd}: the window manager refused …')` at line 279 can
only fire when the display connection itself is lost — never for the refusal it names.

**Impact is bounded but real.** `ok/task/task.py:341` only logs on a False return, so no task
breaks today. But `PynputInteraction`, `PyDirectInteraction` and
`ForegroundPostMessageInteraction` all call `bring_to_front()` and then send input assuming
focus was granted — Phase 4's foreground fallback (§4/4d) is built on this returning the
truth.

**Fix:** after `d.sync()`, poll `is_active(wid)` for a short bounded window (the file already
has this pattern in `resize_window`'s settle loop — ~500 ms at 50 ms is ample) and return
that instead of `True`. `test_bring_to_front_reports_a_refusal_instead_of_raising`
(`tests/test_x11_window.py:425`) drives a fake and passes either way; add a live assertion
that `activate()` on a destroyed window id returns False.

## P2-4 — the method-drift gate is a tautology and can never fail [test gap]

`tests/test_x11_window.py:577` `test_every_upstream_method_is_inherited_or_overridden`:

```python
missing = [name for name in vars(HwndWindow) if not name.startswith('__')
           and not hasattr(X11Window, name)]
self.assertEqual([], missing)
```

`X11Window` subclasses `HwndWindow`, so `hasattr(X11Window, name)` is True for every name in
`vars(HwndWindow)` by definition. `missing` is `[]` unconditionally.

`LINUX.md` and `PORT.md` §10 D1 both advertise this gate as failing when upstream gains
"a method the subclass does not have" — the exact drift it is claimed to catch is invisible
to it. Proven by simulating that drift:

```
>>> HwndWindow.brand_new_win32_method = <a method that calls win32gui>
drift test would report missing = []
X11Window inherits the new win32 method: True
```

An upstream rebase that adds a Win32-calling method to `HwndWindow` therefore lands as a
silently inherited `NotImplementedError` at runtime, with a green suite.

**Fix:** invert the test. AST-walk `HwndWindow`'s method bodies for `win32api` / `win32gui` /
`win32con` / `win32process` / `ctypes` name references, and assert every method that touches
one appears in `vars(X11Window)` (i.e. is genuinely overridden, not inherited). That reads
the same way `test_the_linux_modules_call_no_win32` (line 586) already does, and it fails on
the drift that matters. Keep the `issubclass` assertion.

## P2-5 — the constructor-drift gate misses tuple and annotated assignment [test gap]

`tests/test_x11_window.py:559-566`. `_init_attributes` collects only targets that are a bare
`ast.Attribute` inside `statement.targets`:

```python
_init_attributes sees: ['a']    # for a body of  self.a = 1 / self.b, self.c = 2, 3 / self.d: int = 4
                                # -> misses b, c (ast.Tuple target) and d (ast.AnnAssign)
```

`HwndWindow.__init__` today uses only plain assignments, so the gate passes for the right
reason — by luck, not by construction. `do_update_window_size` in the same class already
uses `self.x, self.y = x, y`, so tuple assignment is idiomatic in this file and an upstream
edit could plausibly introduce it into `__init__`.

**Fix:** also walk `ast.AnnAssign` (`.target`) and recurse into `ast.Tuple`/`ast.List`
targets. Three extra lines in the same comprehension.

## P2-6 — `find_hwnd` is silent when it enumerates windows and matches none [diagnosability]

`ok/compat/window_x11.py:251-332`. The only log lines are a `debug` for ignored Win32 class
filters (line 270) and a `warning` on a `player_id` mismatch (line 304). The `exe_names`
miss at line 296 and the `pid <= 0` skip at line 290 are silent, so `find_hwnd` returning
`(None, 0, None, 0, 0, 0, 0, [])` is indistinguishable between:

* the game is not running (the normal case, correctly reported by the exit gate);
* `_NET_WM_PID` is absent (measured: `xmessage` reports `pid=0` and is invisible to
  `find_hwnd`, while `list_clients()` sees it);
* `_NET_WM_PID` resolves to a pid this process cannot see in `/proc`.

The third is not hypothetical — it is exactly **[GATE-1b]**, which `PORT.md` §2 V19 and §10
both record as still untested: under SteamLinuxRuntime/pressure-vessel the game runs in its
own PID namespace, and Phase 2's entire identity mechanism is `_NET_WM_PID` →
`psutil.Process(pid)` → command line. If that boundary bites, the user sees "game not
running" with nothing in the log to say otherwise.

**Fix:** one `logger.debug` per rejected window naming the reason (`no _NET_WM_PID`, `pid N
not resolvable`, `exe_names did not match <candidates>`), plus a single `logger.info` when
the enumeration ran, found ≥1 toplevel, and matched none. Cheap, and it is the difference
between five minutes and an afternoon when [GATE-1b] is finally tested.

## P2-7 — `list_clients()`' fallbacks are unreachable whenever `_NET_CLIENT_LIST` is non-empty [observation, NOT verified against the game]

`ok/compat/x11.py:188-206`. The three sources are tried in order, but source 1 short-circuits
on a *non-empty* list rather than on the property being absent:

```python
value = _prop(d, root.id, '_NET_CLIENT_LIST')
if value:
    return [int(w) for w in value]
```

`_NET_CLIENT_LIST` contains only windows the WM **manages**. An override-redirect toplevel is
never in it, and under a running EWMH WM the WM_STATE walk and the raw-children fallback
below can never run to find one.

**Stated honestly: I could not test this against the game.** `wine notepad` — §10's live
evidence and the case I re-ran — produces a managed window that appears in
`_NET_CLIENT_LIST` normally, and I have no Proton game to check the fullscreen path against.
So this is a shape-of-the-code observation, not a demonstrated failure. It is worth a note
because fullscreen-exclusive is the state `PORT.md` warns about in the capture layer
(`[V7]`, and `start_controller`'s own "don't use full-screen exclusive mode" string), and
because the cost of hardening is one line: union the WM_STATE walk's result into the
`_NET_CLIENT_LIST` result instead of returning early, de-duplicated. Confirm against the real
game in the same session that answers [GATE-1b] / [GATE-2].

## P2-8 — `LINUX.md`'s no-display test count is off by one [documentation]

`LINUX.md`, last paragraph: *"With no `DISPLAY` they skip (`35 passed, 7 skipped` for that
file alone)"*. Measured:

```
$ env -u DISPLAY QT_QPA_PLATFORM=offscreen python -m pytest tests/test_x11_window.py
35 passed, 8 skipped
```

Eight, which is what the same sentence says two clauses earlier (*"Eight of the 419 are live
X11 tests"*). Change `7` to `8`.

## P2-9 — nothing runs the Phase 2 exit gate [automation]

`tools/check_linux_startup.py` lives in **this** repo, because it needs ok-ww's config —
correct, and §10 says so. But every workflow here is Windows: `.github/workflows/test.yml`
and all three `build.yml` jobs are `runs-on: windows-latest`, and no workflow invokes the
gate. The fork's `.github/workflows/linux.yml` cannot run it, since the file is not in the
fork.

This is the same class of gap as G5 in the previous review, which was closed on the fork side
only. The gate is the *only* automated check that the ok-ww ⇄ ok-script-linux pair actually
starts; the fork's CI proves the fork's own suite passes, which is a weaker claim.

**Fix:** add an `ubuntu-latest` job here that installs `-r requirements-linux.txt` and runs
`xvfb-run -a python tools/check_linux_startup.py`. Note the gate hard-requires `DISPLAY`
(line 52) and calls `os._exit` (line 45), both of which are fine under `xvfb-run`.

## P2-10 — `WM_NAME` is decoded as UTF-8 though ICCCM types it `STRING` (Latin-1) [minor]

`ok/compat/x11.py:234` `get_name` falls back from `_NET_WM_NAME` (UTF-8, correct) to
`WM_NAME` and decodes both with `'utf-8', 'replace'`. A `WM_NAME` of type `STRING` is
Latin-1 per ICCCM 2.7.1, so accented titles from a client that sets only `WM_NAME` come back
mangled.

Low impact by construction: ok-ww passes `title=None`, so `find_hwnd` never matches on the
title, and `hwnd_title` is informational. Worth one line — decode `WM_NAME` as
`'latin-1'` when `_NET_WM_NAME` was absent — because it costs nothing and the function is the
one place titles enter the port.

---

# Phase 1 — re-verification

The previous review's sixteen findings (G1-G16) were re-checked where Phase 2 could have
regressed them. **No regressions, and every §9/§9b claim reproduces.** Executed:

| Claim | Result |
|---|---|
| G1 — `winreg` raises `FileNotFoundError` | holds; `LINUX.md` documents both guard styles |
| G2 — `OPTIONAL_EXTRAS` gone | holds; sweep reports 70/70, 0 skipped |
| G3 — suite stable | holds across this run and the Phase 2 run: 419/6/1, same 6 |
| G3b — do not pass `-q` | holds; the run without `-q` prints its stats line |
| G4 — Linux lock pins a commit | holds |
| G5 — fork CI runs the gates | holds (`.github/workflows/linux.yml`); **but see P2-9 — the ok-ww side still has none** |
| G9 — the win32con scan covers `tests/` | holds |
| G16 — `cv2` stays undeclared, documented in `LINUX.md` | holds; the CI workflow's comment keeps the repro in step |
| §9 C9 — the deferred half of the Phase 1 exit criterion | **now met**: `check_linux_startup.py` reaches `do_start` and selects a capture method |

One Phase 1 item Phase 2 exercised for the first time, worth recording as *confirmed
correct* rather than as a gap: the `ok/util/window.py` bottom-of-file shadow does not create
an import cycle. `ok.compat.window_x11` reaches back for `compare_path_safe` and
`get_player_id_from_cmdline` from inside function bodies only (`window_x11.py:133`, `:272`),
so either module can be imported first. Verified by importing each first in a fresh
interpreter.

---

# What shipped

All ten Phase 2 findings are closed; the table at the top of this file records each
outcome, and `PORT.md` §10b records the corrections worth keeping. What is **not** closed
is P2-7's underlying question and the two gates it belongs to: `list_clients` now
enumerates override-redirect toplevels, but no one has yet pointed it at a
fullscreen-exclusive Proton game. That belongs to the same session that answers
[GATE-1b] and [GATE-2], along with the mute path's descendant-pid fallback.

The original order, kept for the record:

# Suggested order

1. **P2-1** — the only finding that corrupts game state (an unboundedly growing window) and
   that fires on the default config. Ship the regression test with it.
2. **P2-2** — silent feature death for most of the userbase; one-line fix.
3. **P2-4**, **P2-5** — the two drift gates are what Phase 3 and every rebase will lean on;
   fixing them before Phase 3 lands is much cheaper than after.
4. **P2-3**, **P2-6** — correctness of contract and diagnosability, both needed before
   Phase 4's foreground fallback and before [GATE-1b] is tested.
5. **P2-9** — automation, before Phase 3 changes the startup path again.
6. **P2-7**, **P2-8**, **P2-10** — cheap; P2-7 stays open until the game can be driven.

None of these block Phase 3. P2-1 and P2-2 should land before it.

*(All ten landed before it, in one change: ok-script-linux `9b33a03`, plus this repo's CI
job and lock repin.)*
