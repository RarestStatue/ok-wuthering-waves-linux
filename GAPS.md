# GAPS

> **Resolved 2026-09-01, and re-verified independently the same day.** Nine of the ten
> Phase 2 findings below were fixed, and each fix was re-measured from scratch on this
> machine's real KWin/Xwayland desktop by a second pass that trusted none of the numbers
> in this file. **P2-9 was the exception** — its workflow had never run green — and it is
> fixed now. The code fixes are in ok-script-linux `9b33a03` and `8cda739` (branch
> `linux-port`); the CI job and the lock repin are in this repo.
>
> The second pass found four more. **P2-9a, P2-9b and P2-13 are now fixed too**
> (ok-script-linux `8cda739` and this repo's workflow + lock repin); P2-11 and P2-12 stayed
> open until the fourth pass below closed them. All four are written up in
> **[Phase 2 — second pass](#phase-2--second-pass-2026-09-01)**. None of them were
> regressions from the nine fixes.
>
> **Third pass, 2026-09-01 (same day): every "fixed" claim above re-verified from the
> code and re-executed; both open findings re-reproduced.** See
> **[Third pass — patch verification](#third-pass--patch-verification-2026-09-01)** for
> what was checked and how. P2-11 and P2-12 were the only work left, and both were written
> up below as drop-in patches — exact file, exact line, exact body, exact tests.
>
> **Fourth pass, 2026-09-02: both are now fixed.**
> P2-12 went in exactly as specified (`c23646d`). P2-11's blocking measurement turned out
> not to be blocked — a nested `Xwayland :9` and a ~50-line reparenting WM reproduce the
> shape with no root and no package — and it resolved to a code fix, not documentation
> (`4ca767e`). Fork suite **445 passed / 6 failed / 1 skipped**, `test_x11_window.py`
> **69 passed** (56/13 with no `DISPLAY`), every gate green including the cold startup
> gate. See **[Fourth pass](#fourth-pass--the-last-two-findings-closed-2026-09-02)**.
>
> **Fifth pass, 2026-09-02: every one of the thirteen fixes re-confirmed in the code and
> re-executed — and four findings are open again.** None is a regression.
> **[P2-14](#p2-14--is_active-is-false-for-a-focused-window-under-a-reparenting-wm-correctness--fixed)**
> is a real correctness defect four passes walked past: under a reparenting WM
> `x11.is_active()` is False for the window that holds the input focus, which inverts
> `visible`, `clickable()` and `MouseResetTask`, and makes `activate()` report a refusal of
> focus it was granted. Reproduced on a nested `Xwayland :9`, patched, measured
> (**74 / 61-13 / 450**) and reverted; the patch below is drop-in.
> **P2-15** and **P2-16** are publication gaps of exactly P2-9a's kind: the fork commit the
> Linux lock pins (`693a496`) **exists on no remote**, and ok-ww's repin commit `ec496b0` is
> **unpushed**, so no CI run has ever covered this pair. **P2-17** is inherited: `test.yml`
> and `build.yml` still carry the submodule checkout that P2-9a had to remove from
> `linux.yml`. See **[Fifth pass](#fifth-pass--phase-0-2-re-verification-2026-09-02)**.
>
> **Sixth pass, 2026-09-02: the four are closed, and one of them closed differently than
> the fifth pass predicted.** P2-14 went in exactly as specified (ok-script-linux
> `f41745b`) — `74 passed`, `61 passed / 13 skipped` with no `DISPLAY`, fork suite
> `450 passed`, and the nested-`Xwayland` control flipped `0x200000` (frame) to `0x200001`
> (client), `is_active` False to True, `activate` `False in 0.51s` to `True in 0.00s`.
> P2-15 and P2-16 are one push each: `linux-port` is now `12e297c` on the remote, the lock
> pins it, the pin is fetchable with no credentials, and run **33669383034** on `6fac179`
> is green — the first CI evidence for this pair. **P2-17's recommended option (a)
> is disproven** — `test.yml` and `build.yml`'s first job both run `tests\*.py`, and seven
> of those tests load `ok_templates/*.png`, so dropping `submodules: true` trades a
> checkout failure for a test failure. Only a repin fixes those workflows, and that is the
> templates owner's call; nothing was changed. See
> **[Sixth pass](#sixth-pass--the-fifth-passs-four-closed-2026-09-02)**.
>
> **Seventh pass, 2026-09-02: the first review of Phase 3, and Phases 0-2 re-verified
> against the tree it landed on.** Nothing regressed — 484 passed / 6 failed / 1 skipped in
> the fork, 108 in the two X11 files, all three drift gates and the startup gate green, and
> both repos' CI green on this exact pair (`493354a` ⇄ `ed8813a`). §11's measurements
> reproduce, including the copy contract, the colour order and zero leaked SHM segments.
> **Seven findings, all in Phase 3.**
> [P3-1](#p3-1--a-depth-30-10-bit-visual-is-decoded-as-8-bit-silently-correctness-fix-first--fixed)
> is a silently wrong picture on a 10-bit visual — latent on this machine, and the exact
> failure mode `xshm.py`'s own docstring exists to prevent.
> [P3-2](#p3-2--minimizing-the-game-disables-the-running-task-instead-of-pausing-it-correctness--fixed)
> is the one that bites today: the minimized-window `CaptureException` §4 asked for reaches
> `TaskExecutor.py:639` and is answered with `task.disable()`, so minimizing the game
> switches the task off instead of pausing it — a Linux-only behaviour change, and the
> window layer's own pause already does the job reversibly.
> **P3-3** lets a dead `DISPLAY` through the availability guard, **P3-4** has `get_name()`
> claiming a composite path that silently fell back, **P3-5** is an unverified observation
> about the letterbox crop, and **P3-6**/**P3-7** are documentation. See
> **[Seventh pass](#seventh-pass--phase-0-3-review-2026-09-02)**.
>
> **Eighth pass, 2026-09-02: six of the seven are fixed.** P3-1, P3-2, P3-3 and P3-4 are
> code (ok-script-linux `9a53b14`, tightened by `5f1987e`), P3-6 and P3-7 are the documents
> they asked for. Fork suite **491 passed / 6 failed / 1 skipped / 16 subtests**,
> `test_x11_capture.py` **41 passed** (was 34), **92 / 23** with no `DISPLAY`,
> `test_x11_window.py` **74 passed** unchanged, both drift gates exit 0 and the startup gate
> is `PASS`. Mid grey on a 10-bit visual goes `[0, 2, 8]` -> `[128, 128, 128]`; a minimized
> window returns `None` instead of a `CaptureException` that `TaskExecutor.py:644` answered
> with `task.disable()`; `DISPLAY=:99` is no longer "available" and logs one ERROR instead
> of one per grab; and `get_name()` reads the path actually taken.
> **P3-5 is deliberately not patched** — it needs the game running, and the game was not
> running for this pass either. See
> **[Eighth pass](#eighth-pass--the-seventh-passs-phase-3-findings-closed-2026-09-02)**.
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
> | P2-11 | fixed — measured on a nested `Xwayland :9` under a purpose-written reparenting WM (10 clients): `find_hwnd` 3.17ms non-reparenting, 5.28ms reparenting, **3.93ms** after the fix, and 10 pure-noise `no _NET_WM_PID` reject lines gone. `list_clients` drops a frame whose child it already has, and only that shape, so P2-7's override-redirect window survives |
> | P2-12 | fixed — an unresolvable pid reports once instead of twice, and a title-only miss says which title did not match instead of ending on a dangling `: ` |
> | P2-14 | fixed — `get_focus_toplevel` resolves focus through ICCCM `WM_STATE` (`_client_window`), with the root's child kept as the no-WM fallback and one level of descent for a frame-focusing WM. Live control on a nested `Xwayland :9`: frame `0x200000` -> client `0x200001`, `is_active` False -> True, `activate` `False in 0.51s` -> `True in 0.00s`. ok-script-linux `f41745b`, five new unit tests |
> | P2-15 | fixed — `linux-port` pushed; `origin/linux-port` is `12e297c` and the lock pins it. Confirmed fetchable with no credentials (`GIT_CONFIG_GLOBAL=/dev/null git -c credential.helper= ls-remote`), which is how pip clones it |
> | P2-16 | fixed — ok-ww `master` pushed with the repin. `Linux startup gate` run **33669383034** on `6fac179` is `success`, the first CI evidence for the `6fac179` ⇄ `12e297c` pair; both `do_start` passes are in its log |
> | P2-17 | **open, inherited, and not ours to close** — the fifth pass's option (a) is disproven: both workflows run `tests\*.py`, and seven of those tests read `ok_templates/*.png`, so dropping `submodules` only moves the failure. Repinning the submodule is the templates owner's call; recorded, not changed |
> | P3-1 | fixed — `_channel_fields` carries each mask's *width*, `_channel_indices` is `None` for a channel that is not 8 bits wide, and `_unpack_wide` decodes it. All six 10-bit probes correct, mid grey `[0, 2, 8]` -> `[128, 128, 128]`, MSBFirst control correct, and depth 24 still takes the `cv2.cvtColor` fast path (a test, not a comment) |
> | P3-2 | fixed — `do_get_frame` returns `None` for a minimized window and logs once per episode. The `CaptureException` that reached `TaskExecutor.py:644` -> `task.disable()` is gone, and the window layer's reversible pause is now the whole story. The live iconify test asserts `None` and its stale-frame half is unchanged |
> | P3-3 | fixed — `x11_capture_available()` is `xshm.available() and x11.available()`, and `_open`'s failures log once. `DISPLAY=:99` re-measured: `False` (was `True`), one ERROR for three grabs (was three) |
> | P3-4 | fixed — `X11Grabber.composite_active` is the path actually taken, `get_name()` reads it, and `update_capture_method` switches through the new `use_composite_path` instead of waiting for the next frame. Live: direct 1.78 ms / composite 1.68 ms, both `[153, 102, 51]` |
> | P3-5 | **open, observation, not verified against the game** — `get_crop_point`'s vertical slack is a Windows title bar; in Linux client coordinates it takes the whole letterbox off the top. Unreachable at 16:9. Deliberately not patched: the game was not running for the eighth pass either |
> | P3-6 | fixed — `LINUX.md` gains a **System libraries** subsection: Fedora `libX11`/`libXext`/`libXcomposite`, Debian `libx11-6`/`libxext6`/`libxcomposite1`, and what their absence costs |
> | P3-7 | fixed — the step is now `Phase 2-3 exit gate` |
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

## P2-11 — `list_clients`' new root-children source is unmeasured on a *reparenting* WM [cost/diagnosability] — **MEASURED AND FIXED**

> **Closed 2026-09-02 (fourth pass).** The blocking measurement was taken — not by
> installing a reparenting WM, which still is not possible here, but by writing one
> against a nested `Xwayland :9`. Outcome **2** of the three below: the cost and the log
> noise both turned out to be real, and one predicate removes both. ok-script-linux
> `4ca767e`. Numbers, the harness, and why the two obvious predicates are wrong are in
> **[Fourth pass](#fourth-pass--the-last-two-findings-closed-2026-09-02)**.

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

> **Correction, third pass: the fix location named in the original write-up was wrong.**
> It said "`_walk_for_clients`' sibling loop in `ok/compat/x11.py:~200`". That is
> **source 2**, not source 3: `_walk_for_clients` is at `x11.py:161` and only runs when
> `_NET_CLIENT_LIST` is absent or empty (`x11.py:216-221`), which is never the case on a
> WM that has this problem. **Source 3 — the one that adds the frames — is the root-children
> loop inside `list_clients` itself, `ok/compat/x11.py:223-232`:**
>
> ```python
>         for child in root.query_tree().children:
>             if child.id in seen:
>                 continue
>             try:
>                 attributes = child.get_attributes()
>                 if (attributes.map_state == Xlib.X.IsViewable
>                         and attributes.win_class == Xlib.X.InputOutput):
>                     add(child.id)
>             except Exception:
>                 continue
> ```
>
> `seen` is the local set built by `add()` a few lines above (`x11.py:210-215`), already
> holding every id from sources 1 and 2, so the "is this a frame around a client we
> already have" test is `any(c.id in seen for c in child.query_tree().children)` — no
> extra bookkeeping needed. Note the loop skips `child.id in seen` first, which is why a
> *non*-reparenting WM is unaffected: there the clients themselves are the root's children
> and are already in `seen`.

**Measure before changing anything. Nothing here is measured yet, and this machine cannot
measure it:** the session is `kwin_wayland --xwayland` (KDE/Wayland), which does not
reparent, and **no reparenting WM and no nested/virtual X server is installed** — checked
2026-09-01 for `openbox`, `xfwm4`, `marco`, `metacity`, `mutter`, `i3`, `fluxbox`, `jwm`,
`icewm`, `twm`, `blackbox`, `Xephyr`, `Xvfb`; none present. So step 1 is to install one
(`sudo dnf install xorg-x11-server-Xephyr openbox` on this Fedora box), then:

```sh
Xephyr :9 -screen 1280x1024 &
DISPLAY=:9 openbox &
DISPLAY=:9 xterm &                      # or any client, to give the WM something to frame
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
DISPLAY=:9 $V/bin/python - <<'EOF'
import subprocess, time
from ok.compat import x11
clients = x11.list_clients()
print('list_clients  ', [hex(w) for w in clients], len(clients))
print(subprocess.run(['xprop', '-root', '_NET_CLIENT_LIST'],
                     capture_output=True, text=True).stdout.strip())
for wid in clients:
    print(hex(wid), 'wm_state', x11.get_wm_state(wid), 'pid', x11.get_pid(wid),
          'name', repr(x11.get_name(wid)))
t = time.time()
for _ in range(50):
    x11.list_clients()
print(f'list_clients {(time.time()-t)/50*1000:.2f} ms/call')
EOF
```

There is **no** `x11.get_root()` — `_NET_CLIENT_LIST` is read off the root inside
`list_clients` and is not exposed, which is why the snippet shells out to `xprop`. The
comparison that matters is `len(list_clients())` against the number of ids `xprop` prints
(the surplus is the frames), plus the per-call cost. Every helper used above exists at
`8cda739`: `get_property:155`, `get_pid:247`, `get_wm_state:315`, `get_name:261`.
This exact snippet was run on the non-reparenting session and works.

For reference, the same measurement on this non-reparenting session, third pass:
`list_clients` **2.10 ms/call** with 2 clients. The write-up's prediction is that a
reparenting WM roughly doubles the per-managed-window cost and adds one
`no _NET_WM_PID` line per managed window to P2-6's message.

**Then, and only then, one of three outcomes:**

1. Cost is unchanged in practice (few toplevels) → **documentation only**: record the
   reparenting-WM number in `PORT.md` §10b C14, whose cost figures currently generalise
   from a non-reparenting compositor, and close this finding.
2. Cost matters → skip frames in the `x11.py:223-232` loop, per the corrected code
   location above.
3. Only the log noise matters → leave the enumeration alone and drop `no _NET_WM_PID`
   rejects from `find_hwnd`'s message (`ok/compat/window_x11.py:331`) when the window is
   also unnamed, since an unnamed pid-less toplevel is never the game.

**Whichever is chosen, do not regress P2-7.** `tests/test_x11_window.py` has a live test
that hand-builds an override-redirect toplevel and asserts it is in `list_clients()` and
not in `_NET_CLIENT_LIST`; an override-redirect window has no `WM_STATE` and no
`_NET_WM_PID` either, so a frame-skip predicate that omits the "its children are already
in `seen`" clause will delete exactly the window P2-7 was fixed to find.

## P2-12 — two cosmetic defects in P2-6's rejection message [diagnosability, cheap] — **FIXED**

Both re-reproduced on 2026-09-01 (third pass) against ok-script-linux `8cda739`, using
`tests/test_x11_window.py`'s own `FakeX11` harness. Verbatim output of both repros is
below; the exact patch and the exact tests follow. All line numbers are `8cda739`.

**File:** `/home/max/vsCODE/ok-script-linux/ok/compat/window_x11.py`, inside
`find_hwnd` (`def find_hwnd` at line **282**; the reject-collecting loop is lines
**313-372**).

### (a) One window produces two reject lines

`window_x11.py:333-336` today:

```python
        candidates, cmdline = _exe_candidates(pid)
        if not candidates and not cmdline:
            rejects.append(f'{hwnd} ({text!r}): pid {pid} is not resolvable in /proc')

        if exe_names:
```

There is no `continue`, so control falls into the `exe_names` branch (line 337) and
appends a second line for the same window. Reproduced — one window, `pid=4242`
unresolvable, `exe_names=['game.exe']`:

```
find_hwnd matched none of 1 toplevel windows (title=None exe_names=['game.exe'] player_id=-1): 20971521 ('Ghost'): pid 4242 is not resolvable in /proc; 20971521 ('Ghost'): pid 4242 [] does not match ['game.exe']
```

The first line is the real diagnosis — this is the [GATE-1b] pressure-vessel shape. The
second reads like a different window.

**Do not add a bare `continue`.** It would be a behaviour change, not a cosmetic one:
when `exe_names` is falsy the `elif candidates:` / `else` arms at lines 343-346 let a
window with an unresolvable pid still match with `name, full_path = "", ""`. ok-ww always
passes `exe_names`, but the fork is a library and other apps do not have to. Guard the
skip on `exe_names` being truthy, where it is provably a no-op (an unresolvable pid has
no candidates, so `_match_exe_names` returns `None` and the loop was going to `continue`
one branch later anyway):

```python
        candidates, cmdline = _exe_candidates(pid)
        if not candidates and not cmdline:
            rejects.append(f'{hwnd} ({text!r}): pid {pid} is not resolvable in /proc')
            if exe_names:
                # An unresolvable pid can never match `exe_names`, and the generic
                # "does not match []" line below would then report the same window twice
                # with the weaker of the two reasons. Skipping here is a no-op for the
                # match itself. With `exe_names` unset the window is still a candidate
                # (`name`/`full_path` fall back to ''), so do not skip it there.
                continue

        if exe_names:
```

### (b) A title-only miss logs an empty reason list

`window_x11.py:322-327` `continue`s on a title mismatch after `toplevels += 1` (line 319)
without appending a reject, so when every window is filtered by title `rejects` is empty
and `'; '.join(rejects)` leaves a dangling separator. Reproduced — one window named
`'Other'`, `title='Wuthering Waves'`, `exe_names=None`:

```
"find_hwnd matched none of 1 toplevel windows (title='Wuthering Waves' exe_names=None player_id=-1): "
```

Unreachable from ok-ww today (`X11Window.__init__` passes `title=None`; confirmed at
`ok/device/capture_methods/x11_window.py`), reachable from any other app on the fork.
Replace lines **322-327**:

```python
        if title:
            if isinstance(title, str):
                title_matched = title == text
            else:
                title_matched = bool(re.search(title, text))
            if not title_matched:
                rejects.append(f'{hwnd} ({text!r}): title does not match {title!r}')
                continue
```

and make the join defensive at line **372**, so no future filter can reintroduce the
dangling separator:

```python
                        + ('; '.join(rejects) or 'no window passed the filters'))
```

`re` is already imported (`window_x11.py:1-45`); `title` may be a `str` or a compiled
pattern — that is upstream's contract and the rewrite preserves both arms exactly.

### Tests to add

In `tests/test_x11_window.py`, class `TestFindHwnd` (line **136**), immediately after
`test_a_miss_says_why_once_rather_than_five_times_a_second` (lines **244-265**) and
before `test_player_id_filters_on_the_command_line` (line **267**). `run_find` (line
**141**) does not capture the log, so these use the same explicit `mock.patch` shape as
the P2-6 test above them — including `_last_no_match_log=0`, without which the 30s
rate limit swallows the second test's message.

```python
    def test_an_unresolvable_pid_is_reported_once_not_twice(self):
        """[P2-12a] The pressure-vessel shape [GATE-1b] is the diagnosis; the generic
        `does not match` line for the same window is noise that reads like another one."""
        from ok.compat import window_x11
        fake = FakeX11([FakeWindow(0x1400001, pid=4242, name='Ghost')])

        with unittest.mock.patch.object(window_x11, 'x11', fake), \
                unittest.mock.patch.object(window_x11, '_exe_candidates', return_value=([], [])), \
                unittest.mock.patch.object(window_x11, '_last_no_match_log', 0), \
                unittest.mock.patch.object(window_x11.logger, 'info') as info:
            self.assertEqual(0, window_x11.find_hwnd(None, ['game.exe'], 0, 0)[1])

        message = info.call_args[0][0]
        self.assertIn('pid 4242 is not resolvable in /proc', message)
        self.assertNotIn('does not match', message)
        self.assertEqual(1, message.count('20971521'), 'one window, one reject line')

    def test_an_unresolvable_pid_still_matches_when_no_exe_names_are_given(self):
        """[P2-12a] The skip must not change matching: with `exe_names` unset a window
        whose pid is invisible in /proc is still a candidate, with an empty path. A title
        is required because `find_hwnd` returns a miss outright when both filters are
        None (`window_x11.py:296`)."""
        from ok.compat import window_x11
        fake = FakeX11([FakeWindow(0x1400001, pid=4242, name='Ghost', geometry=(0, 0, 800, 600))])

        with unittest.mock.patch.object(window_x11, 'x11', fake), \
                unittest.mock.patch.object(window_x11, '_exe_candidates', return_value=([], [])):
            name, hwnd, full_path = window_x11.find_hwnd('Ghost', None, 0, 0)[:3]

        self.assertEqual(0x1400001, hwnd)
        self.assertEqual('Ghost', name)
        self.assertEqual('', full_path)

    def test_a_title_only_miss_says_which_title_did_not_match(self):
        """[P2-12b] Every window filtered by title left `rejects` empty, so the message
        ended in a dangling `: `."""
        from ok.compat import window_x11
        fake = FakeX11([FakeWindow(0x1400001, pid=4242, name='Other')])

        with unittest.mock.patch.object(window_x11, 'x11', fake), \
                unittest.mock.patch.object(window_x11, '_exe_candidates',
                                           return_value=([('game.exe', '/g/game.exe')], [])), \
                unittest.mock.patch.object(window_x11, '_last_no_match_log', 0), \
                unittest.mock.patch.object(window_x11.logger, 'info') as info:
            self.assertEqual(0, window_x11.find_hwnd('Wuthering Waves', None, 0, 0)[1])

        message = info.call_args[0][0]
        self.assertFalse(message.endswith(': '), 'the reason list must never be empty')
        self.assertIn("title does not match 'Wuthering Waves'", message)
```

### Verification — this whole patch was applied and run before being written down

Not a proposal: the three code edits and the three tests above were applied to a working
copy of `8cda739` on 2026-09-01, measured, and then reverted (the fork tree is clean at
`8cda739`). Expected results, all observed:

```sh
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
$V/bin/python -m pytest tests/test_x11_window.py     # 62 today -> 65 passed with the patch
$V/bin/python -m pytest tests                        # 441 passed, 6 failed, 1 skipped, 10 subtests
```

And the check that makes them regression tests rather than decoration — with the **tests
applied but `window_x11.py` reverted**:

```
FAILED tests/test_x11_window.py::TestFindHwnd::test_a_title_only_miss_says_which_title_did_not_match
FAILED tests/test_x11_window.py::TestFindHwnd::test_an_unresolvable_pid_is_reported_once_not_twice
2 failed, 63 passed
```

`test_an_unresolvable_pid_still_matches_when_no_exe_names_are_given` passes **both**
before and after, by design: it is the guard on the behaviour change, not on the fix.

The six failures are §9b's Windows-only set (`test_device_manager` ×2, `test_process`,
`test_task_ui`, `test_web_server` ×2) and must stay exactly those six. No ok-ww code change
is needed — but if this lands on the fork's `linux-port` branch,
`requirements-linux.txt:35` pins `@8cda7398…` and **must be repinned** to the new commit,
or CI keeps testing the old tree (that is P2-9a's whole lesson).

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
2. ~~**P2-9b**~~ — done. The gate had only ever passed on a dirty config.
3. ~~**P2-13**~~ — done. A 5-second stall on the startup path; one guard, two tests.
4. ~~**P2-12**~~ — done (`c23646d`). Applied exactly as specified above; all three tests
   behaved as predicted, including the one that passes before *and* after.
5. ~~**P2-11**~~ — done (`4ca767e`). The measurement was not blocked after all: a nested
   `Xwayland :9` plus a ~50-line reparenting WM reproduces the shape with no root and no
   package. It resolved to outcome 2, not documentation.

Phase 2 has no open findings *from the first four passes*, and Phase 3 was never blocked by
any of them. (The fifth pass reopened it: P2-14 through P2-17.)

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

---

# Third pass — patch verification (2026-09-01)

An independent check of the claims in this file's own tables: does the code actually
contain each fix, and does it behave that way when run. State: ok-script-linux `8cda739`
(branch `linux-port`), ok-ww `ca80c6c` (`master`), `requirements-linux.txt:35` pinned to
`@8cda7398…` — the pin and the fork HEAD agree. Same venv (`/home/max/vsCODE/okport-venv`),
same KWin/Xwayland desktop, two monitors, no game running.

**Result: eleven of the thirteen findings are genuinely closed in code and confirmed by
execution. P2-11 and P2-12 remain open, exactly as this file says.** Nothing was found to
be marked fixed that is not.

| Finding | Where the fix is, at `8cda739` | Confirmed by |
|---|---|---|
| P2-1 | `ok/compat/window_x11.py:198` `resize_window` — subtracts `get_frame_extents` to get the client size, settles on `client + extents == requested`, centres the *outer* rect with a comment recording the win_gravity reasoning | code read; the two live `resize_window` tests pass |
| P2-2 | `x11_window.py:67` `_pactl_env()` returns `{**os.environ, 'LC_ALL': 'C', 'LANGUAGE': ''}`; `import os` present at line 32; `set_mute_state` skips a stream already at the target | code read |
| P2-3 | `ok/compat/x11.py:462` `activate(wid, timeout=0.5)` polls `is_active` and returns it | live: `activate(0x7fffffff)` → **False** after 0.5s, with `activate 2147483647: the window manager did not grant focus within 0.5s` at debug |
| P2-4 / P2-5 | `tests/test_x11_window.py:756` recurses `ast.Tuple`/`ast.List`, `:772` handles `ast.AnnAssign`/`ast.AugAssign`; `:865` asserts `{'a','b','c','d'}` | test run |
| P2-6 | `window_x11.py:313-372` — `rejects` list, `_NO_MATCH_LOG_INTERVAL = 30` at line 44 | test run, and the two repros below |
| P2-7 | `x11.py:176` `list_clients` unions all three sources; source 3 (`:223`) keeps override-redirect windows; source 2 is the fallback | code read; live `list_clients` returns ids `_NET_CLIENT_LIST` does not have |
| P2-8 | `LINUX.md:228` now reads `49 passed, 13 skipped` | measured: `62 passed` with `DISPLAY`, `49 passed, 13 skipped` without |
| P2-9 / P2-9a | `.github/workflows/linux.yml` — no `submodules`, no `lfs`, with the reason in a comment above the step | `gh run list`: **two green runs**, `33587502715` and `33587618601`, after three failures |
| P2-9b | `tools/check_linux_startup.py:90-114` drives both `do_start` passes | run cold (`rm -f configs/devices.json`): `first do_start only set the preferred device; re-entering as the app does` → `do_start selected BitBlt_True + PostMessageInteraction` → `PASS`, exit 0 |
| P2-10 | `x11.py:261` `get_name` decodes `WM_NAME` as `latin-1`, `_NET_WM_NAME` as `utf-8` | code read |
| P2-13 | `x11.py:512` `resize` calls `win.get_attributes()` — reply-bearing — before `configure` | live: `x11.resize(0x7fffffff,100,100)` → **False in 0.000s**; `resize_window(0x7fffffff,500,300)` → **False in 0.000s** (was 5.04s) |
| P2-11 | **not fixed, and correctly so** — it is a measurement, not a patch | see the correction in P2-11: this machine has no reparenting WM to measure on |
| P2-12 | **not fixed** — `window_x11.py:335` still has no `continue`; the title filter at `:322-327` still appends no reject | both re-reproduced verbatim, see P2-12 |

P2-12's patch was not merely specified — it was applied to a working copy, run
(`441 passed, 6 failed`), shown to fail 2/3 of its new tests without the code change, and
reverted. One error in the first draft of that spec was caught this way and corrected in
place: `find_hwnd` returns a miss immediately when `title` **and** `exe_names` are both
None (`window_x11.py:296`), so the behaviour-preservation test has to pass a title.

Costs re-measured on this desktop: `list_clients` **2.10 ms/call** (2 clients). Consistent
with the second pass's 1.87 ms and the first pass's 1.8 ms; the variance is how many
windows are open, which is the point P2-11 makes.

One correction to this file itself, made above rather than left for the reader: **P2-11's
"Fix" named the wrong function.** It pointed at `_walk_for_clients` (source 2, `x11.py:161`,
which cannot run on a WM that publishes `_NET_CLIENT_LIST`) instead of the root-children
loop in `list_clients` (source 3, `x11.py:223-232`, which is what adds the frames). An
implementer following the original text would have patched dead code and measured no
change. P2-11 now carries the corrected location, the `seen`-based predicate, a runnable
measurement recipe, and the warning that a careless frame-skip deletes the
override-redirect window P2-7 exists to find.

## How to re-run this verification

```sh
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
$V/bin/python -m pytest tests/test_x11_window.py                 # 62 passed
env -u DISPLAY QT_QPA_PLATFORM=offscreen $V/bin/python -m pytest tests/test_x11_window.py
                                                                 # 49 passed, 13 skipped
$V/bin/python -m pytest tests                                    # 438 passed, 6 failed, 1 skipped
$V/bin/python tools/scan_module_level_win32.py --check           # exit 0
$V/bin/python tools/check_linux_imports.py                       # exit 0, 70/70

cd /home/max/vsCODE/ok-wuthering-waves-linux
rm -f configs/devices.json && $V/bin/python tools/check_linux_startup.py   # PASS, cold
gh run list --limit 5                                            # top two rows green
```

The six failures are §9b's Windows-only set and must stay six. `configs/devices.json` is
gitignored and is regenerated by the gate run — deleting it is the cold-start test, not a
destructive act.

---

# Fourth pass — the last two findings closed (2026-09-02)

Both remaining findings are fixed, on ok-script-linux branch `linux-port-p2-11-12`:
**P2-12 `c23646d`**, **P2-11 `4ca767e`**. State going in: ok-script-linux `8cda739`, ok-ww
`ca80c6c`, same venv (`/home/max/vsCODE/okport-venv`), same KWin/Xwayland desktop, no game
running. **Phase 2 had no open findings at this point** — the fifth pass below reopened it
with P2-14 through P2-17.

## P2-12 — applied exactly as the third pass specified

The write-up above was a drop-in patch and behaved as one. Nothing in it needed correcting.

* Both defects reproduced first, verbatim, against `8cda739`.
* The three code edits and three tests went in unchanged.
* `tests/test_x11_window.py`: **62 → 65 passed**.
* The negative control the spec asked for: with the tests applied and `window_x11.py`
  reverted, exactly `test_a_title_only_miss_says_which_title_did_not_match` and
  `test_an_unresolvable_pid_is_reported_once_not_twice` fail — `2 failed, 63 passed` —
  and `test_an_unresolvable_pid_still_matches_when_no_exe_names_are_given` passes both
  before and after, which is its job.

## P2-11 — the measurement was not blocked; the assumption was

Three passes recorded this as blocked on hardware/packages: `kwin_wayland` does not
reparent, and none of Xephyr, Xvfb, Xnest, openbox, xfwm4, mutter, marco, metacity, i3,
fluxbox, icewm, jwm, twm, blackbox or even xterm is installed — re-checked 2026-09-02,
still none, and installing needs root.

The unstated assumption was that measuring a reparenting WM means *installing* one. Two
things make that false:

1. **`Xwayland :9 -geometry 1000x700`** is already on this box (the session runs it) and
   gives a nested rootful X server inside the existing Wayland session — no root, no
   package, and nothing touching the user's real `:0`.
2. **A window manager is just an X client.** Select `SubstructureRedirect` on the root;
   on each `MapRequest` create a frame window, `reparent` the client into it, map both,
   set `WM_STATE` on the client and publish `_NET_CLIENT_LIST`. ~50 lines of python-xlib.
   Behind a `--reparent` flag, the same harness produces *both* shapes against the same
   server and the same clients — which is the comparison the finding actually needed. The
   absolute milliseconds are from a nested server and are not the session's; the columns
   are.

### What it measured

10 managed clients, each with a real `_NET_WM_PID` and a name; `--reparent` the only
difference between columns 1 and 2:

| | non-reparenting | reparenting, `8cda739` | reparenting, `4ca767e` |
|---|---|---|---|
| `find_hwnd` | 3.17 ms/call | 5.28 ms/call | **3.93 ms/call** |
| `list_clients` | 0.11 ms/call | 0.53 ms/call | 1.00 ms/call |
| ids returned | 10 | 20 (10 frames) | 10 |
| `no _NET_WM_PID` reject lines in P2-6's message | 0 | 10 | 0 |

At 3 clients the same shape: `find_hwnd` 1.02 → 1.66 → 1.28 ms, surplus 3 → 0. And the
non-reparenting column is byte-for-byte unchanged by the fix (3.17 → 3.17 ms), because
there the clients are the root's own children and are skipped by `child.id in seen` before
the new predicate is reached.

So P2-11's prediction held in shape and sign — "roughly doubles, plus one noise line per
managed window" — and the answer to its three-way question is **outcome 2**, not outcome 1.
The cost alone would have been arguable (~2% of the 0.2s poll); the cost *plus* one
pure-noise line per managed window in the one message whose whole purpose is signal is not.
Outcome 3 was rejected because it treats the symptom in `find_hwnd`'s message while
`list_clients` keeps paying three round trips per frame.

### The fix, and why the two obvious predicates are wrong

`ok/compat/x11.py`, a new `_frames_a_known_client(child, seen)` called from the
root-children loop — the location the third pass corrected this finding to.

```python
    try:
        return any(c.id in seen for c in child.query_tree().children)
    except Exception:
        return False
```

A real WM's frames **are** override-redirect, unnamed and pid-less, so every predicate of
the form "skip override-redirect" / "skip unnamed" / "skip pid-less" also deletes the
override-redirect toplevel P2-7 exists to find — a fullscreen-exclusive Wine window is
exactly that shape. The separating test is positional: *does this window contain a client
we already have.* `seen` already holds sources 1 and 2, so it needs no extra bookkeeping,
and an override-redirect toplevel has no child in `seen` because nothing else in the tree
holds it.

The trade is explicit in the table: `list_clients` **alone** gets slower — one `QueryTree`
per frame is a round trip the old loop did not make — and buys back three per managed
window in `find_hwnd`, the call that runs on the 0.2s poll thread. Both callers of
`list_clients` (`find_hwnd`, `find_all_visible_windows`) filter by name or pid and were
paying for the frames either way.

Four unit tests (`TestFrameSkip`), no display needed: a frame, an override-redirect
toplevel, a toplevel whose children are all unknown (the bare-X-server/Xvfb case), and a
window destroyed mid-walk. The predicate is unit-tested rather than driven live precisely
because neither this desktop nor CI is a reparenting WM.

## Verification state (fourth pass)

| Check | Result |
|---|---|
| `pytest tests` (fork) | **445 passed / 6 failed / 1 skipped / 10 subtests** — the six are §9b's Windows-only set, unchanged |
| `pytest tests/test_x11_window.py` | **69 passed** (was 62) |
| same, `env -u DISPLAY QT_QPA_PLATFORM=offscreen` | **56 passed / 13 skipped** (was 49/13) |
| `tools/scan_module_level_win32.py --check` | exit 0 |
| `tools/check_linux_imports.py` | exit 0, 70/70 |
| `tools/check_linux_startup.py`, cold (`rm -f configs/devices.json`) | `PASS  startup reaches capture-method selection`, `BitBlt_True + PostMessageInteraction`, exit 0 |
| live P2-7 override-redirect test on the real desktop | passes — the regression that mattered |

Docs moved with the code: `LINUX.md` 62 → 69 tests, 438 → 445 suite, `49 passed, 13 skipped`
→ `56 passed, 13 skipped`; `PORT.md` §10c is new (C20-C22) and §10b C14 now carries the
reparenting-WM numbers it had generalised past.

And P2-9a's lesson, applied without being asked: the two commits are merged to the fork's
`linux-port` as **`693a496`**, and `requirements-linux.txt:35` is repinned from
`@8cda7398…` to `@693a4961…`. A lock left on the old commit means CI keeps testing the old
tree and every green run says nothing about these fixes.

## Reproducing the reparenting measurement

The harness is three short scripts; they are not committed, because a window manager in
`tools/` would be odd. Recreate them from the description above, or:

```sh
Xwayland :9 -geometry 1000x700 &                 # nested, rootful, no root needed
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
DISPLAY=:9 $V/bin/python miniwm.py --reparent &  # omit the flag for the flat shape
DISPLAY=:9 $V/bin/python clients.py 10 &
DISPLAY=:9 $V/bin/python measure.py 'REPARENT 10'
```

`miniwm.py` is the ~50-line WM above; `clients.py` maps N named toplevels with
`_NET_WM_PID`; `measure.py` prints `list_clients()` against `xprop -root _NET_CLIENT_LIST`
(the surplus is the frames), times `list_clients` and `find_hwnd` over 50 calls, and
captures P2-6's message with `window_x11._last_no_match_log = 0` and `logger.info`
patched. Kill the three and the nested server when done — nothing touches `:0`.

---

# Fifth pass — Phase 0-2 re-verification (2026-09-02)

An independent check of everything this file marks fixed, plus a fresh look at the Phase 2
code for defects four passes did not ask about. State reviewed: ok-script-linux `693a496`
(branch `linux-port`), ok-ww `ec496b0` (`master`), same venv
(`/home/max/vsCODE/okport-venv`), same KWin/Xwayland desktop, two monitors, no game running.

**Result: every code fix this file claims is genuinely in the tree, and every count
reproduces exactly.** Nothing is marked fixed that is not. But **four findings are open
again**, and none of them is a regression from the thirteen:

* **P2-14** — a Phase 2 correctness defect the four passes missed: under a *reparenting*
  WM, `x11.is_active()` is False for the window that holds the input focus. Reproduced,
  patched, measured and reverted; the patch is below, drop-in.
* **P2-15** — `requirements-linux.txt` pins a fork commit that **exists only on this
  machine**. `origin/linux-port` is still `8cda739`; `693a496` was never pushed, so the
  Linux CI job cannot install and no published tree contains the fourth pass's fixes.
* **P2-16** — ok-ww `master` is one commit ahead of `origin/master`. The repin commit
  `ec496b0` has never run CI; the last green run is `ca80c6c`, which pinned `8cda739`.
* **P2-17** — `test.yml` and `build.yml` still carry the `submodules: true` / `lfs: true`
  that P2-9a removed from `linux.yml`, against the same unreachable submodule commit.

P2-15 and P2-16 are the same lesson P2-9a recorded, one level up: *a fix that is not
published is not a fix, and a green run on an older pair proves nothing about this one.*

## What reproduces

Every check in the fourth pass's verification table was re-executed:

| Check | Re-measured at `693a496` |
|---|---|
| `pytest tests` (fork) | **445 passed / 6 failed / 1 skipped / 10 subtests** — the six are §9b's Windows-only set (`test_device_manager` ×2, `test_process`, `test_task_ui`, `test_web_server` ×2) |
| `pytest tests/test_x11_window.py` | **69 passed** |
| same, `env -u DISPLAY QT_QPA_PLATFORM=offscreen` | **56 passed / 13 skipped** |
| `tools/scan_module_level_win32.py --check` | exit 0 |
| `tools/check_linux_imports.py` | exit 0, **70/70** resolved |
| `tools/check_linux_startup.py`, cold (`rm -f configs/devices.json`) | `first do_start only set the preferred device; re-entering as the app does` → `do_start selected BitBlt_True + PostMessageInteraction` → `PASS`, exit 0 |
| Lock pin vs fork HEAD | `requirements-linux.txt:35` = `@693a4961…` = `git rev-parse linux-port`. **Agree locally, and that is the problem — see P2-15** |
| `LINUX.md` counts | `LINUX.md:124` says 69 tests, `:227-228` say 445 and `56 passed, 13 skipped`. Correct |

And each fix was confirmed *in the code*, not from the tables:

| Finding | Where it is at `693a496` |
|---|---|
| P2-1 | `window_x11.py` `resize_window` subtracts `get_frame_extents`, settles on `client + extents == requested`, centres the outer rect with the win_gravity comment |
| P2-2 | `x11_window.py` `_pactl_env()` → `{**os.environ, 'LC_ALL': 'C', 'LANGUAGE': ''}`, passed as `env=`; `set_mute_state` skips a stream already at the target |
| P2-3 | `x11.py` `activate(wid, timeout=0.5)` polls `is_active` and returns it |
| P2-4 / P2-5 | `TestUpstreamDrift._win32_bound_methods` taint analysis + `_self_attributes` recursion; `test_the_method_gate_sees_upstream_growing_a_win32_method` simulates the drift |
| P2-6 / P2-12 | `find_hwnd`'s `rejects` list, `_NO_MATCH_LOG_INTERVAL = 30`, the `exe_names`-guarded `continue`, the title reject line, and `('; '.join(rejects) or 'no window passed the filters')` |
| P2-7 / P2-11 | `list_clients` unions three sources; source 3 calls `_frames_a_known_client`, whose predicate is `any(c.id in seen for c in child.query_tree().children)` |
| P2-9 / P2-9a / P2-9b | `.github/workflows/linux.yml` (no `submodules`, no `lfs`, reason in a comment); `tools/check_linux_startup.py` drives both `do_start` passes |
| P2-10 | `get_name` decodes `WM_NAME` as `latin-1` |
| P2-13 | `resize` calls the reply-bearing `win.get_attributes()` before `configure` |

## P2-14 — `is_active()` is False for a focused window under a reparenting WM [correctness] — **FIXED**

`ok/compat/x11.py:408` `get_focus_toplevel()`, the fallback `is_active()` uses when the WM
publishes no `_NET_ACTIVE_WINDOW`. Its docstring states the intent and then does the
opposite of it:

```python
    """``XGetInputFocus`` walked up to the toplevel, for WMs that do not set EWMH focus.

    A reparenting WM hands focus to a frame or an input-only child, so the raw id rarely
    equals the client window; walking to the child of the root is what makes it comparable.
    """
```

Under a reparenting WM the root's child **is the frame**, not the client — the same fact
P2-11 was fixed for, one function away. So the walk climbs *past* the client and returns
the frame, and `is_active(client)` compares two different windows.

**Reproduced** on a nested `Xwayland :9` (no root, no package — the P2-11 harness), with a
client carrying `WM_STATE` reparented into an override-redirect frame and
`XSetInputFocus` pointed at the client:

```
raw XGetInputFocus       : 0x200001
client                   : 0x200001
frame  (child of root)   : 0x200000
x11.get_active_window()  : 0x0          # no WM, so the EWMH short-circuit does not fire
x11.get_focus_toplevel() : 0x200000     # the FRAME
x11.is_active(client)    : False        # the client literally holds the input focus
x11.is_active(frame)     : True
```

and through the two callers that matter:

```
x11.activate(focused client)             -> False in 0.51s   (focus was already granted)
window_x11.is_foreground_window(client)  -> False
```

**Reachability and impact.** The EWMH path (`get_active_window()`) short-circuits on KWin,
Mutter and every WM that publishes `_NET_ACTIVE_WINDOW`, so this is invisible on the
machine every measurement in this file was taken on. It bites on a reparenting WM that
does *not* publish it (twm, mwm, ctwm, and any WM during a restart), where every
`_NET_ACTIVE_WINDOW`-less poll takes the fallback. Then, all of these invert:

* `X11Window.visible` (`x11_window.py:399` `visible = self.is_foreground()`) is False for
  the whole of foreground play. `src/task/MouseResetTask.py:39` gates on
  `not self.hwnd.visible`, so it pins the physical cursor **while the user is playing**.
  That is exactly the [V15] inversion `PORT.md` warns about, arriving through the other door.
* `clickable()` on `PynputInteraction` (`pynput.py:41`), `PyDirectInteraction`
  (`pydirect.py:30`) and `ForegroundPostMessageInteraction`
  (`foreground_post_message.py:20`) is False forever — Phase 4's foreground fallback
  (§4/4d) never becomes usable.
* `bring_to_front()` reports a refusal for focus that *was* granted, after paying
  `activate`'s full 0.5s timeout per candidate. P2-3 made that return value honest; this
  makes it lie again in the one case P2-3 could not measure.
* `bitblt.py:116` and `base.py:84` (`clickable`) read the same flag.
* With `Mute Game while in Background` on (default False, `GlobalConfig.py:53`), the game
  is muted for the whole session while it is in the foreground.

### The patch — applied, measured and reverted before being written down

**File:** `/home/max/vsCODE/ok-script-linux/ok/compat/x11.py`. Replace the whole of
`get_focus_toplevel` (**lines 408-434** at `693a496`, from `def get_focus_toplevel():` down
to and including `return _call(run, 0, 'focus_toplevel') or 0`) with the two functions
below. `_prop` (`x11.py:148`) and `_window` (`x11.py:144`) are already defined above this
point; nothing else in the module changes, and `is_active` is left exactly as it is.

```python
def _client_window(d, wid, root_id):
    """The *client* window at or above ``wid``, or the root's child, or 0. Never raises.

    ICCCM's answer to "which client does this window belong to" is ``WM_STATE``: the WM
    sets it on the client window and on nothing else, which is what ``XmuClientWindow``
    looks for. Focus almost never lands on the client itself -- a toolkit gives it to an
    input child, and a *reparenting* WM puts the client inside a frame -- so the search
    walks up from ``wid`` and returns the first window carrying it.

    Walking all the way to the root's child instead returned the **frame** under a
    reparenting WM, so ``is_active()`` was False for a window that held the input focus
    [P2-14]. One level of descent covers the other half of that shape, a WM that focuses
    the frame rather than the client.

    The root-child fallback is the right answer when nothing in the branch carries
    ``WM_STATE`` at all: a bare X server with no window manager, which is also CI.
    """
    root_child = 0
    for _ in range(16):
        if not wid or wid == root_id:
            break
        try:
            if _prop(d, wid, 'WM_STATE') is not None:
                return int(wid)
            tree = _window(d, wid).query_tree()
        except Exception:
            return 0
        if tree.parent is None or tree.parent == 0:
            break
        parent_id = tree.parent if isinstance(tree.parent, int) else tree.parent.id
        if parent_id == root_id:
            root_child = int(wid)
            break
        wid = parent_id
    if root_child:
        try:
            for child in _window(d, root_child).query_tree().children:
                if _prop(d, child.id, 'WM_STATE') is not None:
                    return int(child.id)
        except Exception:
            pass
    return root_child


def get_focus_toplevel():
    """``XGetInputFocus`` resolved to the client window, for WMs that set no EWMH focus."""

    def run(d):
        import Xlib.X
        focus = d.get_input_focus().focus
        if focus in (Xlib.X.PointerRoot, Xlib.X.NONE, 0) or isinstance(focus, int):
            return 0
        return _client_window(d, focus.id, d.screen().root.id)

    return _call(run, 0, 'focus_toplevel') or 0
```

Three things about it that are deliberate, so nobody "simplifies" them back out:

1. **`WM_STATE` first, root-child second — not either alone.** `WM_STATE`-only would
   return 0 on a bare X server with no WM (CI under Xvfb, and this file's own live tests),
   where nothing carries the property; root-child-only is the bug.
2. **The one level of descent is not decoration.** It covers a WM that focuses the *frame*
   rather than the client, which is a real ICCCM-legal shape and the second half of the
   reproduction below. It runs only when the whole up-walk found no `WM_STATE`, so on the
   EWMH path it never runs at all.
3. **It takes `d` and is module-level**, rather than staying nested inside `run`, purely so
   the tests below can drive it against a fake display — the same reason
   `_frames_a_known_client` is shaped that way.

### Tests to add

`tests/test_x11_window.py`. Two edits:

* add `import types` to the import block (**after `import time`, line 25** at `693a496`);
* insert the class below immediately **before `@skip_on_windows` / `class TestFrameSkip`
  (lines 325-326)**, i.e. after `TestFindHwnd`, keeping the two blank lines the file uses
  between top-level classes. The class needs the `@skip_on_windows` decorator of its own.

```python
@skip_on_windows
class TestFocusClientWindow(unittest.TestCase):
    """[P2-14] `is_active` must see the client, not the reparenting WM's frame.

    Measured on a nested `Xwayland :9` with the client reparented into an
    override-redirect frame and the input focus set on the client: `get_focus_toplevel`
    returned the frame, so `is_active(client)` was False while `XGetInputFocus` named the
    client, `is_foreground_window` was False for a focused game, and `x11.activate` spent
    its whole 0.5s timeout to report a refusal of focus it had been granted. Unit-tested
    rather than driven live because the fallback only runs on a WM that publishes no
    `_NET_ACTIVE_WINDOW`, and this desktop (KWin) and CI (Xvfb, no WM) are neither.
    """

    class _Window:
        def __init__(self, wid, parent=None, wm_state=False, children=(), raises=False):
            self.id = wid
            self.parent = parent
            self.wm_state = wm_state
            self.children = list(children)
            self.raises = raises

    class _Display:
        """The three calls `_client_window` makes: get_atom, create_resource_object, query_tree."""

        def __init__(self, windows):
            self.windows = {w.id: w for w in windows}

        def get_atom(self, name):
            return 39 if name == 'WM_STATE' else 1

        def create_resource_object(self, kind, wid):
            # The root and anything outside the fixture behave as a bare window.
            window = self.windows.get(wid) or TestFocusClientWindow._Window(wid)
            display = self

            class _Resource:
                id = wid

                def get_full_property(self, atom, kind_):
                    if window.raises:
                        raise RuntimeError('BadWindow: it went away mid-walk')
                    # SimpleNamespace, not Mock: `parent` is a reserved Mock kwarg and a
                    # `Mock(parent=...)` silently hands back the wrong object below.
                    return types.SimpleNamespace(value=[1, 0]) if window.wm_state else None

                def query_tree(self):
                    if window.raises:
                        raise RuntimeError('BadWindow: it went away mid-walk')
                    return types.SimpleNamespace(
                        parent=None if window.parent is None else display.create_resource_object('window', window.parent),
                        children=[display.create_resource_object('window', c) for c in window.children])

            return _Resource()

    ROOT = 0x100

    def test_focus_on_an_input_child_resolves_to_the_client(self):
        from ok.compat import x11
        display = self._Display([
            self._Window(0x1400002, parent=0x1400001),
            self._Window(0x1400001, parent=self.ROOT, wm_state=True, children=[0x1400002]),
        ])

        self.assertEqual(0x1400001, x11._client_window(display, 0x1400002, self.ROOT))

    def test_a_reparented_client_is_not_reported_as_its_frame(self):
        """The regression: the frame is the root's child, so the old walk returned it."""
        from ok.compat import x11
        display = self._Display([
            self._Window(0x1400001, parent=0x2000001, wm_state=True),
            self._Window(0x2000001, parent=self.ROOT, children=[0x1400001]),
        ])

        self.assertEqual(0x1400001, x11._client_window(display, 0x1400001, self.ROOT))

    def test_a_wm_that_focuses_the_frame_still_resolves_to_the_client(self):
        """One level of descent: the frame carries no WM_STATE, its child does."""
        from ok.compat import x11
        display = self._Display([
            self._Window(0x2000001, parent=self.ROOT, children=[0x1400001]),
            self._Window(0x1400001, parent=0x2000001, wm_state=True),
        ])

        self.assertEqual(0x1400001, x11._client_window(display, 0x2000001, self.ROOT))

    def test_with_no_wm_state_anywhere_the_root_child_is_the_answer(self):
        """A bare X server with no window manager, which is also what CI runs under."""
        from ok.compat import x11
        display = self._Display([
            self._Window(0x1400002, parent=0x1400001),
            self._Window(0x1400001, parent=self.ROOT, children=[0x1400002]),
        ])

        self.assertEqual(0x1400001, x11._client_window(display, 0x1400002, self.ROOT))

    def test_a_window_that_dies_mid_walk_is_zero_not_an_exception(self):
        from ok.compat import x11
        display = self._Display([self._Window(0x1400001, parent=self.ROOT, raises=True)])

        self.assertEqual(0, x11._client_window(display, 0x1400001, self.ROOT))
```

**The `types.SimpleNamespace` comment is load-bearing, not style.** The first draft of this
fixture used `unittest.mock.Mock(parent=…)`; `parent` is a reserved `Mock` constructor
keyword, so `tree.parent` came back as mock plumbing and three of the five tests failed
with `AttributeError: '_Resource' object has no attribute '_mock_new_name'` surfacing as
`20971521 != 0`. Do not swap it back.

### Expected results, all observed

The patch and the tests above were applied to a working copy of `693a496`, run, and then
reverted — the fork tree is clean at `693a496`.

```sh
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
$V/bin/python -m pytest tests/test_x11_window.py            # 69 today -> 74 passed
env -u DISPLAY QT_QPA_PLATFORM=offscreen $V/bin/python -m pytest tests/test_x11_window.py
                                                            # 56/13 today -> 61 passed, 13 skipped
$V/bin/python -m pytest tests                               # 445 -> 450 passed, 6 failed, 1 skipped
```

The six failures stay §9b's Windows-only set. The live X11 tests, including P2-7's
override-redirect test and the two `resize_window` ones, are unaffected.

**The negative control is the nested server, not the unit tests** (they cannot run at all
without `_client_window`). Same harness, same shape, before and after the patch:

```
before: x11.get_focus_toplevel() -> 0x200000 (frame)   is_active(client) False   activate() False in 0.51s
after : x11.get_focus_toplevel() -> 0x200001 (client)  is_active(client) True    activate() True  in 0.00s
```

### Reproducing it

```sh
Xwayland :9 -geometry 1000x700 &        # nested, rootful, inside the Wayland session
V=/home/max/vsCODE/okport-venv
DISPLAY=:9 $V/bin/python - <<'EOF'
import sys, time
from Xlib import X, display
sys.path.insert(0, '/home/max/vsCODE/ok-script-linux')
from ok.compat import x11

d = display.Display(); root = d.screen().root
def mk(parent, override=0):
    return parent.create_window(0, 0, 300, 200, 0, X.CopyFromParent, X.InputOutput,
                                X.CopyFromParent, background_pixel=d.screen().white_pixel,
                                override_redirect=override)
wm_state = d.get_atom('WM_STATE')
frame = mk(root, 1); client = mk(root)
client.change_property(wm_state, wm_state, 32, [1, 0])   # what a WM puts on the client
client.reparent(frame, 0, 0); frame.map(); client.map(); d.sync(); time.sleep(0.3)
d.set_input_focus(client, X.RevertToParent, X.CurrentTime); d.sync(); time.sleep(0.3)

print('client', hex(client.id), 'frame', hex(frame.id))
print('get_focus_toplevel', hex(x11.get_focus_toplevel()))
print('is_active(client) ', x11.is_active(client.id))
t = time.time(); ok = x11.activate(client.id)
print(f'activate(client)   {ok} in {time.time()-t:.2f}s')
# and the frame-focused half, which the descent covers
d.set_input_focus(frame, X.RevertToParent, X.CurrentTime); d.sync(); time.sleep(0.3)
print('frame focused -> get_focus_toplevel', hex(x11.get_focus_toplevel()))
EOF
pkill -f 'Xwayland :9'
```

Nothing here touches `:0`. `Xwayland` is already installed (the session runs it); Xephyr,
Xvfb and every standalone WM still are not, and are still not needed.

## P2-15 — the Linux lock pins a fork commit that exists on no remote [automation, fix first] — **FIXED**

`requirements-linux.txt:35` pins
`git+https://github.com/RarestStatue/ok-script-linux@693a496177b4f1bb298391cb14792e0dedebb53e`.
That commit is local-only:

```
$ git -C ../ok-script-linux ls-remote origin
8cda73980fec17957e3750290f9de58bddaf9388	HEAD
8cda73980fec17957e3750290f9de58bddaf9388	refs/heads/linux-port
```

`origin/linux-port` is still the *third* pass's commit. `693a496`, `4ca767e` and `c23646d`
— the entire fourth pass, P2-11 and P2-12 — are on this machine only, as is the branch
`linux-port-p2-11-12` they were merged from. Verified end to end, which is also the exact
error the Install step will print:

```
$ git fetch --depth 1 origin 693a496177b4f1bb298391cb14792e0dedebb53e
fatal: remote error: upload-pack: not our ref 693a496177b4f1bb298391cb14792e0dedebb53e
```

So the moment `ec496b0` is pushed (P2-16), the Linux startup gate fails at `Install`. And
the fourth pass's own closing paragraph — *"a lock left on the old commit means CI keeps
testing the old tree"* — is half of the lesson: a lock moved to a commit nobody can fetch
does not test anything at all.

**Fix, in this order:**

1. `git -C /home/max/vsCODE/ok-script-linux push origin linux-port` — `693a496` is already
   a merge on `linux-port`, so this is a fast-forward of the remote branch; nothing needs
   rebasing. Push the topic branch too if it is worth keeping:
   `git push origin linux-port-p2-11-12`.
2. Confirm the pin is now fetchable *anonymously*, the way CI does it — pip's clone carries
   no credentials, which is what cost run `33587086281` in P2-9a:
   ```sh
   GIT_CONFIG_GLOBAL=/dev/null git -c credential.helper= ls-remote \
       https://github.com/RarestStatue/ok-script-linux.git | grep 693a4961
   ```
3. Only then push ok-ww (P2-16) and read the run.

**Do not "fix" this by repinning the lock back to `8cda739`.** That drops P2-11 and P2-12
out of the tested tree.

## P2-16 — ok-ww `master` is one commit ahead of its remote, so no CI run covers this pair [automation] — **FIXED**

```
$ git status -sb
## master...origin/master [ahead 1]
$ git log --oneline -1 origin/master
ca80c6c docs(port): record the green Linux gate run
$ gh run view 33587618601 --json headSha,conclusion
{"conclusion":"success","headSha":"ca80c6c2af5a6c2a86d2cc1dd1688c3549750f9f"}
```

`ec496b0` — the commit that repins the lock to `693a496` and records the fourth pass — is
unpushed. Both green runs in `gh run list` are `ca80c6c` and its predecessor, i.e. the
`8cda739` pair. Everything the fourth pass concluded about CI is therefore a statement
about the *third* pass's trees.

**Fix:** after P2-15's push and check, `git push origin master`, then **read the run**, not
the YAML — P2-9a's rule. A green run on `ec496b0` is the first CI evidence for `693a496`.
If the Install step fails on the pin, P2-15 was not done.

## P2-17 — `test.yml` and `build.yml` keep the submodule checkout P2-9a had to remove [automation, inherited] — **OPEN, and option (a) is disproven**

P2-9a diagnosed `actions/checkout` failing with
`upload-pack: not our ref 515962ce…` because `ok_templates` is pinned to a commit that is
on no ref of the labeling repo, and dropped `submodules`/`lfs` from `linux.yml`. The same
two lines are still in every other workflow: `test.yml:35-36` and `build.yml:43-44`,
`:127-128`, `:195-196`. The submodule commit is still unreachable — re-checked today:

```
$ git ls-remote https://github.com/ok-oldking/ok-wuthering-waves-coco-labeling.git | grep -c 515962ce
0
```

Invisible so far only because no Windows workflow has ever been triggered on this fork.
The first push that touches `test.yml`'s paths burns a job at checkout.

**Fix — pick one, and record which:**

* **(a) Match `linux.yml`.** Drop `submodules: true` / `lfs: true` from `test.yml` and from
  all three `build.yml` jobs, with the same comment naming the unreachable commit. Cheap
  and consistent, but `build.yml` packages the app: check whether the build steps read
  `ok_templates/` before dropping it there — the startup gate does not, but a *build* may.
* **(b) Repin the submodule** to a commit that exists (`d1b4ed8c…` is the labeling repo's
  current `master`) with `git -C ok_templates fetch && git submodule set-branch`… and
  commit the new gitlink. This changes what the app ships, so it is not a CI-only decision
  — it belongs to whoever owns the templates, and `ok_templates` is a *submodule of an
  upstream project*, not this port's to bump on a whim.

(a) for `test.yml` now, and (b) escalated rather than guessed, is the honest split. Either
way this is not Phase 2's bug — it is inherited, and it is recorded here because the next
person to push will hit it and waste an hour on the wrong hypothesis.

> **Sixth pass: (a) is wrong, for `test.yml` as much as for `build.yml`, and the "check
> whether the build steps read `ok_templates/`" caveat above is the thing that catches it.**
> Both `test.yml` (`:83`) and `build.yml`'s first job (`:95`) run every file in `tests\`:
>
> ```powershell
> Get-ChildItem -Path ".\tests\*.py" | ForEach-Object { python -m unittest $_.FullName ... }
> ```
>
> and seven of those files load images out of the submodule — `tests/TestChar.py:2069`,
> `TestCombatCheck.py:33,47`, `TestFeatureSet.py:13`, `TestForte.py:45`, `TestKey.py:48`,
> `TestSkipDialogWideMode.py:17,18,31`, `TestWorld.py:23`. Dropping `submodules: true`
> therefore does not make those jobs pass; it moves the failure from `actions/checkout` to
> `cv2.imread` returning `None`. That is not the trade `linux.yml` made — the startup gate
> genuinely does not read `ok_templates/`, which is why (a) was right *there* and is wrong
> here.
>
> So the only fix for these two workflows is (b), and (b) is a decision about what the app
> ships, taken against a submodule this port does not own. Re-checked today: the gitlink is
> still `515962ce`, the labeling repo's `master` is `d1b4ed8c1ca9e145c514853c14030a7358afe12c`,
> and `git ls-remote | grep -c 515962ce` is still `0`. **Nothing was changed.** P2-17 stays
> open, now with the wrong answer ruled out rather than merely untried, and it belongs to
> whoever owns `ok_templates`.

## Suggested order (fifth pass)

1. **P2-15** — one `git push`. Until it happens, every other claim about CI is unfalsifiable
   and the fourth pass's fixes exist on exactly one disk.
2. **P2-16** — push ok-ww, read the run. Together with 1, this is the first CI evidence for
   the `ec496b0` ⇄ `693a496` pair.
3. **P2-14** — the only correctness finding. Drop-in patch and tests above; ship them in one
   commit on `linux-port`, then repin `requirements-linux.txt:35` to the new fork commit and
   push both (that is 1 and 2 again — do them in that order and it is one cycle, not two).
4. **P2-17** — cheap for `test.yml`, escalate for `build.yml`.

None of the four blocks Phase 3.

## Phase 3 readiness

Nothing in Phase 2 is left open that Phase 3 depends on, and the two Phase 2 items that
were always going to outlive it are unchanged and still correctly recorded:

* **[GATE-1b]** — the pressure-vessel PID-namespace question. `find_hwnd`'s whole identity
  chain is `_NET_WM_PID` → `psutil.Process(pid)` → command line, and P2-6/P2-12's rejection
  message now says precisely which link broke. Still untested against a Steam-launched game.
* **P2-7 against the real game** — `list_clients` enumerates override-redirect toplevels and
  has a live test that builds one by hand, but no one has pointed it at a
  fullscreen-exclusive Proton window. Same session as [GATE-1b] / [GATE-2].

Phase 3 (`X11CaptureMethod`) needs neither. Two things it *will* touch that this pass
confirms are ready: `tools/check_linux_startup.py` asserts only that *a* capture method is
selected, so it starts naming `X11` without a change (its own docstring says so); and
`x11.is_minimized()` is the predicate `do_get_frame` should raise `CaptureException` on
per `PORT.md` §4 Phase 3 / [V7] — it is already the three-way check (`_NET_WM_STATE_HIDDEN`,
`WM_STATE == IconicState`, not viewable) and is live-tested.

---

# Sixth pass — the fifth pass's four, closed (2026-09-02)

The fifth pass's suggested order, run. Three of the four are closed; the fourth is closed
as a question rather than a change, because measuring it disproved the answer that was
recommended. State at the end: ok-script-linux `12e297c` (branch `linux-port`, **pushed**),
ok-ww `master` with the lock repinned to it, same venv, same KWin/Xwayland desktop.

| | What was done |
|---|---|
| **P2-14** | The patch and the five tests below applied verbatim. ok-script-linux `f41745b` |
| **P2-15** | `git push origin linux-port` (`8cda739..f41745b`, fast-forward) and `linux-port-p2-11-12`; pin re-verified anonymously |
| **P2-16** | `requirements-linux.txt:35` repinned to `12e297c` and ok-ww `master` pushed |
| **P2-17** | Measured, **not changed** — option (a) is disproven. See the block in P2-17 above |

## P2-14 — applied exactly as the fifth pass specified

`ok/compat/x11.py`: `get_focus_toplevel`'s body became the two functions written above,
`_client_window` and a three-line `get_focus_toplevel`. `is_active` was not touched.
`tests/test_x11_window.py`: `import types` after `import time`, and `TestFocusClientWindow`
inserted between `TestFindHwnd` and `TestFrameSkip`.

Every number the fifth pass predicted came out:

| Check | Predicted | Measured |
|---|---|---|
| `pytest tests/test_x11_window.py` | 69 -> 74 | **74 passed** |
| same, no `DISPLAY` | 56/13 -> 61/13 | **61 passed, 13 skipped** |
| `pytest tests` (fork) | 445 -> 450 | **450 passed, 6 failed, 1 skipped, 10 subtests** — the six are §9b's Windows-only set, unchanged |
| `tools/scan_module_level_win32.py --check` | exit 0 | exit 0 |
| `tools/check_linux_imports.py` | exit 0 | exit 0, **70/70** resolved |
| `tools/check_linux_startup.py`, cold | PASS | `first do_start only set the preferred device` -> `do_start selected BitBlt_True + PostMessageInteraction` -> `PASS`, exit 0 |

**The live control, which is the part the unit tests cannot give.** Same nested
`Xwayland :9` harness as the fifth pass's reproduction — a client carrying `WM_STATE`
reparented into an override-redirect frame, `XSetInputFocus` on the client:

```
client 0x200001 frame 0x200000
get_focus_toplevel 0x200001            # was 0x200000, the frame
is_active(client)  True                # was False
activate(client)   True in 0.00s       # was False in 0.51s
frame focused -> get_focus_toplevel 0x200001   # the descent, exercised
```

The last line is the half the fifth pass added the one level of descent for: with focus on
the *frame*, the walk finds no `WM_STATE` on the way up, falls back to the root's child,
and descends one level into the client. Both halves of the shape now answer with the
client.

`LINUX.md` moved with the counts: `:124` says 74 tests and names the `WM_STATE` resolution,
`:227-228` say 450 and `61 passed, 13 skipped` (ok-script-linux `12e297c`).

## P2-15 / P2-16 — published, in that order

```
$ git -C ../ok-script-linux push origin linux-port
   8cda739..f41745b  linux-port -> linux-port
$ GIT_CONFIG_GLOBAL=/dev/null git -c credential.helper= ls-remote \
      https://github.com/RarestStatue/ok-script-linux.git
12e297ce46bdda5657955555073975ccd04c7bd3	HEAD
12e297ce46bdda5657955555073975ccd04c7bd3	refs/heads/linux-port
4ca767e486a6e45ed1c5cc9676fd68c51174ca57	refs/heads/linux-port-p2-11-12
```

The anonymous `ls-remote` is the check that matters, not the push: pip's clone carries no
credentials, and a pin that resolves only with the developer's own git config is the
failure P2-9a burned run `33587086281` on. `linux-port-p2-11-12` was pushed too, so the
fourth pass's topic branch is no longer single-disk either.

`requirements-linux.txt:35` now pins `12e297c` — the `LINUX.md` commit, not `f41745b`, so
the tested tree and the documented counts are the same tree. The fifth pass's warning
still stands in the other direction: **do not repin backwards.** `8cda739` drops P2-11,
P2-12 and P2-14; `693a496` is fetchable now but predates P2-14.


**The run.** `Linux startup gate` **33669383034**, `6fac179`, conclusion `success` — the
first CI evidence for the `6fac179` ⇄ `12e297c` pair, and the first time the Install step
has resolved this fork pin from a credential-less clone:

```
Install            Building wheel for ok-script (pyproject.toml): finished with status 'done'
Install            Successfully installed ... ok-script-2.0.5+linux.1 ... python-xlib-0.33 ...
Phase 2 exit gate  OK    first do_start only set the preferred device; re-entering as the app does
Phase 2 exit gate  OK    do_start selected BitBlt_True + PostMessageInteraction
Phase 2 exit gate  PASS  startup reaches capture-method selection
```

Read from the run, not the YAML — P2-9a's rule. Both `do_start` passes are in the log,
which is the thing P2-9b added and the thing a green tick alone would not prove.

## State after this pass

| | |
|---|---|
| ok-script-linux | `12e297c` on `linux-port`, **pushed**; working tree clean |
| ok-ww | `6fac179` on `master`, **pushed**; CI green |
| Lock | `requirements-linux.txt:35` → `12e297c`, fetchable anonymously |
| Open | **P2-17 only**, inherited, and not this port's to close |
| Phase 3 | Unblocked. Nothing in the fifth or sixth pass touches what §4 Phase 3 depends on |

---

# Seventh pass — Phase 0-3 review (2026-09-02)

The first review of **Phase 3**, plus a re-verification of Phases 0-2 against the tree
Phase 3 landed on. State reviewed: ok-script-linux `493354a` (branch `linux-port`, pushed),
ok-ww `ed8813a` (`master`, pushed), venv `/home/max/vsCODE/okport-venv` (python 3.12.14),
a real KWin/Xwayland desktop (`DISPLAY=:0`, two monitors), **the game not running**.

Everything below was executed, not read. Nothing in Phases 0-2 regressed. Seven findings
are new and all seven are in Phase 3; **P2-17 is still open and still inherited**.

| | Severity | One line |
|---|---|---|
| **P3-1** | correctness, fix first | a depth-30 (10-bit) visual is decoded as 8-bit — a silently wrong picture, no error |
| **P3-2** | correctness | minimizing the game **disables** the running task instead of pausing it |
| **P3-3** | correctness of the guard | `x11_capture_available()` is True for a `DISPLAY` nothing answers, so the backend is selected and every grab logs an ERROR |
| **P3-4** | contract | `get_name()` says `X11_Composite` for grabs that silently fell back to the direct path, and lags a method switch by one frame |
| **P3-5** | observation, NOT verified against the game | the letterbox crop takes all vertical slack off the top, because upstream's formula is written for *window* coordinates |
| **P3-6** | documentation | the runtime shared libraries (`libX11`, `libXext`, `libXcomposite`) are a hard requirement nothing records; missing `libXext` means no capture backend at all |
| **P3-7** | documentation | `.github/workflows/linux.yml`'s step is still called `Phase 2 exit gate` after growing the Phase 3 assertions |

## What checks out

Every load-bearing claim in `PORT.md` §11 and in `LINUX.md`'s Phase 3 section reproduces.

| Claim | Result |
|---|---|
| Fork suite | **484 passed / 6 failed / 1 skipped / 10 subtests** — `LINUX.md:253`'s number exactly, and the 6 are §9b's Windows-only set, no new ones |
| `tests/test_x11_window.py` + `tests/test_x11_capture.py` | **108 passed** (74 + 34); with `DISPLAY` unset **85 passed, 23 skipped** — `LINUX.md:274-275`'s 61/13 and 24/10 |
| `tools/scan_module_level_win32.py --check` | exit 0, `TOTAL 27`, same 4 calling a loader at import |
| `tools/check_linux_imports.py` | exit 0, **70/70** resolved |
| `tools/check_linux_startup.py` | `PASS`; `do_start selected X11 + PostMessageInteraction`, `capture backend is X11CaptureMethod`, and the frame step reports itself skipped with no game — which is the documented shape |
| CI, both repos, on this pair | fork `Linux port gates` **33672722286** on `493354a` `success`; ok-ww `Linux startup gate` **33672918236** on `ed8813a` `success`, and its log carries `OK    do_start selected X11 + PostMessageInteraction` — so the X11 branch is proven under `xvfb-run`, not only here |
| Lock ⇄ fork pin | `requirements-linux.txt:35` pins `493354a`, which is `origin/linux-port`'s head. Both repos clean and pushed; P2-15/P2-16's failure mode has not come back |
| §11's throughput | reproduced on a 1920x1080 test window: `X11` (SHM) **1.06 ms**, `X11` (`XGetImage`) **9.45 ms**, `X11_Composite` **1.01 ms**. §11 measured 2.28 / 11.01 / 2.16 at that size; this machine is quicker today and the 6-9x ratio holds |
| The copy contract [V14] | a frame from the SHM path is byte-identical after the next grab into the same segment |
| Colour | a window painted `0x336699` grabs as BGR `[153, 102, 51]` — no double swap, on both the direct and the composite path |
| Segment hygiene | `ipcs -m` shows 2 segments while three grabbers are live and **0** after `close()`; the `IPC_RMID`-straight-after-`XShmAttach` claim holds |
| E3's re-naming | the composite path re-names the pixmap per grab and costs the same as the direct path (1.01 vs 1.06 ms) |
| `X11CaptureMethod.connected()`'s extra round trip | `x11.exists` is **0.074 ms**, and **0.052 ms** with a thread hammering `list_clients` on the shared python-xlib connection concurrently. `TaskExecutor.can_capture` calls it before every `get_frame`, and against a 1.0 ms grab that is not a cost worth removing |
| `winreg` on Linux (Phase 1, re-checked) | ok-ww's game-install detection is safe: the stub's `winreg` raises `FileNotFoundError`, an `OSError`, which `config.py`'s `_find_pc_exe_from_registry` and `_find_most_recently_run_pc_exe` already catch. The constants are real ints, so `KEY_READ \| KEY_WOW64_64KEY` does not `TypeError` |
| `capture_rect` ⇄ `get_capture_origin` | agree, and E5's choice of `client_*` over `real_*` is right for Linux — but the shared formula has its own problem, see **P3-5** |
| Reuse-after-`close()` | not reachable in production: every `capture_method.close()` (`DeviceManager.py:142,679,698,706`, `update.py:73,92`) drops the reference. The grabber does survive it anyway — verified: `close()` then `grab()` reopens the display and re-redirects |
| The drift gate covers Phase 3 | `tests/test_x11_window.py:1075-1078` walks `ok/compat/xshm.py` and `ok/device/capture_methods/x11_capture.py` for Win32 references |

One trap worth repeating because it cost this pass ten minutes and `LINUX.md:249` already
warns about it: **`pytest tests -q` from the fork root is `-qq`** (`pytest.ini`'s `addopts`
already carries `-q`) and suppresses the `N failed, M passed` line entirely, leaving a
`FAILED` row as the last output. Use `-o addopts="-ra"`.

---

## P3-1 — a depth-30 (10-bit) visual is decoded as 8-bit, silently [correctness, fix first] — **FIXED**

`ok/compat/xshm.py:296-316` derives each channel's *byte* index from the low set bit of its
mask and never checks how **wide** the mask is. A depth-30 TrueColor visual — 10 bits per
channel, `bits_per_pixel` still 32, masks `R=0x3FF00000 G=0x000FFC00 B=0x000003FF` — has
low bits at 20, 10 and 0, so `index()` returns bytes 2, 1, 0, which is exactly the
`(0, 1, 2)` fast path at `:339`. `cv2.cvtColor(..., COLOR_BGRA2BGR)` then takes the low
byte of each 10-bit field as if it were the channel.

No exception and no log line: a wrong *picture*, which is the one failure mode the module's
own docstring (`xshm.py:299-303`) says the general form exists to prevent.

Measured, with a hand-made `XImage` carrying those masks (`bits_per_pixel=32`, `depth=30`,
LSBFirst):

| 10-bit pixel | decoded BGR | should be |
|---|---|---|
| pure red `(1023, 0, 0)` | `[0, 0, 240]` | `[0, 0, 255]` |
| pure green `(0, 1023, 0)` | `[0, 252, 15]` | `[0, 255, 0]` |
| pure blue `(0, 0, 1023)` | `[255, 3, 0]` | `[255, 0, 0]` |
| mid grey `(512, 512, 512)` | `[0, 2, 8]` | `[128, 128, 128]` |
| white `(1023, 1023, 1023)` | `[255, 255, 255]` | `[255, 255, 255]` |

Mid grey arriving as near-black is what makes this worth code rather than a note: the
picture is not merely tinted, it is non-monotonic in luminance, so every template match and
every OCR call degrades and the app has nothing to report.

**Reachability, stated honestly.** This machine's root is depth 24 (`xdpyinfo`:
`depth of root window: 24 planes`, and no depth-30 visual is advertised), so this is
**latent here, not live**. It becomes live on an X server with `DefaultDepth 30` (NVIDIA's
30-bit mode) or when a client picks a 30-bit visual on a depth-24 root. The fix is small
and removes a whole class, so it is worth doing rather than documenting.

### The patch

`ok/compat/xshm.py`. Replace `_channel_indices` (`:296-316`) with a field-based helper plus
a wide unpacker, and route `image_to_bgr` (`:319-349`) through them.

```python
def _channel_fields(image, masks=None):
    """``((shift, width), ...)`` for B, G, R, or ``None`` for a mask that is absent.

    ``width`` is the part ``_channel_indices`` used to ignore. A depth-30 TrueColor visual
    is 10 bits per channel with ``bits_per_pixel`` still 32, and its low set bits land on
    bytes 0, 1, 2 -- i.e. straight onto the BGRA fast path, where the low byte of each
    10-bit field is read as the channel. Mid grey came back as ``[0, 2, 8]``.
    """
    red, green, blue = image.red_mask, image.green_mask, image.blue_mask
    if not (red or green or blue) and masks:
        red, green, blue = masks

    def field(mask):
        mask = int(mask)
        if not mask:
            return None
        shift = (mask & -mask).bit_length() - 1
        return shift, (mask >> shift).bit_length()

    return field(blue), field(green), field(red)


def _channel_indices(image, masks=None):
    """Byte offsets of B, G, R inside each 32-bit pixel, for 8-bit-per-channel visuals.

    ``None`` for a channel whose mask is absent *or* is not 8 bits wide; the caller falls
    back to :func:`_unpack_wide` for the second case.
    """
    def index(field):
        if field is None or field[1] != 8:
            return None
        byte = field[0] // 8
        return byte if image.byte_order == LSB_FIRST else 3 - byte

    return tuple(index(f) for f in _channel_fields(image, masks))


def _unpack_wide(array, fields, byte_order):
    """Channels wider than 8 bits (a depth-30 visual), scaled down to 8. BGR order out."""
    words = array.astype(np.uint32)
    if byte_order == LSB_FIRST:
        words = (words[:, :, 0] | (words[:, :, 1] << 8)
                 | (words[:, :, 2] << 16) | (words[:, :, 3] << 24))
    else:
        words = (words[:, :, 3] | (words[:, :, 2] << 8)
                 | (words[:, :, 1] << 16) | (words[:, :, 0] << 24))
    out = np.empty(array.shape[:2] + (3,), dtype=np.uint8)
    for channel, (shift, width) in enumerate(fields):        # fields is (blue, green, red)
        value = (words >> shift) & ((1 << width) - 1)
        value = value >> (width - 8) if width >= 8 else value << (8 - width)
        out[:, :, channel] = value.astype(np.uint8)
    return out
```

and in `image_to_bgr`, replace the block that currently reads

```python
    blue, green, red = _channel_indices(frame, masks)
    if (blue, green, red) == (0, 1, 2):
        # The measured path: one 0.15 ms pass that drops the alpha byte and copies.
        bgr = cv2.cvtColor(array, cv2.COLOR_BGRA2BGR)
    else:
        if None in (blue, green, red):
            raise ValueError(f'X11 image has no RGB masks: {frame.red_mask:#x} '
                             f'{frame.green_mask:#x} {frame.blue_mask:#x}')
        bgr = np.ascontiguousarray(array[:, :, [blue, green, red]])
```

with

```python
    fields = _channel_fields(frame, masks)
    if None in fields:
        raise ValueError(f'X11 image has no RGB masks: {frame.red_mask:#x} '
                         f'{frame.green_mask:#x} {frame.blue_mask:#x}')
    blue, green, red = _channel_indices(frame, masks)
    if (blue, green, red) == (0, 1, 2):
        # The measured path: one 0.15 ms pass that drops the alpha byte and copies.
        bgr = cv2.cvtColor(array, cv2.COLOR_BGRA2BGR)
    elif None in (blue, green, red):
        # A channel that is not 8 bits wide -- a depth-30 (10-bit) visual. Byte indices
        # cannot express it, and taking the fast path anyway is a silently wrong picture.
        bgr = _unpack_wide(array, fields, frame.byte_order)
    else:
        bgr = np.ascontiguousarray(array[:, :, [blue, green, red]])
```

The `pixels_per_row != width` slice at `:347-348` stays where it is and still applies.

The unpacker was prototyped against the masks above before being written down; it returns
`[0,0,255]`, `[0,255,0]`, `[255,0,0]`, `[128,128,128]`, `[255,255,255]`, `[0,0,0]` for the
six probes, and `[0,0,255]` for the MSBFirst red control.

### Tests to add

In `tests/test_x11_capture.py`, `TestImageToBgr`. `make_image` needs a `depth` argument
(it currently hard-codes `depth=24` at `:46`); add `depth=24` to its signature and pass it
through, which changes nothing for the existing five tests.

```python
DEPTH30 = (0x3FF00000, 0x000FFC00, 0x000003FF)   # red, green, blue of a 10-bit visual


def make_10bit_image(r, g, b, byte_order=0):
    """One depth-30 pixel. `bits_per_pixel` is still 32, which is the whole trap."""
    word = (r << 20) | (g << 10) | b
    order = range(0, 32, 8) if byte_order == 0 else range(24, -8, -8)
    pixels = np.array([[[(word >> s) & 0xff for s in order]]], dtype=np.uint8)
    return make_image(pixels, byte_order=byte_order, masks=DEPTH30, depth=30)


def test_a_ten_bit_visual_is_not_read_as_eight_bit(self):
    """A depth-30 visual lands on the BGRA fast path unless the mask *width* is checked.

    Unfixed, mid grey came back as [0, 2, 8] -- not a tint, a picture whose luminance is
    not even monotonic, with no exception and no log line.
    """
    from ok.compat import xshm

    for (r, g, b), expected in (((1023, 0, 0), [0, 0, 255]),
                                ((0, 1023, 0), [0, 255, 0]),
                                ((0, 0, 1023), [255, 0, 0]),
                                ((512, 512, 512), [128, 128, 128]),
                                ((1023, 1023, 1023), [255, 255, 255])):
        image, _buffer = make_10bit_image(r, g, b)
        self.assertEqual(expected, xshm.image_to_bgr(image)[0, 0].tolist())


def test_a_ten_bit_visual_on_a_big_endian_server(self):
    from ok.compat import xshm

    image, _buffer = make_10bit_image(1023, 0, 0, byte_order=1)
    self.assertEqual([0, 0, 255], xshm.image_to_bgr(image)[0, 0].tolist())


def test_the_eight_bit_path_still_takes_the_cheap_copy(self):
    """The regression guard for the fix: depth 24 must not fall into `_unpack_wide`."""
    from ok.compat import xshm

    pixels = np.array([[[1, 2, 3, 255]]], dtype=np.uint8)
    image, _buffer = make_image(pixels)
    self.assertEqual((0, 1, 2), xshm._channel_indices(image.contents))
    self.assertEqual([1, 2, 3], xshm.image_to_bgr(image)[0, 0].tolist())
```

### Reproducing the defect before the fix

```python
import ctypes, numpy as np
from ok.compat.win32_stub import install; install()
from ok.compat import xshm

DEPTH30 = (0x3FF00000, 0x000FFC00, 0x000003FF)
word = (512 << 20) | (512 << 10) | 512                    # mid grey
buf = (ctypes.c_ubyte * 4)()
buf[0:4] = bytes([(word >> s) & 0xff for s in (0, 8, 16, 24)])
img = xshm.XImage(width=1, height=1, format=xshm.Z_PIXMAP,
                  data=ctypes.cast(buf, ctypes.c_void_p).value, byte_order=0, depth=30,
                  bytes_per_line=4, bits_per_pixel=32,
                  red_mask=DEPTH30[0], green_mask=DEPTH30[1], blue_mask=DEPTH30[2])
print(xshm._channel_indices(img))                          # (0, 1, 2)  <- the fast path
print(xshm.image_to_bgr(ctypes.pointer(img))[0, 0])        # [0 2 8]    <- near-black
```

---

## P3-2 — minimizing the game **disables** the running task instead of pausing it [correctness] — **FIXED**

`ok/device/capture_methods/x11_capture.py:124-135` raises a `CaptureException` when the
grab returns nothing and the window is minimized. §4 Phase 3 asked for exactly that ("so
the UI can tell the user 'un-minimize the game'"), and §11 E4 correctly gated it on
`x11.exists()`. What neither checked is where a `CaptureException` *goes*.

The chain, all in the fork:

1. `base.py:43-44` re-wraps it, message preserved.
2. `TaskExecutor.next_frame` (`:286-309`) calls `self.method.get_frame()` on every
   iteration, and `check_enabled` (`:329-335`) does **not** stop it once the executor is
   paused — it sleeps 1 s and falls through. So the raise still happens after the window
   layer has paused everything.
3. The exception leaves `next_frame`, leaves the task (`ok/task/task.py:539` is how a task
   asks for one), and lands in the task loop's `except Exception` at
   `TaskExecutor.py:639`, which emits `capture_error` (`:641`), sets `task.running = False`
   (`:643`) and calls **`task.disable()` (`:644`)**.

So a minimize does not pause the bot, it **turns the task off**. After restoring the window
the user has to re-enable it by hand, and the app's own recovery path — which already
exists and already works — never gets a chance:

* `x11_window.py:410` computes `pos_valid = (not self.is_minimized()) and check_pos(...)`,
* `:411-417` pauses the executor on the transition and emits
  `'Paused because game window is minimized or out of screen!'`,
* and when the window comes back, `pos_valid` flips and play resumes.

The Windows path never reaches `task.disable()` for this: `BitBltCaptureMethod.do_get_frame`
(`bitblt.py:42-57`) returns whatever `capture_by_bitblt` produced and raises nothing for a
minimized window, so on Windows a minimize is only the pause above. **This is a
Linux-only behaviour change, introduced by Phase 3.**

One thing this pass did **not** measure, flagged because it widens the blast radius if
true: `x11.is_minimized` (`ok/compat/x11.py:374-391`) answers True for *any* window that is
not viewable (`:391`), so a window that is momentarily unmapped is "minimized" too. Whether
Wine/DXVK unmaps the game's toplevel during a fullscreen mode switch was not tested — the
game was not running for this pass. It is one `xprop -spy WM_STATE` away from being settled
and should be settled before Phase 4 puts real play time on this path.

### The patch

The capture layer should stop raising and let the window layer's pause carry the message —
it is the same message, it is already actionable, and it pauses rather than disables.

`ok/device/capture_methods/x11_capture.py`, in `__init__` (`:97-100`), add:

```python
        self._minimized_reported = False
```

and replace `do_get_frame`'s `:123-136` tail with:

```python
            frame = self.grabber.grab(hwnd, x, y, width, height)
            if frame is None and x11.exists(hwnd) and x11.is_minimized(hwnd):
                # Deliberately NOT a CaptureException. A CaptureException out of a task
                # reaches `TaskExecutor`'s `except Exception` (TaskExecutor.py:639), which
                # calls `task.disable()` (:644) -- so raising here turns a minimize into a
                # switched-off task the user has to turn back on. The window layer already
                # handles this correctly and reversibly: `pos_valid` goes False
                # (x11_window.py:410), the executor is paused and the user is told
                # "Paused because game window is minimized or out of screen!" (:411-417),
                # and play resumes when the window comes back.
                #
                # `exists` first, and it is not belt and braces: `is_minimized`'s last
                # resort is "not viewable", which a window id that no longer names anything
                # answers True [V7].
                if not self._minimized_reported:
                    self._minimized_reported = True
                    logger.info(f'{hwnd:#x} is minimized; X11 cannot capture it. '
                                f'The window layer pauses the executor and notifies.')
                return None
            if frame is not None:
                self._minimized_reported = False
            return frame
```

Nothing else changes: `CaptureException` stays imported for nothing, so drop the import at
`:40` as well, and trim the module docstring's third bullet (`:26-28`) — replace

```
* **A minimized window raises rather than returning None**, with a message the UI can show,
  because "un-minimize the game" is something the user can act on and a generic capture
  failure is not. Occlusion needs no such treatment on Xwayland [V7].
```

with

```
* **A minimized window returns None, it does not raise.** A `CaptureException` out of a
  task reaches `TaskExecutor.py:639` and is answered with `task.disable()` -- a minimize
  would switch the task off instead of pausing it. The window layer already pauses the
  executor and tells the user, reversibly, when `pos_valid` goes False. Occlusion needs no
  treatment at all on Xwayland [V7].
```

### Tests to change

`tests/test_x11_capture.py:253` `test_a_minimized_window_raises_something_the_user_can_act_on`
must be rewritten, not deleted — it is the guard for this whole finding:

```python
    def test_a_minimized_window_is_no_frame_and_does_not_kill_the_task(self):
        """A CaptureException here reaches TaskExecutor.py:639 -> task.disable().

        Minimizing the game must pause the bot (the window layer does that through
        `pos_valid`), never switch the task off. Returning None is what keeps that true.
        """
        method, grabber, hwnd_window = self.make(frame=None)
        with unittest.mock.patch('ok.compat.x11.exists', return_value=True), \
                unittest.mock.patch('ok.compat.x11.is_minimized', return_value=True):
            self.assertIsNone(method.do_get_frame())
            self.assertIsNone(method.do_get_frame())      # reported once, not per poll
```

(match `self.make(...)` to whatever the existing fixture in that class is named; the
existing test at `:253` shows the shape). `test_a_window_that_no_longer_exists_is_not_reported_as_minimized`
(`:265`) still passes unchanged and is still worth keeping — it is E4's guard.

Add one more, so the "report once" half is pinned:

```python
    def test_the_minimized_notice_is_logged_once_per_episode(self):
        method, grabber, hwnd_window = self.make(frame=None)
        with unittest.mock.patch('ok.compat.x11.exists', return_value=True), \
                unittest.mock.patch('ok.compat.x11.is_minimized', return_value=True), \
                unittest.mock.patch.object(x11_capture.logger, 'info') as info:
            method.do_get_frame()
            method.do_get_frame()
            self.assertEqual(1, info.call_count)
        grabber.frame = np.zeros((4, 4, 3), dtype=np.uint8)   # window restored
        method.do_get_frame()
        with unittest.mock.patch('ok.compat.x11.exists', return_value=True), \
                unittest.mock.patch('ok.compat.x11.is_minimized', return_value=True), \
                unittest.mock.patch.object(x11_capture.logger, 'info') as info:
            method.do_get_frame()
            self.assertEqual(1, info.call_count)          # a new episode reports again
```

### If you disagree with the direction

The alternative that keeps a capture-layer message is to raise only while the window layer
has *not yet* noticed — `if not hwnd_window.pos_valid: return None` before the raise. Do
not take it: the poll runs every 0.2 s and a task can sit inside `next_frame` for 6, so the
race is wide open and the failure it leaves is exactly the one above, just rarer and
therefore harder to attribute.

---

## P3-3 — `x11_capture_available()` is True for a `DISPLAY` nothing answers [correctness of the guard, diagnosability] — **FIXED**

`x11_capture.py:54-61` delegates to `xshm.available()` (`xshm.py:270-272`), which is
`the libraries load` **and** `DISPLAY is set`. Neither proves a server will answer. §11 E7
introduced this guard so that "a machine without X11 is not stranded on a backend that can
never produce a frame" — a stale or wrong `DISPLAY` is exactly that machine, and the guard
lets it through.

Measured with `DISPLAY=:99` (no server):

```
x11_capture_available: True
x11.available (python-xlib): False
ERROR xshm:cannot connect to X display ':99' for capture
grab -> None
ERROR xshm:cannot connect to X display ':99' for capture
grab -> None
ERROR xshm:cannot connect to X display ':99' for capture
grab -> None
```

Two defects in one: the branch at `update.py:42-52` selects `X11`, returns it, and never
falls through to anything else; and `_open` (`xshm.py:377-393`) logs at ERROR on **every**
grab, so the log is the failure rather than a report of it. Note the window layer's own
guard already gets this right — `ok/compat/x11.available()` (`x11.py:98-101`) opens a
connection and answers False.

### The patch

`ok/device/capture_methods/x11_capture.py:54-61`:

```python
def x11_capture_available():
    """True when the pixel path can run at all: the libraries load, and a display answers.

    The sibling of ``windows_graphics_available()``, and used the same way -- to keep
    ``update_capture_method`` from selecting a backend that can never produce a frame, so
    the next entry in the user's ``capture_method`` list gets its turn.

    ``xshm.available()`` alone is not enough: it proves libX11/libXext loaded and
    ``DISPLAY`` is set, and a stale ``DISPLAY`` passes both while every grab fails.
    ``x11.available()`` is the window layer's own guard and actually opens a connection,
    on a connection it then keeps.
    """
    return xshm.available() and x11.available()
```

`x11` is already imported at `:39`; nothing else moves.

`ok/compat/xshm.py`, `_open` (`:377-393`) — make the two failures log once, the way
`_load` already does with `_load_error_logged` (`:154`, `:252-254`). Add beside it:

```python
_open_error_logged = False
```

and in `_open`, replace the two bare `logger.error(...)` calls with:

```python
        global _open_error_logged
        name = os.environ.get('DISPLAY')
        if not name:
            if not _open_error_logged:
                _open_error_logged = True
                logger.error('DISPLAY is not set; X11 capture needs X11 or Xwayland')
            return None
        display = libs.x11.XOpenDisplay(name.encode())
        if not display:
            if not _open_error_logged:
                _open_error_logged = True
                logger.error(f'cannot connect to X display {name!r} for capture')
            return None
        _open_error_logged = False
        self._display = display
        return display
```

### Tests to add

```python
    def test_an_unanswerable_display_is_not_available(self):
        """A stale DISPLAY passes `xshm.available()` and then fails every grab.

        `xshm.available()` is `the libraries load` and `DISPLAY is set`; neither proves a
        server answers. Measured before the fix with `DISPLAY=:99`:
        `x11_capture_available()` True, `x11.available()` False, and one ERROR per grab.
        """
        from ok.compat import x11
        from ok.device.capture_methods import x11_capture

        with unittest.mock.patch.object(x11, 'available', return_value=False):
            self.assertFalse(x11_capture.x11_capture_available())
        with unittest.mock.patch.object(x11, 'available', return_value=True), \
                unittest.mock.patch('ok.compat.xshm.available', return_value=True):
            self.assertTrue(x11_capture.x11_capture_available())
```

Patch `x11.available`, do **not** point the real `DISPLAY` at a dead server in a unit test:
`ok/compat/x11.py` memoises its connection in a module global (`_display`, `x11.py:36`), so
a test that actually connects to `:99` leaves a `None` behind and every live test that runs
later in the same process silently skips or fails. What needs pinning here is the
composition, not python-xlib's connect — that is `x11.available()`'s own job and it already
has tests. The behaviour with a genuinely dead display is reproduced out-of-process in the
snippet below.

### Reproducing the defect before the fix

```sh
cd /home/max/vsCODE/ok-script-linux
DISPLAY=:99 /home/max/vsCODE/okport-venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from ok.compat.win32_stub import install; install()
from ok.compat import x11, xshm
from ok.device.capture_methods import x11_capture
print('x11_capture_available:', x11_capture.x11_capture_available())   # True  <- the bug
print('x11.available:', x11.available())                               # False <- the truth
g = xshm.X11Grabber()
for _ in range(3):
    print('grab ->', g.grab(0x123456, 0, 0, 100, 100))                 # ERROR each time
"
```

The existing `test_an_unavailable_pixel_path_falls_through_to_the_next_method`
(`tests/test_x11_capture.py:362`) already covers the fall-through and needs no change.

---

## P3-4 — `get_name()` reports a composite path that is not being used [contract, diagnosability] — **FIXED**

`x11_capture.py:138-139`:

```python
    def get_name(self):
        return 'X11_Composite' if self.grabber.use_composite else 'X11'
```

`use_composite` is what the user *asked for*, not what the grabber is *doing*. Two ways
they part company:

**(a) A silent fallback keeps the name.** `_composite_pixmap` (`xshm.py:522-577`) sets
`_composite_failed` and returns 0 in three places — no libXcomposite (`:538`), no Composite
extension on the server (`:543-550`), a refused `XCompositeRedirectWindow` (`:557-565`) —
and from then on every grab is the plain direct path. `get_name()` still says
`X11_Composite`, and so does everything that logs it: `DeviceManager`, the GUI's
capture-method display, and `tools/check_linux_startup.py:116`. The three `logger.info`
lines are the only trace, and they are below the level most users will ever look at.

**(b) A method switch lags by one frame.** `update.py:49` sets the module flag and
`get_capture` (`:89-96`) hands back the *same live object*; the grabber is only rebuilt
inside `do_get_frame` (`x11_capture.py:108-112`). Between the switch and the next frame,
`get_name()` reports the old path. `check_linux_startup.py:119` accepts either name so the
gate does not catch it, and `DeviceManager` logs the wrong one.

Neither is a wrong picture. Both make the one question you ask when the composite path
misbehaves — "which path am I actually on?" — unanswerable from the log.

### The patch

`ok/compat/xshm.py`, on `X11Grabber`, beside `shm_active` (`:671-675`):

```python
    @property
    def composite_active(self):
        """True when grabs really are going through the XComposite pixmap.

        Distinct from ``use_composite``, which is what was asked for: the composite path
        falls back to the direct grab silently and permanently on a missing libXcomposite,
        a server without the extension, or a refused redirect.
        """
        with self._lock:
            return bool(self.use_composite and not self._composite_failed)
```

`ok/device/capture_methods/x11_capture.py` — `get_name` becomes:

```python
    def get_name(self):
        # `composite_active`, not `use_composite`: the composite path degrades to the
        # direct grab silently, and a name that keeps claiming otherwise is the reason a
        # composite problem is hard to see in a log.
        return 'X11_Composite' if self.grabber.composite_active else 'X11'
```

and add, for (b):

```python
    def use_composite_path(self, composite):
        """Switch the grabber between the direct and the XComposite path, now.

        Called by ``update_capture_method``: ``get_capture`` hands back this same object
        across a reconfiguration, so the path cannot be a constructor argument -- and
        leaving the rebuild to the next ``do_get_frame`` means ``get_name()`` reports the
        old path until a frame happens to be asked for.
        """
        with self.lock:
            if self.grabber.use_composite != composite:
                self.grabber.close()
                self.grabber = xshm.X11Grabber(use_composite=composite)
```

`ok/device/capture_methods/update.py:49-52` becomes:

```python
                x11_capture.use_composite = (method_name == 'X11_Composite')
                if x11 := get_capture(capture_method, X11CaptureMethod, hwnd, exit_event):
                    x11.use_composite_path(x11_capture.use_composite)
                    logger.info(f'use {method_name} capture')
                    return x11
```

Keep `do_get_frame`'s lazy rebuild (`:108-112`) as it is — it is now a safety net rather
than the only path, and it costs one comparison per frame.

### Tests to add

```python
    def test_the_name_follows_the_path_actually_taken(self):
        method, grabber, _ = self.make()
        method.grabber.use_composite = True
        method.grabber._composite_failed = False
        self.assertEqual('X11_Composite', method.get_name())
        method.grabber._composite_failed = True          # silently fell back
        self.assertEqual('X11', method.get_name())

    def test_switching_the_path_takes_effect_before_the_next_frame(self):
        """`get_capture` reuses the object, so `update_capture_method` must not wait."""
        # extend tests/test_x11_capture.py:355 `test_x11_composite_sets_the_flag` with:
        self.assertTrue(capture.grabber.use_composite)
        self.assertEqual('X11_Composite', capture.get_name())   # without a frame first
```

`test_switching_to_composite_rebuilds_the_grabber` (`:310`) covers the `do_get_frame` path
and stays.

---

## P3-5 — the letterbox crop takes all vertical slack off the top [observation, NOT verified against the game] — **OPEN, needs the game running**

`capture_rect` (`x11_capture.py:84`) and the inherited `HwndWindow.get_capture_origin` both
call `get_crop_point(client_width, client_height, width, height)`, and `get_crop_point`
(`geometry.py:14-17`) splits the *horizontal* slack evenly while giving **all** the
vertical slack to the top:

```python
    x = round((frame_width - target_width) / 2)
    y = (frame_height - target_height) - x
```

`geometry.py:8-10` explains why, and the explanation is a Windows one: `y` is "the *title
bar*, i.e. all remaining vertical slack after subtracting one border". That is right in
**window** coordinates, which is what `BitBltCaptureMethod.do_get_frame` passes
(`bitblt.py:47-48`: `get_crop_point(self.hwnd_window.window_width,
self.hwnd_window.window_height, ...)`).

On Linux the crop is computed in **client** coordinates — correctly, per §11 E5, because
the X client window *is* the client area and decorations belong to the WM's frame
(`window_x11.py:161-176`). So there is no title bar in the slack. When
`do_update_window_size` crops the height for the aspect ratio (`x11_window.py:403-407`),
every pixel of slack is real letterbox, and this formula takes it all off the top.

Worked example, arithmetic only:

| | |
|---|---|
| client geometry | 1920 x 1200 |
| `frame_aspect_ratio` | 16:9, so `height` becomes `int(1920 / 1.7778)` = 1080 |
| `get_crop_point(1920, 1200, 1920, 1080)` | `x = 0`, `y = 120 - 0 = 120` |
| captured rows | 120 .. 1200 |
| correct if the game letterboxes 60 top / 60 bottom | 60 .. 1140 |

i.e. 60 rows of content lost at the top and 60 rows of black gained at the bottom.

**Why this is filed as an observation and not a finding with a patch:**

1. It is unreachable at 16:9, and `config.py`'s `supported_resolution` (`ratio: '16:9'`,
   `resize_to` all 16:9) plus `try_resize_to` steer the window there.
2. Capture and the overlay use the **same** origin, so clicks still land where the picture
   says they do. The symptom is a mis-framed picture, not mis-aimed input.
3. The formula is upstream's and shared with Windows. Changing `get_crop_point` changes
   BitBlt too, which is not this port's call; the honest fix would be a Linux-only origin
   in `capture_rect` **and** a matching override of `get_capture_origin` in `X11Window`,
   which is a bigger change than the evidence currently justifies.
4. **It has not been checked against the game.** The game was not running for this pass.

**What to measure before touching anything** — the whole question is whether a
non-16:9 Proton window letterboxes at all, or just renders the window's real aspect:

```sh
# game running, windowed, deliberately taller than 16:9 (e.g. 1920x1200)
PYTHONPATH=. python3 - <<'PY'
from config import config
from ok import OK
ok = OK(config); ok.device_manager.update_pc_device(); ok.device_manager.do_start(notify=False)
w, cap = ok.device_manager.hwnd_window, ok.device_manager.capture_method
w.do_update_window_size()
print('client', w.client_width, w.client_height, 'cropped', w.width, w.height)
import cv2; cv2.imwrite('/tmp/okww-crop.png', cap.get_frame())
PY
```

Then look at `/tmp/okww-crop.png`: a black band along the **bottom** and clipped content at
the top is this defect; content filling the frame is the game rendering the window's own
aspect, and there is nothing to fix. Record the answer here either way.

---

## P3-6 — the runtime shared libraries are a hard requirement nothing records [documentation] — **FIXED**

`ok/compat/xshm.py:249-250` loads `libX11.so.6` and `libXext.so.6`, and `:257` optionally
`libXcomposite.so.1`. None of the three is a Python package, so neither
`requirements-linux.txt` nor `pyproject.toml` can pull them and neither mentions them.

If `libXext` (or `libX11`) is absent the consequence is total and quiet: `_load()` returns
None -> `x11_capture_available()` is False -> the branch at `update.py:42-45` is skipped
for **both** names -> `update_capture_method` returns None -> `do_start` selects no capture
method at all. The single trace is one line, `libX11/libXext are not loadable, X11 capture
is unavailable: ...`, logged once by design (`xshm.py:252-254`).

`LINUX.md`'s "What Phase 3 added" table names the libraries in a cell describing what
`xshm.py` does, but nowhere says they must be installed, and the install snippet at the
bottom of "Test baseline on Linux" lists only Python packages. ok-ww's CI gets them
transitively through `xvfb` (`.github/workflows/linux.yml:49-51`), which is why nothing has
noticed.

### The patch

One paragraph in `LINUX.md`, in the Phase 3 section, after the "Five things are
load-bearing" list:

```markdown
### System libraries

The pixel path is `ctypes` over the system X libraries, so they are a **runtime
requirement** that no Python lock can express:

| | Fedora | Debian / Ubuntu |
|---|---|---|
| required | `libX11`, `libXext` | `libx11-6`, `libxext6` |
| optional (`X11_Composite` only) | `libXcomposite` | `libxcomposite1` |

Without `libX11`/`libXext`, `x11_capture_available()` is False, both `X11` and
`X11_Composite` are skipped, `update_capture_method` returns None and the app starts with
no capture method — with one log line as the only trace
(`libX11/libXext are not loadable, X11 capture is unavailable`). Without `libXcomposite`,
`X11` works and `X11_Composite` degrades to it.
```

The Fedora names were confirmed on this machine (`rpm -qf /usr/lib64/libX11.so.6` ->
`libX11`, and likewise for the other two). Phase 6 (packaging) is where these become
`Requires:` lines; this is the note that keeps them from being forgotten until then.

---

## P3-7 — the ok-ww workflow step is still called `Phase 2 exit gate` [documentation] — **FIXED**

`.github/workflows/linux.yml:60` names the step `Phase 2 exit gate`, and `tools/check_linux_startup.py`
now carries the Phase 3 assertions too (its own docstring says so, `:2`, "Phase 2 and Phase
3 exit gate"). Run **33672918236**'s log therefore reads
`Phase 2 exit gate  OK    capture backend is X11CaptureMethod`.

Cosmetic, and worth fixing in the same commit as anything else here because this file's
step names are what the sixth pass's "read the run, not the YAML" rule quotes.

```yaml
      - name: Phase 2-3 exit gate
        run: xvfb-run -a python tools/check_linux_startup.py
```

The header comment at `:1-11` is still accurate and needs no change.

---

## Suggested order (seventh pass)

1. **P3-2** — it is the only one that changes what a user experiences today, and it is a
   deletion plus a flag.
2. **P3-3** — two small edits, and it removes a log flood that would otherwise bury the
   evidence for anything else.
3. **P3-1** — self-contained, latent, and closes a whole class. Do it before Phase 4 so the
   capture layer is not still moving while input lands on top of it.
4. **P3-4**, **P3-6**, **P3-7** — one commit; none of them can break anything.
5. **P3-5** — do not patch. Run the measurement above the first time the game is up for
   Phase 4 and record the answer in this file.

Re-run afterwards, from the fork root and this repo:

```sh
V=/home/max/vsCODE/okport-venv
$V/bin/python -m pytest tests --tb=no -o addopts="-ra"        # expect 6 failed, 484+N passed, 1 skipped
$V/bin/python -m pytest tests/test_x11_capture.py -o addopts="-ra"
env -u DISPLAY $V/bin/python -m pytest tests/test_x11_window.py tests/test_x11_capture.py -o addopts="-ra"
$V/bin/python tools/scan_module_level_win32.py --check && $V/bin/python tools/check_linux_imports.py
PYTHONPATH=. $V/bin/python tools/check_linux_startup.py       # from ok-wuthering-waves-linux
```

Then push the fork, repin `requirements-linux.txt:35` to the new commit, push ok-ww, and
read **both** runs' logs — P2-9a/P2-15/P2-16's rule, which has caught a false green three
times in this file.

## State after this pass

| | |
|---|---|
| ok-script-linux | `493354a` on `linux-port`, pushed, clean; CI **33672722286** green |
| ok-ww | `ed8813a` on `master`, pushed, clean; CI **33672918236** green, and its log shows the X11 backend selected |
| Lock | `requirements-linux.txt:35` -> `493354a` |
| Phases 0-1 | Re-verified: 27 offenders, 70/70 lazy imports, the `winreg` stub's `FileNotFoundError` contract holds against ok-ww's own registry code |
| Phase 2 | Re-verified: all fourteen fixes still in the code, 74 tests, no regression from Phase 3 |
| Phase 3 | Works, and against the real game per §11. Seven findings above, none blocking |
| Open | **P2-17** (inherited, not ours) and **P3-1 .. P3-7** |
| Phase 4 readiness | Nothing here blocks it. P3-2 should land first — Phase 4 is the phase that will actually leave the bot running while the user does something else, which is when a task that switches itself off gets noticed |

---

# Eighth pass — the seventh pass's Phase 3 findings, closed (2026-09-02)

Six of the seven went in; **P3-5 was deliberately left alone**, which is what the seventh
pass's own suggested order asked for. Everything below was executed on this machine
(`DISPLAY=:0`, real KWin/Xwayland, two monitors, **the game still not running**) against
the venv at `/home/max/vsCODE/okport-venv`.

| | Outcome |
|---|---|
| P3-1 | **fixed** — ok-script-linux `9a53b14`, tightened in `5f1987e`. `_channel_fields` carries each mask's *width*, `_channel_indices` returns `None` for a channel that is not 8 bits wide, and `_unpack_wide` decodes that case. All six 10-bit probes now correct, including mid grey `[0, 2, 8]` -> `[128, 128, 128]` |
| P3-2 | **fixed** — `do_get_frame` returns `None` for a minimized window and logs once per episode instead of raising. The `CaptureException` import is gone; the module docstring and `LINUX.md`'s load-bearing list say why |
| P3-3 | **fixed** — `x11_capture_available()` is `xshm.available() and x11.available()`, and `_open`'s two failures log once, as `_load`'s already did. Re-measured with `DISPLAY=:99`: `False` (was `True`), and **one** ERROR for three grabs (was three) |
| P3-4 | **fixed** — `X11Grabber.composite_active` reports the path actually taken, `get_name()` reads it, and `update_capture_method` calls the new `use_composite_path` so a switch does not wait for the next frame |
| P3-5 | **still open, still an observation, and still not measurable** — the game was not running for this pass either. Not patched, per the seventh pass's own recommendation. The measurement snippet in P3-5 is unchanged and is the first thing to run when Phase 4 brings the game up |
| P3-6 | **fixed** — `LINUX.md` gains a **System libraries** subsection under Phase 3 with the Fedora and Debian package names and what their absence costs |
| P3-7 | **fixed** — `.github/workflows/linux.yml:60` is now `Phase 2-3 exit gate` |
| P2-17 | **still open, still inherited, still not ours** — nothing changed; the sixth pass's disproof of option (a) stands |

## What was measured, not read

**P3-1.** The seventh pass's five probes plus a black control and an MSBFirst control, on a
hand-made depth-30 `XImage` (`bits_per_pixel=32`, masks `R=0x3FF00000 G=0x000FFC00
B=0x000003FF`):

| 10-bit pixel | before | after |
|---|---|---|
| red `(1023, 0, 0)` | `[0, 0, 240]` | `[0, 0, 255]` |
| green `(0, 1023, 0)` | `[0, 252, 15]` | `[0, 255, 0]` |
| blue `(0, 0, 1023)` | `[255, 3, 0]` | `[255, 0, 0]` |
| mid grey `(512, 512, 512)` | `[0, 2, 8]` | `[128, 128, 128]` |
| white | `[255, 255, 255]` | `[255, 255, 255]` |
| black | `[0, 0, 0]` | `[0, 0, 0]` |
| red, MSBFirst | — | `[0, 0, 255]` |

`_channel_indices` on that image is `(None, None, None)` after the fix — which is what
routes it to `_unpack_wide` — and is still `(0, 1, 2)` for a depth-24 image, so the
measured `cv2.cvtColor` fast path is untouched. That last one is a test
(`test_the_eight_bit_path_still_takes_the_cheap_copy`), not a comment.

**The cost of the width check, and what it was traded for.** `image_to_bgr` needs both the
fields and the byte indices. Written the way the seventh pass specified, it derived the
fields twice per frame — `_channel_fields` 1.16 us + `_channel_indices` 1.68 us = 2.84 us,
against ~1.0 us before. `5f1987e` splits out `_indices_from_fields`, so the per-frame cost
is one derivation (1.16 us) and `_channel_indices` is its one-line composition, unchanged
for its callers and its tests. Against a 1.0-1.8 ms frame either number is noise; it was
worth removing because it is free to remove.

**P3-2.** `TaskExecutor.py:638-644` re-read: `except Exception` -> `capture_error.emit()`
-> `task.running = False` -> **`task.disable()`**. The chain the seventh pass described is
exactly what is in the code. The live test that used to assert the raise
(`test_an_iconified_window_is_a_capture_exception_not_a_stale_frame`) is now
`test_an_iconified_window_is_no_frame_not_a_stale_one` and asserts `None`; it ran green on
this desktop, and its log line is the one-per-episode notice:

```
INFO x11_capture:0x4e00000 is minimized; X11 cannot capture it. The window layer pauses the executor and notifies.
```

The stale-frame half of that test — restore, repaint, grab again — is unchanged and still
passes, so the thing it was really guarding (a compositing WM's backing pixmap making a
minimized window look like a working capture) is still guarded.

**P3-3.** Out of process, so nothing memoises a bad connection into the rest of the run:

```
$ DISPLAY=:99 python -c "...x11_capture.x11_capture_available(); three grabs..."
x11_capture_available: False           # was True
xshm.available: True  x11.available: False
ERROR xshm:cannot connect to X display ':99' for capture
grab -> None
grab -> None
grab -> None
```

One ERROR, three grabs. Before the fix it was one ERROR *per* grab, and
`x11_capture_available()` was True — so `update.py:42-52` selected the backend and never
fell through. The unit test patches `x11.available` rather than pointing the real `DISPLAY`
at a dead server, for the reason the seventh pass gave: `ok/compat/x11.py` memoises its
connection in a module global, and a test that really connects to `:99` leaves a `None`
behind that silently skips or fails every live test after it.

**P3-4.** Live, on a 1920x1080 test window painted `0x336699`:

| | ms/frame | `shm_active` | `use_composite` | `composite_active` | centre pixel |
|---|---|---|---|---|---|
| direct | 1.78 | True | False | False | `[153, 102, 51]` |
| composite | 1.68 | True | True | True | `[153, 102, 51]` |

Both paths still land the colour the seventh pass measured (BGR of `0x336699`, no double
swap), and the two are still within noise of each other. `composite_active` is False the
moment `_composite_failed` is set, which is the unit test
`test_the_name_follows_the_path_actually_taken`. The switch-without-a-frame half is
`test_switching_the_path_takes_effect_before_the_next_frame`, and it goes through the real
`update_capture_method` with the live object passed back in — the reuse path, which is the
only way the lag was reachable.

## Verification state (eighth pass)

| | |
|---|---|
| Fork suite | **491 passed / 6 failed / 1 skipped / 16 subtests** (498 collected). +7 passes and +6 subtests over the seventh pass's 484/10; the 6 failures are §9b's Windows-only set, unchanged |
| `tests/test_x11_capture.py` | **41 passed** (was 34) |
| `tests/test_x11_window.py` | **74 passed**, unchanged — Phase 3's edits touched nothing it covers |
| Both files, no `DISPLAY` | **92 passed / 23 skipped** (was 85/23) |
| `tools/scan_module_level_win32.py --check` | exit 0, `TOTAL 27`, same 4 calling a loader at import |
| `tools/check_linux_imports.py` | exit 0, **70/70** |
| `tools/check_linux_startup.py` | `PASS` — `do_start selected X11 + PostMessageInteraction`, `capture backend is X11CaptureMethod`, frame step reports itself skipped with no game |
| Throughput | direct 1.78 ms, composite 1.68 ms at 1920x1080 — the same 6-9x-over-`XGetImage` shape §11 measured; this machine was under more load today than during the seventh pass |
| Lock ⇄ fork pin | `requirements-linux.txt:35` -> `5f1987e`, confirmed fetchable with no credentials (`GIT_CONFIG_GLOBAL=/dev/null git -c credential.helper= ls-remote`), which is how pip clones it |

Reproduce the whole set:

```sh
V=/home/max/vsCODE/okport-venv
cd /home/max/vsCODE/ok-script-linux
$V/bin/python -m pytest tests --tb=no -o addopts="-ra"
$V/bin/python -m pytest tests/test_x11_capture.py -o addopts="-ra"
env -u DISPLAY $V/bin/python -m pytest tests/test_x11_window.py tests/test_x11_capture.py -o addopts="-ra"
$V/bin/python tools/scan_module_level_win32.py --check && $V/bin/python tools/check_linux_imports.py
cd /home/max/vsCODE/ok-wuthering-waves-linux && PYTHONPATH=. $V/bin/python tools/check_linux_startup.py
```

## A note on the commits

Every commit in this pass is **signed**, but not on the first attempt: `git commit` could
not reach a pinentry from the session that wrote them (`gpg failed to sign the data ...
PINENTRY_LAUNCHED`), so they went in with `--no-gpg-sign` first — which is what `493354a`
already is, so the history was mixed rather than uniformly signed. The agent unlocked
later, and both branches were re-signed with
`git rebase --exec 'git commit --amend --no-edit -S'` and force-pushed. The rewrite is
byte-identical: the pre-rewrite head's tree and the re-signed head's tree are the same
object (`23e61ac`), so only the commit objects changed.

That rewrite is why the CI run IDs below are **not** the ones the first push produced
(`33692712165` / `33692885303`, both `success` on the pre-rewrite SHAs). Those runs proved
the same trees, but this file's own rule is a green run on the *exact* pair, so the pair
below is the one that counts.

## State after this pass

| | |
|---|---|
| ok-script-linux | `5f1987e` on `linux-port`, pushed, clean, **signed**; CI `Linux port gates` **33693264759** `success` |
| ok-ww | `57a1234` on `master`, pushed, clean, **signed**; CI `Linux startup gate` **33693364875** `success`, and its log carries the renamed step plus `OK    do_start selected X11 + PostMessageInteraction` and `OK    capture backend is X11CaptureMethod` |
| Lock | `requirements-linux.txt:35` -> `5f1987e` |
| Phases 0-2 | Untouched by this pass and still green: 74 `test_x11_window.py` tests, 27 offenders, 70/70 lazy imports |
| Phase 3 | Six of seven findings closed in code and docs; P3-5 is the only Phase 3 item left and it needs the game |
| Open | **P2-17** (inherited, not ours) and **P3-5** (needs the game running) |
| Phase 4 readiness | Nothing blocks it. P3-2 landed first, which is what the seventh pass asked for — Phase 4 is when a task that switches itself off would actually be noticed. Two things to settle with the game up: P3-5's letterbox measurement, and the `xprop -spy WM_STATE` question from P3-2 (does Wine/DXVK unmap the toplevel during a fullscreen mode switch, which `is_minimized`'s "not viewable" last resort would read as minimized) |
