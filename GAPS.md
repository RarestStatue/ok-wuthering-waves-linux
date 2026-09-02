# GAPS

> **Resolved 2026-09-01, and re-verified independently the same day.** Nine of the ten
> Phase 2 findings below were fixed, and each fix was re-measured from scratch on this
> machine's real KWin/Xwayland desktop by a second pass that trusted none of the numbers
> in this file. **P2-9 was the exception** — its workflow had never run green — and it is
> fixed now. The code fixes are in ok-script-linux `9b33a03` and `8cda739` (branch
> `linux-port`); the CI job and the lock repin are in this repo.
>
> The second pass found four more. **P2-9a and P2-13 are now fixed too** (ok-script-linux
> `8cda739` and this repo's workflow + lock repin); **P2-11 and P2-12 stay open** for the
> next model. All four are written up in
> **[Phase 2 — second pass](#phase-2--second-pass-2026-09-01)**. None of them were
> regressions from the nine fixes.
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
> | P2-8 | fixed — and the numbers moved anyway: the file is 62 tests, 13 of them live, `49 passed, 13 skipped` with no `DISPLAY` (60/11 at `9b33a03`, before P2-13 added two) |
> | P2-9 | fixed on the second attempt. The first `.github/workflows/linux.yml` was correct in shape but its only run (`33585991431`, push of `0b62a6b`) failed in 41s at `actions/checkout` — `submodules: true` cannot resolve `ok_templates`. Both `submodules` and `lfs` are dropped; see P2-9a |
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

Nine of the ten Phase 2 findings are closed; the table at the top of this file records
each outcome, and `PORT.md` §10b records the corrections worth keeping. **P2-9 is not
closed** — see P2-9a below. What is also **not** closed is P2-7's underlying question and
the two gates it belongs to: `list_clients` now enumerates override-redirect toplevels,
but no one has yet pointed it at a fullscreen-exclusive Proton game. That belongs to the
same session that answers [GATE-1b] and [GATE-2], along with the mute path's
descendant-pid fallback.

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
job and lock repin. Nine of them work; P2-9's job never ran — P2-9a.)*

---

# Phase 2 — second pass (2026-09-01)

An independent re-verification of the `9b33a03` patch set. Nothing in the table above was
taken on trust: every fix was re-driven against a live window on this machine's
KWin/Xwayland desktop, and every count was re-run. State reviewed: ok-script-linux
`9b33a03`, ok-ww `0b62a6b` (`master`), same venv (`/home/max/vsCODE/okport-venv`).

## What reproduces

| Claim | Re-measured |
|---|---|
| Fork suite `436 passed / 6 failed / 1 skipped / 10 subtests` | exact, and the 6 are §9b's Windows-only set (`test_device_manager` ×2, `test_process`, `test_task_ui`, `test_web_server` ×2) |
| `tests/test_x11_window.py` is 60 tests, 11 live | exact: `60 passed` with `DISPLAY`, `49 passed, 11 skipped` without |
| Four tests need a WM | exact: `_wm_present()` gates lines 1043, 1070, 1102, 1123 — iconify, de-iconify, and the two `resize_window` ones |
| `scan_module_level_win32.py --check` / `check_linux_imports.py` | exit 0; 27 offenders, 70/70 resolved |
| `tools/check_linux_startup.py` | `PASS startup reaches capture-method selection`, `BitBlt_True + PostMessageInteraction`, both monitor rects |
| Linux lock repinned | `requirements-linux.txt:35` → `@9b33a03d…`; `opencv-python==5.0.0.93` is pinned here, so the fork's separate opencv CI step has no ok-ww equivalent to add |
| **P2-1a** outer contract | `resize_window(wid, 500, 328)` on a 28px-title-bar window → `True`, `get_window_bounds` = `(2950, 584, 500, 328, 500, 300, 1.0)`. Window rect exactly 500x328, content exactly 500x300 |
| **P2-1b** re-centre stability | four iterations of `resize_window(hwnd, window_width, window_height)`: `(500,328,500,300)` every time. Was +28px per call |
| **P2-1c** centring | monitor `(1920,0,4480,1440)`, expected frame origin `(2950,556)`, client origin `(2950,584)`, delta `(0,28)` = `(left,top)`. The "do not subtract" correction is right |
| **P2-2** pactl locale | under `LC_ALL=de_DE.UTF-8 LANGUAGE=de`: pinned `_pactl` parses `[('72',0,False),('415',32472,False)]`, an unpinned `subprocess.run` parses `[]` with header `'Ziel-Eingabe #72'` |
| **P2-3** activate | `x11.activate(0x7fffffff)` → `False` after 0.5s with `did not grant focus` at debug; a real window → `True` in 0.00s with `is_active` True |
| **P2-4** method gate | taint analysis finds 9 Win32-bound upstream methods (`__init__`, `bring_to_front`, `do_update_window_size`, `handle_mute`, `hwnd_title`, `is_foreground`, `try_resize_to`, `update_window_size`, `validate_mute_config`); `inherited-and-tainted` is `[]`, and the 9 it leaves alone are exactly the pure ones the module docstring names |
| **P2-5** constructor gate | `{'a','b','c','d'}` over the three assignment shapes |
| **P2-6** rejection reporting | live miss logged one line naming three windows with per-window reasons, once per 30s |
| **P2-7** override-redirect | a hand-built override-redirect toplevel is in `list_clients()` and **not** in `_NET_CLIENT_LIST` |
| **P2-10** `WM_NAME` | with `_NET_WM_NAME` deleted and `WM_NAME` set to Latin-1 bytes, `get_name` → `'Wuthering Wavés'` |
| Cost | `list_clients` 1.87 ms/call, `find_hwnd` 2.88 ms/call — the table's 1.8/2.45 ms, on a desktop with a few more windows open |

## P2-9a — the Phase 2 exit-gate workflow fails at checkout and has never run the gate [automation, fix first] — **FIXED**

`.github/workflows/linux.yml` is the fix for P2-9. Its only run — `33585991431`, on the
push of `0b62a6b` — **failed in 41 seconds**, in `actions/checkout@v4`, before `pip
install` and long before the gate:

```
Submodule 'ok_templates' (…/ok-wuthering-waves-coco-labeling.git) registered for path 'ok_templates'
Cloning into '…/ok_templates'...
##[error]fatal: remote error: upload-pack: not our ref 515962cee85a1c45caaa13749f9da6c80c75efcc
##[error]fatal: Fetched in submodule path 'ok_templates', but it did not contain 515962cee85a1c45caaa13749f9da6c80c75efcc. Direct fetching of that commit failed.
##[error]The process '/usr/bin/git' failed with exit code 128
```

So P2-9's claim in the table above — "the gate runs on `ubuntu-latest` under `xvfb-run`" —
describes a job that has never executed a single line of it. Everything downstream of
checkout (the apt list, the `requirements-linux.txt` install, `xvfb-run`, the gate under
Xvfb-with-no-WM) is still unproven.

The pinned submodule commit is unreachable, not merely un-shallow-fetchable:

```
$ git ls-remote https://github.com/ok-oldking/ok-wuthering-waves-coco-labeling.git
d1b4ed8c1ca9e145c514853c14030a7358afe12c  HEAD
d1b4ed8c1ca9e145c514853c14030a7358afe12c  refs/heads/master
… (only refs/pull/*, none of them 515962ce)
```

`git submodule status` here reports `-515962ce…` — the leading `-` means never
initialized. Adding `fetch-depth` will not help: no ref on the remote reaches that commit.
This is inherited repo breakage, not something Phase 2 introduced; `build.yml` and
`test.yml` carry the same `submodules: true` and would hit it too, which is invisible only
because neither has ever run on this fork (`gh run list` returns exactly one row, the
failure above).

**Fix:** drop `submodules: true` and `lfs: true` from `.github/workflows/linux.yml`. The
gate does not need either, which is not a guess:

* `ok_templates/` is empty on this machine (the submodule was never initialized) and
  `python tools/check_linux_startup.py` still prints `PASS`. The gate stops at
  capture-method selection; template loading is a task-time concern.
* `.gitattributes` is one line (`.github/workflows/*.lock.yml linguist-generated=true
  merge=ours`) and declares no `filter=lfs`, so `lfs: true` fetches nothing.

Then push and **read the run**. A green P2-9 is the run, not the file. Do not mark P2-9
fixed again on the strength of the YAML existing — that is the exact mistake this finding
records.

> **Fixed, and it took three runs — each one exposing something the previous had hidden.**
> This is the whole argument for P2-9 in one paragraph: nothing between the first push and
> the third run was a *new* defect. All three were already true and unobservable.
>
> 1. `33587086281` — checkout passed once `submodules: true` and `lfs: true` were dropped
>    (reason recorded in a comment above the step so nobody adds them back). `Install`
>    then failed: `fatal: could not read Username for 'https://github.com'`, because
>    `RarestStatue/ok-script-linux` was **private** while ok-ww is public, so pip's
>    anonymous clone of the pinned fork commit hit a credential prompt. Resolved by making
>    the fork public — it is a fork of the already-public `ok-oldking/ok-script`, and a
>    sweep for key-shaped strings and credential-shaped filenames over the tracked tree came
>    back empty first. Verified with an anonymous `git clone` of `8cda739` from a clean
>    `GIT_CONFIG_GLOBAL=/dev/null` environment.
> 2. `33587220652` — install passed, and the gate itself failed:
>    `FAIL do_start() selected no capture method`. See P2-9b; the gate had never actually
>    passed on a clean machine.
> 3. `33587502715` — **green**, on `7bc87e5`, and it took the cold path by design:
>    `first do_start only set the preferred device; re-entering as the app does`, then
>    `do_start selected BitBlt_True + PostMessageInteraction`, then
>    `PASS  startup reaches capture-method selection` — on a runner with one monitor,
>    `(0, 0, 1280, 1024)`, under Xvfb with no window manager.

## P2-9b — the exit gate only ever passed because of leftover local state [correctness of the gate itself] — **FIXED**

The first CI run that reached `tools/check_linux_startup.py` failed on its own step 4:

```
OK    pc device pc: connected=False 0x0 (game not running, which is a valid state)
INFO  DeviceManager:first start use first or connected device {…'imei': 'pc'…}
INFO  DeviceManager:preferred device did change pc
FAIL  do_start() selected no capture method
```

`DeviceManager.do_start` (`ok/device/DeviceManager.py:651`) opens with
`preferred = self.get_preferred_device()`, and `get_preferred_device` is
`self.device_dict.get(self.config.get("preferred"))`. On a **first run there is no
`preferred`**, so `do_start` calls `set_preferred_device()`, emits `communicate.adb_devices`
and **returns, having selected nothing**. The real app recovers on the next pass, when the
UI reacts to that signal.

The gate called `do_start` exactly once. It passed on this machine only because
`configs/` is **gitignored** and `configs/devices.json` here already held
`"preferred": "pc"` from earlier runs. Deleting that one file reproduces CI byte for byte:

```
$ rm -f configs/devices.json && python tools/check_linux_startup.py
…
FAIL  do_start() selected no capture method
```

So every `PASS startup reaches capture-method selection` recorded in `PORT.md` §10, §10b
and in this file's own tables was measured on a dirty config, and the Phase 1 exit criterion
C9 that this gate was built to discharge was never actually demonstrated cold. Nothing in
the *port* is wrong — this is the gate mis-modelling first-run startup — but the claim it
was making was stronger than what it checked.

**Fixed** by driving both passes, the way the app does: if the first `do_start` selects
nothing, the gate asserts a preferred device now exists, says so, and re-enters. Verified
both ways on this machine — cold (`rm -f configs/devices.json`) it prints `first do_start
only set the preferred device; re-entering as the app does` and then `PASS`; warm it takes
the single-pass path and prints `PASS` as before.

## P2-11 — `list_clients`' new root-children source is unmeasured on a *reparenting* WM [cost/diagnosability]

Every measurement behind P2-7 was taken on this session's `kwin_wayland`, which does **not**
reparent X11 clients — verified: every id in `_NET_CLIENT_LIST` is a direct child of the
root, and `list_clients()` returned 4 ids against a `_NET_CLIENT_LIST` of 3 (the one extra
being the test's own override-redirect window). Under a *classic* reparenting WM
(`kwin_x11`, Mutter on X11, Xfwm, Openbox — all plausible for a Proton gaming session) the
root's children are the WM's **frames**, and the clients live one level down. Source 3
then adds one frame per managed window on top of source 1's clients.

Simulated by hand-building the shape (a root-child frame with the client reparented
inside it):

```
frame in list_clients : True
client in list_clients: False   # would be True via _NET_CLIENT_LIST under a real WM
…: 77594624 (''): no _NET_WM_PID
```

Not a correctness bug — the real client still arrives from `_NET_CLIENT_LIST`, and a frame
carries no `_NET_WM_PID` and no name, so it falls out at the first filter exactly as
`ok/compat/x11.py`'s docstring says. But two claims in the table above are narrower than
they read: the `1.8 ms` / `2.45 ms` costs roughly double on such a WM (one extra
`get_wm_state` + `get_name` + `get_pid` round trip per managed window), and P2-6's
rejection log gains a `no _NET_WM_PID` line per managed window, which is noise in the one
message whose whole purpose is signal.

**Fix (optional, and only if the numbers justify it — measure first on a reparenting WM):**
in `_walk_for_clients`' sibling loop in `ok/compat/x11.py:~200`, skip a root child that has
no `WM_STATE` **and** no `_NET_WM_PID` **and** whose own children include a window already
in `seen` — i.e. it is a frame around a client source 1 already gave us. Cheaper
alternative: leave the enumeration alone and drop `no _NET_WM_PID` rejects from the
`find_hwnd` message when the window is also unnamed, since an unnamed pid-less toplevel is
never the game. Either way, record the reparenting-WM measurement in `PORT.md` §10b C14,
whose cost figures currently generalise from a non-reparenting compositor.

## P2-12 — two cosmetic defects in P2-6's rejection message [diagnosability, cheap]

Both reproduced against the fakes in `tests/test_x11_window.py`.

**(a) One window can produce two reject lines.** `ok/compat/window_x11.py:~330`:

```python
candidates, cmdline = _exe_candidates(pid)
if not candidates and not cmdline:
    rejects.append(f'{hwnd} ({text!r}): pid {pid} is not resolvable in /proc')   # no `continue`
```

Control falls through into the `exe_names` branch, which appends a second line for the
same window:

```
… 20971521 ('Ghost'): pid 4242 is not resolvable in /proc; 20971521 ('Ghost'): pid 4242 [] does not match ['game.exe']
```

The first line is the real diagnosis (this is the [GATE-1b] pressure-vessel shape); the
second is noise that reads like a different window. **Fix:** `continue` after the
unresolvable-pid append. Note the message is then *only* emitted on that path, which is
what makes it worth having.

**(b) A title-only miss logs an empty reason list.** The `title` filter `continue`s after
`toplevels += 1` without appending a reject, so when every window is filtered by title the
message ends in a dangling separator:

```
"find_hwnd matched none of 1 toplevel windows (title='Wuthering Waves' exe_names=None player_id=-1): "
```

Unreachable from ok-ww today (it passes `title=None`), reachable from any other app
built on the fork. **Fix:** append a reject on the title mismatch too
(`f'{hwnd} ({text!r}): title does not match {title!r}'`), or build the message with
`'; '.join(rejects) or 'no window passed the title filter'`.

## P2-13 — `x11.resize()` has the same replyless-request lie P2-3 fixed in `activate()` [contract] — **FIXED**

`ok/compat/x11.py:512`. The docstring says *"False on refusal; the WM may clamp or ignore
either"*, and the body issues one `ConfigureWindow` — replyless, like the three P2-3
identified — then `d.sync()` and `return True`. P2-3's own evidence recorded this
(`x11.resize(0x7fffffff, 100, 100) -> True`) and the patch fixed only `activate`. Still
true at `9b33a03`:

```
x11.exists(0x7fffffff) -> False
x11.resize(0x7fffffff,100,100) -> True        # docstring says False on refusal
```

**Impact is bounded**, because `resize_window` now settles against the real geometry and
so cannot be fooled — but it pays the full timeout to find out:

```
resize_window(0x7fffffff, 500, 300) -> False, took 5.04s
```

Five seconds on the caller's thread for an answer `x11.exists()` gives in under a
millisecond. `try_resize_to` runs it inside `do_update_window_size`'s path at startup.

**Fix:** either (a) make the docstring honest — say the return value only reports that the
request was *sent*, and that the caller must read the geometry back, which is what
`resize_window` already does; or (b) guard the body with `if not exists(wid): return
False`, which costs one round trip and turns the 5.04s into ~1ms. (b) is preferable and is
the same shape as `bring_to_front`'s existing `x11.exists` guard. Do **not** make `resize`
poll the geometry itself — `resize_window` owns the settle loop and would then poll twice.

**Add a regression test** next to `test_activate_reports_a_refusal_rather_than_assuming_success`
(`tests/test_x11_window.py:1140`), asserting `x11.resize(bogus, …)` is False.

> **Fixed** in ok-script-linux `8cda739`, and option (b) is what landed — with one
> refinement: rather than calling `exists()` (a second `_call`, a second lock acquisition),
> the guard is `win.get_attributes()` at the top of `resize`'s own `run(d)`. It is
> reply-bearing, so a dead window raises `BadWindow` synchronously inside the `_call` that
> was going to happen anyway, and `_call` maps it to False. Measured after:
>
> ```
> x11.resize(0x7fffffff, 100, 100)      -> False
> resize_window(0x7fffffff, 500, 300)   -> False in 0.001s   (was False in 5.04s)
> ```
>
> Two tests, both live: `test_resizing_a_window_that_does_not_exist_fails_fast` asserts the
> False and that `resize_window` returns in under 2s, and
> `test_resizing_a_live_window_still_succeeds` asserts the guard did not turn a real resize
> into a refusal. Suite after: **438 passed, 6 failed, 1 skipped, 10 subtests**; the file is
> 62 tests, 13 live.

## Suggested order (second pass)

1. ~~**P2-9a**~~ — done. The only finding that left a *previous* finding falsely marked
   fixed, and it blocked every other CI claim.
2. ~~**P2-13**~~ — done. A 5-second stall on the startup path; one guard, two tests.
3. **P2-12** — two lines, in the message that exists to be read at 3am. **Open.**
4. **P2-11** — measure on a reparenting WM before changing anything; may turn out to be
   documentation only. **Open.**

Neither open item blocks Phase 3.

## Second-pass verification state

ok-script-linux `8cda739` (branch `linux-port`, pushed), ok-ww master with the workflow fix
and the lock repinned to `8cda739`.

* Fork suite **438 passed / 6 failed / 1 skipped / 10 subtests** — the six are §9b's
  Windows-only set, unchanged.
* `tests/test_x11_window.py`: **62 passed** with `DISPLAY`, **49 passed / 13 skipped**
  without.
* `tools/scan_module_level_win32.py --check` exit 0 (27 offenders),
  `tools/check_linux_imports.py` exit 0 (70/70), the `win32con` constant gate 4 passed.
* `tools/check_linux_startup.py` prints `PASS  startup reaches capture-method selection`
  both warm and cold (`rm -f configs/devices.json`) — and, for the first time, **in CI**:
  run `33587502715` is green end to end. That run is now the load-bearing evidence for
  Phase 1's deferred C9 criterion, which until today had only ever been demonstrated on a
  machine that had already run the app.
