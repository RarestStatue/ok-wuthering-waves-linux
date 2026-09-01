# GAPS — review of the Phase 0-1 implementation (2026-09-01)

> **Resolved 2026-09-01.** Every finding below was re-verified by execution before being
> acted on. Fixes are in ok-script-linux `cba672b`, `c700b2d`, `12f64a3` and in this repo's
> lockfile pin and `PORT.md` §9 C7-C9 / §9b.
>
> | | Outcome |
> |---|---|
> | G1 | fixed — `_CALL_ERRORS = {'winreg': FileNotFoundError}`, plus both-guard-styles and end-to-end tests |
> | G2 | fixed — `OPTIONAL_EXTRAS` removed outright |
> | G3 | fixed at the source, not documented around — `TaskTab`'s unparented `QTimer` was the leak; suite now stable at 376/6/1 across three runs |
> | G3b | **cause was wrong.** Not `os._exit`: `pytest.ini`'s `addopts` already carries `-q`, so a second `-q` raises quiet to level 2 and suppresses the stats line. Traced `os._exit` during a full run and it is never called |
> | G4 | fixed — pinned to `12f64a34...`, with the repin step in the regeneration recipe |
> | G5 | fixed — `.github/workflows/linux.yml` on `ubuntu-latest`, the six known failures deselected by node id |
> | G6 | fixed — `publish.yml` gated on `github.repository == 'ok-oldking/ok-script'` |
> | G7 | fixed — `is not None` in both places, with a regression test that holds fd 0 |
> | G8 | fixed — `UNAVAILABLE` sentinel; `check_mutex` refuses to start instead of killing |
> | G9 | fixed — both walks cover `tests/`; widening them immediately surfaced two false positives in the meta-test, now excluded |
> | G10 | fixed — separate non-blocking CI job, and `LINUX.md` flags it as network-dependent |
> | G11 | fixed — the three edits are relabelled Phase 3/4, recorded as §9 C8 |
> | G12 | fixed — recorded as §9 C7 |
> | G13 | fixed — recorded as §9 C9, carried into Phase 2's exit gate |
> | G14 | fixed — docstring rewritten as belt-and-braces; the file is kept |
> | G15 | fixed — audit recorded in the `win32_stub` docstring |
> | G16 | **rejected in part.** The `cv2` diagnosis is right and the `LINUX.md` half is done, but declaring `opencv-python` in the fork is not a fix: upstream's `tests/test_package_metadata.py` asserts that no profile mentions opencv (commit "Refactor dependency profiles for headless installs"), so that a headless consumer can choose `opencv-python-headless`. Attempting it turns that test red |
>
> One further correction the review did not catch: §9's "ok-ww's own suite: 17/17" does not
> reproduce. Default discovery collects 12, all passing; the other 30 modules are named
> `Test*.py` and need an explicit `python_files` override plus a running game.

Review of `PORT.md` §4 Phase 0 / Phase 1 against what actually shipped in
`/home/max/vsCODE/ok-script-linux` (branch `linux-port`, HEAD `e735836`, in sync with
`origin/linux-port`) and in this repo (`9effbc3`, `7870eb6`).

Everything below was **executed**, not read. Reproduction environment:

```sh
python3.12 -m venv v312
v312/bin/pip install -e '/home/max/vsCODE/ok-script-linux[web,default,qt,adb,ocr,dev]' \
    pytest-qt opencv-python==5.0.0.93 openvino polib
```

---

## What checks out

Phase 1's substance is correct and the §9 implementation record is accurate on every
load-bearing claim. Verified independently:

| Claim | Result |
|---|---|
| `tools/scan_module_level_win32.py --check` | exit 0 — 27 offenders, the same 4 calling a loader at import |
| `tools/gen_win32con.py --check` | exit 0 — both generated files current, 94 constants |
| `tools/check_linux_imports.py` | exit 0 — **70/70** resolved, 0 skipped, 0 failed |
| ok-ww's own suite | **17/17** |
| `pip install --dry-run -r requirements.txt` on Linux | fails: `No matching distribution found for pywin32==311` |
| `pip install --dry-run -r requirements-linux.txt` | exit 0 |
| Where startup stops | exactly `hwnd_window.py:392 get_monitors_bounds() → NotImplementedError: win32api.EnumDisplayMonitors`, as documented |
| `windows_graphics_available()` | returns `None`, `WINDOWS_BUILD_NUMBER == -1`, never touches `ok.rotypes` |
| `get_crop_point` / `parse_reg_flag` | transcribed verbatim into `geometry.py`, asymmetry intact |

Two extra checks the plan did not ask for, both clean:

* **Whole-tree import sweep** (stronger than the `_LAZY_IMPORTS` sweep): 233 modules under
  `ok/`, excluding `ok.rotypes` and `ok.capture.windows`, all import on Linux. The single
  failure is `ok.ocr.download_paddle_model`, which wants the third-party `paddleocr` — not
  a port issue. Worth promoting into `tools/check_linux_imports.py`; it would have caught
  anything `_LAZY_IMPORTS` does not reach.
* **Silent-corruption audit.** `grep -rhoE '(win32api|win32gui|…)\.[A-Z][A-Z0-9_]{2,}'`
  over `ok/` yields only `win32api.MAKELONG` (implemented), `win32gui.WNDCLASS` (called →
  raises), and `pydirectinput.FAILSAFE/LEFT/RIGHT` (only ever passed to a stubbed call that
  raises first). So carving out `win32con` alone genuinely is sufficient — no other stubbed
  attribute is used as a value.

---

## G1 — `winreg` stub raises bare `OSError`; half the callers guard on `FileNotFoundError` [correctness, fix first]

`ok/compat/win32_stub.py:66-68` sets `_CALL_ERRORS = {'winreg': OSError}`. PORT.md C5
justifies `OSError` because "every caller already handles [it] as nothing registered".
That is true of ok-ww's `config.py`, but **not** of ok-script's own
`ok/alas/emulator_windows.py`, which guards registry lookups with `except
FileNotFoundError` in **11 places** (lines 203, 228, 233, 241, 374, 387, 406, 431, 437,
478, 486). A bare `OSError` is not caught by those.

Reproduced:

```
>>> EmulatorManager().all_emulator_instances
ESCAPED: OSError Windows-only symbol called on linux: winreg.OpenKey
```

**Fix:** `_CALL_ERRORS = {'winreg': FileNotFoundError}`.

`FileNotFoundError` is a subclass of `OSError`, so every existing `except OSError` caller
(ok-ww `config.py:_find_most_recently_run_pc_exe`, `emulator_windows.py:34,50`) keeps
working, *and* it is what real `winreg` raises for a missing key — strictly more accurate
than the current choice. Verified: with `_error` swapped to `FileNotFoundError`,
`EmulatorManager().all_emulator_instances` returns `[]` cleanly.

Also update `tests/test_linux_win32_compat.py:124-134`
(`test_winreg_calls_raise_oserror`) to assert **both** guard styles catch — the current
test asserts only `OSError` and therefore passes over this bug.

Reachability today is limited (`DeviceManager.refresh_emulators` returns early when
`adb_capture_config is None`, and `do_refresh` logs exceptions), so this is not a startup
blocker — but it is a latent trap on the ADB path and the fix is one word.

## G2 — the Phase-1 exit gate can green over a real failure

`tools/check_linux_imports.py:54` skips `run_web` on **any** `ModuleNotFoundError`, not
just one naming a `web`-extra module. Observed during this review, in a venv that had the
`web` extra but not `cv2`:

```
SKIP  run_web    missing optional dependency -- ok-script's 'web' extra …: No module named 'cv2'
```

If `run_web` were the only failure, the gate would print `69/70 … 0 failed` and exit 0
while `ok.ui.web.server` was genuinely broken.

PORT.md C2 already says the skip is unnecessary (`run_web` resolves without the extra, and
it did here: 70/70, 0 skipped). **Remove `OPTIONAL_EXTRAS` entirely**, or narrow it to
`exc.name in {'fastapi', 'uvicorn', 'webview'}`. Drop the now-dead `SKIP` prose from
PORT.md §4/1c's exit-criterion snippet at the same time.

## G3 — the fork's documented test baseline is not reproducible

`LINUX.md` claims **383 passed / 6 failed / 1 skipped**. Measured here (junit-xml, which
is authoritative — see G3b): **390 tests, 378 passed, 11 failed, 1 skipped**, and the
extra failure set *changes between runs of the same command*:

| run | extra failures beyond the documented six |
|---|---|
| 1 | `test_template_tab::test_search_reuses_cards_and_clears_hidden_selection`, `test_web_server::{test_run_web_logs_start_failure_and_reraises, test_default_web_launch_opens_pywebview, test_pywebview_launch_mode_opens_pywebview_without_debug, test_run_web_reuses_existing_ok_instance}` |
| 2 | `test_template_tab::{test_markup_close_emits_the_editor_coco_data, test_removing_item_only_removes_its_card}`, `test_web_server::{…, test_server_launch_mode_runs_without_opening_client}` |

Every one of them **passes when its file is run alone** (`pytest tests/test_web_server.py`
→ exactly the 2 documented failures; `pytest tests/test_template_tab.py` → 9 passed). The
documented six reproduce exactly.

Cause is visible in the log — a leaked Qt timer from an earlier test firing inside a later
one, which pytest-qt attributes to the current test:

```
CALL ERROR: Exceptions caught in Qt event loop:
  File "ok/ui/qt/tasks/TaskTab.py", line 82, in update_info_table
    current_task = og.executor.current_task
AttributeError: 'NoneType' object has no attribute 'current_task'
```

This is very likely upstream test-isolation debt rather than a port regression, but as
written the baseline cannot serve its stated purpose ("a *new* failure outside this list is
a regression"). Either fix the isolation (tear the `TaskTab` timer down in a fixture), or
restate `LINUX.md`'s baseline as per-file, name the flaky set explicitly, and have CI (G5)
run the suite per-file.

### G3b — the full-suite run never prints its summary line

`pytest -q` over the whole suite exits 1 with the last line of output being a `FAILED`
row; the `N failed, M passed …` stats line is missing. Per-file runs are fine. Counts had
to be recovered with `--junitxml`. Suspect something reaching `os._exit` at teardown —
`ok/util/process.py:72 start_exit_watchdog` uses `hard_exit = force_exit or os._exit`.
Track it down, or `LINUX.md` should tell readers to use `--junitxml`.

## G4 — the Linux lockfile pins a mutable branch

`requirements-linux.txt:29`:

```
ok-script[ocr,qt] @ git+https://github.com/RarestStatue/ok-script-linux@linux-port ; sys_platform == "linux"
```

A lockfile whose top dependency is a moving branch ref is not a lock. Pin the commit:
`…ok-script-linux@e735836fe950a016522cf08aad107df38991ab8d`. Keeping `@linux-port` in
`pyproject.toml` is fine — that is the range spec — but the generated lock must be
immutable, and the regeneration recipe in the file header should say so.

## G5 — nothing runs the Linux gates

`LINUX.md` says the three drift tools "should be run after every rebase" and that "each one
has caught a real regression", but no automation runs them. `.github/workflows/test.yml`
here is `runs-on: windows-latest` only, and the fork carries just `publish.yml`.

Add an `ubuntu-latest` job (fork side is the better home) that runs, in order:

```sh
python tools/scan_module_level_win32.py --check
python tools/check_linux_imports.py
python -m pytest tests          # see G3 re: per-file
```

`tools/gen_win32con.py --check` is the odd one out — see G10.

## G6 — the fork inherits upstream's PyPI publish workflow

`.github/workflows/publish.yml` in the fork still triggers on `push: tags: v*`, builds, and
uploads to PyPI. The fork's `pyproject.toml:11` keeps `name = "ok-script"` (deliberately,
so `ok-script>=2.0.5` resolves). Tagging the fork `vX.Y.Z` therefore attempts to publish a
fork build under the upstream project name. Delete the workflow, or gate it on
`if: github.repository == 'ok-oldking/ok-script'`.

## G7 — file descriptor `0` is a falsy mutex handle

The POSIX handle from `ok/compat/single_instance.py:acquire` is an `int` fd, but
`ok/util/process.py:291` (`check_mutex`) and `:213` (`_release_mutex`) both test it with
`if _mutex_handle:`. If the app is launched with fd 0 closed, `os.open` returns 0, the
re-entrancy short-circuit misfires and the lock is never released at exit. Use
`if _mutex_handle is not None:` in both places. (The Windows branch is unaffected — a
`HANDLE` is never 0.)

## G8 — `acquire()` conflates "held" with "could not open"

`single_instance.acquire` returns `None` both when another process holds the flock and when
`os.open` fails (read-only `XDG_RUNTIME_DIR`, exhausted fds, SELinux denial). In the second
case `_check_mutex_posix` waits 5s, then calls `_terminate_previous_instances`, which
scans for and `kill()`s any process matching the app signature — hunting a previous
instance that does not exist. Return a sentinel (or raise) for the open failure and let
`_check_mutex_posix` bail out instead of escalating to a kill.

## G9 — the win32con coverage scan does not see `tests/`

`tools/gen_win32con.py:117` and `tests/test_linux_win32_compat.py:60` both walk only
`REPO/'ok'`. `tests/test_notifications.py` references `win32con.VK_ESCAPE`, `VK_END`,
`VK_BACK`, `VK_DELETE`, `VK_CONTROL` and `CF_DIB`. All six happen to be in the generated
94 today, so nothing is broken — but a test that starts using a new constant will fail at
run time with the generator's "regenerate with …" `AttributeError` instead of failing the
`--check` gate. Add `tests/` to both walks.

(Downstream ok-ww is clean: it uses `win32api.{Get,Set}CursorPos` and `winreg`, no
`win32con`.)

## G10 — `gen_win32con.py --check` needs the network

It downloads the pywin32 311 `win_amd64` wheel from PyPI on every invocation, including
`--check`. That makes the cheapest-looking of the three gates the one that fails in an
offline or rate-limited CI runner. Either cache the extracted `win32con.py` (with a hash)
in the repo, or mark the gate as network-dependent in `LINUX.md` and keep it out of the
required CI set from G5.

## G11 — three Phase-1 `ok/device/` edits were not made, and the deferral is unrecorded

PORT.md §4/1b states "**The only edits this phase needs in `ok/device/`**" and lists:

1. `capture_methods/__init__.py` — import `X11Window`/`X11CaptureMethod`, rebind `HwndWindow`
2. `interaction_methods/__init__.py` — import `WinePostMessageInteraction`
3. `capture_methods/update.py` — register the new capture methods

None exist in the fork. That is the right call — all three import modules Phases 2-4 have
not written yet — but neither §9 nor `LINUX.md` records it, so the next reader will diff
the plan against the tree and think Phase 1 is incomplete. Move these three bullets into
Phase 2/3 in PORT.md and note the move in §9.

## G12 — the `requirements.txt` divergence is only in a commit message

PORT.md §4/1a instructs: regenerate this repo's `requirements.txt` with `pip-compile` and
"check the regenerated file no longer lists those four". The implementation deliberately
did the opposite — kept `requirements.txt` as the Windows lock (CI is windows-latest) and
added `requirements-linux.txt` alongside. The reasoning is in `9effbc3`'s commit message
but not in PORT.md §9, which is where the other five corrections live. Add it as C7.

## G13 — the Phase-1 exit criterion's second half was not reached

PORT.md §4/1c: "Follow the script with a headless `OK(config)` construction
(`QT_QPA_PLATFORM=offscreen`) up to the point where `do_start` selects a capture method —
that is the step that actually proves the GUI leaves are covered."

Startup stops earlier, at `get_monitors_bounds()` (Phase 2 work), so `do_start` is never
reached and that proof does not exist yet. The fork's Qt test files (`test_task_ui`,
`test_template_tab`, `test_start_tab_overlay`, `test_core_ui_services`) cover much of the
same ground incidentally. State explicitly that this criterion carries into Phase 2's exit
gate rather than leaving it silently unmet.

## G14 — the root `conftest.py` is dead code with a stale rationale

`conftest.py` says "A root conftest is the earliest hook that is guaranteed to run first",
but its own `from ok.compat.win32_stub import install` executes `ok/__init__.py` first,
which already calls `install()` (`ok/__init__.py:14-19`). By the time `conftest`'s
`install()` runs, `_installed` is already `True`. Harmless, but either delete it or rewrite
the docstring to say it is belt-and-braces, so nobody later "fixes" `ok/__init__.py`
believing conftest covers pytest.

## G15 — `install()` monkeypatches the global `ctypes` module [note, no action needed yet]

`ctypes.windll`, `.oledll`, `.WinDLL`, `.OleDLL`, `.HRESULT` and `.WINFUNCTYPE` are set
process-wide, so any third-party library that platform-sniffs with
`hasattr(ctypes, 'windll')` will conclude it is on Windows. Audited the full installed
dependency set (`psutil`, `pynput`, `mouse`, `pyappify`, `darkdetect`, `pywebview`,
`setuptools`, PySide6 stack): **none** do this — they all branch on `platform.system()` or
`sys.platform`. Record the audit as an assumption in the `win32_stub` docstring so a future
dependency addition gets re-checked.

## G16 — `cv2` is an undeclared ok-script dependency, and it breaks the documented repro

`ok/util/color.py:1` and ~10 other modules (`DeviceManager`, `FeatureSet`,
`core/screenshot.py`, `bitblt_utils` …) `import cv2` at module scope, but `opencv-python`
appears nowhere in the fork's `pyproject.toml`, and `onnxocr-ppocrv5` does not pull it in
(`Requires: pillow, pyclipper, shapely`). It only arrives because ok-ww declares it.

Consequence for this port: following `LINUX.md`'s own instructions — "`pytest tests` with
the `qt`, `web`, `adb` and `ocr` extras installed" — gives 20 collection errors, and
`tools/check_linux_imports.py` reports **35/70 failed**, all `No module named 'cv2'`. That
reads exactly like a port regression and cost time in this review.

Pre-existing upstream metadata bug, not something Phase 1 introduced. Fix it in the fork
(`"opencv-python" ` in the `default` extra, which is where `numpy`/`Pillow` already live) —
it is a one-line, Linux-neutral change — and add `opencv-python` to `LINUX.md`'s repro
command either way.

---

## Suggested order

1. **G1** — one-word correctness fix plus a test that would have caught it.
2. **G2**, **G16** — the two gate/repro defects that let a red build look green.
3. **G4**, **G5**, **G6** — supply-chain and automation hygiene before Phase 2 lands.
4. **G3** / **G3b** — make the test baseline mean something.
5. **G7**, **G8**, **G9**, **G10** — small hardening.
6. **G11**, **G12**, **G13**, **G14**, **G15** — documentation truthfulness; cheap, and
   Phase 2 starts by reading these files.

None of these block Phase 2. G1 and G2 should land before it.
