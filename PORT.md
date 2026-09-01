# Porting ok-ww to Linux — Implementation Plan

**Audience:** the engineer/model implementing this port.
**Goal:** run ok-ww natively on Linux (Fedora, NixOS, and other distros) against Wuthering Waves running under Proton/Wine, preserving the original program's function — including **background operation** (bot plays while you use the desktop).

Every load-bearing claim below is tagged **[VERIFIED]** (empirically proven in this repo/machine, evidence included) or **[GATE]** (not yet proven — a verification step is specified before you build on it). Do not treat a GATE as settled. Do not skip a gate.

---

## 1. Executive summary

ok-ww itself is essentially portable already. The Windows coupling lives almost entirely in its dependency `ok-script`, and that library is architecturally pluggable — it has abstract `BaseCaptureMethod` / `BaseInteraction` classes with multiple existing backends (BitBlt, WGC, DXGI, ADB, browser, NemuIPC). **The port adds one backend pair; it is not a rewrite.**

The one genuinely hard problem — background input into a Wine-hosted game — is solved by a **hybrid architecture**:

- **Capture runs natively on Linux** (X11/Xwayland per-window grab). Keeps OpenCV + ONNX/OpenVINO OCR on native Linux, full speed.
- **Input runs inside the game's Wine prefix** via a tiny `PostMessage` shim. This preserves `PostMessage` semantics — delivery to an unfocused HWND — which is exactly what upstream ok-script relies on for background play.

Two candidate input mechanisms were tested; results decided the architecture:

| Mechanism | Reaches Wine? | Works unfocused? | Verdict |
|---|---|---|---|
| X11 `XSendEvent` (xdotool) from Linux | ✅ yes | ❌ no — focus-bound | fallback only |
| `PostMessage` from inside the prefix | ✅ yes | ✅ **yes** | **chosen** |

**Deployment target: the game runs under Steam + Proton** (appid `3513350`, currently dwproton-11.0-12). The shim is delivered into the running game's prefix with Proton's `run` verb — verified to share a wineserver with an already-running process and to deliver `PostMessage` across that boundary **[V10]**. ok-ww attaches to a game the user launched through Steam; it never launches the game itself.

**Status: two open gates, in this order.**

1. **[GATE-1b]** — does a shim launched *outside* the SteamLinuxRuntime container join the wineserver of a game Steam launched *inside* it? **[V10]** did **not** test this: it ran both processes outside the container. The toolmanifest declares `require_tool_appid 4183110` **[V9]**, so the real game runs under pressure-vessel. §4b.
2. **[GATE-2]** — does Wuthering Waves' own Unreal input layer honour `PostMessage` under Wine? §5.

Everything else is downstream of those two. Do not restate GATE-2 as "the only remaining question"; GATE-1b is upstream of it and is answered by the same spike session.

**Revision note (2026-09-01 audit, second pass).** The plan was re-verified against the actual ok-script 2.0.5 tree and against fresh measurements on this machine. The architecture survives unchanged. Load-bearing corrections, all applied in place:

- **[V2]** `import ok` does *not* fail — lazy imports. The old Phase-1 exit criterion was a false green.
- **[V13]** python-xlib has no MIT-SHM; the pixel path must use `ctypes`.
- **[V14]** capture is far faster than assumed — GATE-3 resolved.
- **[V15]** `HwndWindow.visible` means *foreground*, not *mapped* — the old Phase-2 definition silently disabled background mouse-pinning.
- **[V16]** rewritten from an AST scan. The old file list was both incomplete and partly wrong, the old module count (36) was inflated, and the `win32_stub` sketch was missing two symbols that make it fail outright.
- **[V17]** `find_hwnd`/`get_window_bounds` are required contracts — and the old text's "on Linux `real_*` are all 0" was a functional bug (**[V18]**).
- **[V18]** `find_hwnd`'s `real_width`/`real_height` are the window dimensions, never 0.
- **[V19]** the SteamLinuxRuntime container boundary is untested — new **[GATE-1b]**.
- **[V20]** `PynputInteraction` already works on Linux; the planned `X11SendEventInteraction` was redundant and has been removed.

**Revision note (2026-09-01 audit, third pass — empirical).** The second-pass claims were re-checked against the ok-script 2.0.5 tree *and executed* in a Linux venv (python3.12, numpy/opencv/psutil/python-xlib installed, no PySide6). The architecture again survives unchanged, and Phase 1 got **much smaller**. Load-bearing corrections, all applied in place:

- **[V21]** The **`win32_stub` as previously written does not work.** Four modules *call* a DLL loader at module level, and `ok/rotypes` uses the COM-vtable form of `WINFUNCTYPE` that `CFUNCTYPE` cannot provide. `ok/rotypes` and `ok/capture/windows` must be *excluded*, not stubbed.
- **[V22]** **Phase 1b's aggregator surgery is unnecessary.** Measured: with the stub plus a Linux `ok/util/window.py`, every module on the device path imports and **all 71 `_LAZY_IMPORTS` names resolve** with **zero** `_WINDOWS` guards. The old Phase 1b also contradicted the old Phase 1 exit criterion and would have broken `DeviceManager` outright.
- **[V23]** The **[V16] membership was wrong in both directions** (the count 27 was right by coincidence), and the AST scanner that produced it is buggy — it prints 30 on this tree.
- **[V24]** `ok/util/window.py`'s export contract is **11 names, not 7**; two of the four missing ones are on the core path.
- **[V25]** `win32con` needs **94** constants, not "~60", and the old list omitted the entire **`VK_*` family** that `keys.py` depends on.
- **[V26]** Several line references were stale, `find_hwnd`'s `hwnds` return is `[biggest]` rather than `[]`, and four ok-ww repo files (`requirements.txt`, `pyappify.yml`, `deploy.txt`, `setup.py`) were never mentioned.

---

## 2. Verified findings (evidence)

These were established by direct experiment on the target machine. They are the foundation of the plan; you can rely on them without re-testing (though re-running is cheap).

### V1 — ok-ww's own Windows coupling is 3 files [VERIFIED]

130 Python files (89 under `src/`), **21,972 LOC** (re-counted 2026-09-01; earlier drafts said "~16.3k", which was wrong). Win32 usage — re-verified by `grep -rn "win32\|winreg\|pydirectinput\|pycaw\|ctypes" --include=*.py .`, which returns **exactly** these four files plus `config.py:276`'s `ok-ww-win32.zip` update URL:

| File | Usage |
|---|---|
| `config.py:15-80` | `winreg` — locate game install |
| `src/combat/CombatCheck.py:4,223-230` | `win32api.GetCursorPos` / `SetCursorPos` |
| `src/task/MouseResetTask.py:3,38-52` | same |
| `tests/TestMouseResetTask.py:56-57` | `patch('src.task.MouseResetTask.win32api')` — **re-audit: a 4th site** |

`src/char`, `src/combat`, `src/scene`, `src/task`, `src/gui` are otherwise pure OpenCV/NumPy/PySide6 — **portable unchanged**.

The test file matters: Phase 5c removes `win32api` from `MouseResetTask`, which breaks `test_callback_continues_while_enabled`. Update the patch target to the interaction backend in the same commit.

### V2 — ok-script is the real blocker, but structurally shallow [VERIFIED, **corrected 2026-09-01**]

ok-script 2.0.5: 255 Python files (verified: `find ok -name '*.py' | wc -l`). **27** of them reference a Windows-only symbol *at module level and outside a platform guard* — see **[V16]** for the exact, corrected list. (Earlier drafts said 29, then 36, then a 27 whose membership was wrong in both directions; all were produced by tools that either conflated module-level with in-function imports, or descended into upstream's own `if sys.platform == 'win32':` blocks. In-function `ctypes.windll` use is harmless on Linux until called, and so is guarded module-level use.)

**Important — being on that list does not mean the module needs work [V22].** Most of them are made importable by the `win32_stub` alone. The empirically determined minimum is much smaller; see Phase 1.

The aggregator packages import every backend eagerly:

- `ok/device/capture_methods/__init__.py` — imports `bitblt`, `bitblt_utils`, `windows_graphics`, `desktop_duplication`, `hwnd_window`, `types`, `browser`, `update`
- `ok/device/interaction_methods/__init__.py` — imports `post_message`, `pydirect`, `genshin`, `foreground_post_message`, `keys`

All of those carry **module-level** `import win32api/win32con/win32gui/pydirectinput`. Fix is a compatibility shim, not rearchitecting — and **not** import guards either **[V22]**.

**Correction — the old claim "`import ok` dies on Linux at import time" is FALSE for 2.0.5.** `ok/__init__.py` uses PEP-562 lazy attribute imports: a `_LAZY_IMPORTS` name→module map (`ok/__init__.py:94-166`, **71 entries**) plus a module-level `__getattr__` (`:183-184`), with the eager Win32-tainted imports confined to an `if TYPE_CHECKING:` block (`:20`). Measured (not statically inferred) on Linux with **no stub installed** — `import ok` succeeds and pulls in exactly nine `ok.*` entries:

```
ok  ok.core  ok.core.events  ok.core.ui_config  ok.util  ok.util.file
ok.util.gpu_driver_settings  ok.util.handler  ok.util.logger
```

(An earlier draft said "5 modules" and omitted `ok.core.events` and `ok.util.gpu_driver_settings`.) **None** of them import Win32 at module level.

Consequence for the work plan: **the old Phase-1 exit criterion (`python -c "import ok; from ok import OK"`) is a false green.** It would pass on a completely unported tree. The real explosion happens later, when `OK.start()` resolves the lazy names (`MainWindow`, `DeviceManager`, `check_mutex`, `windows_graphics_available`, …). See the replacement exit criterion in Phase 1.

### V3 — dependency metadata blocks installation outright [VERIFIED]

From the wheel's `METADATA`, with **no platform markers**:

```
Requires-Dist: pywin32!=312,>=306
Requires-Dist: pydirectinput==1.0.4
Requires-Dist: pycaw==20240210
```

Plus `ok-d3dshot` (DXGI, Windows-only) in the `default` extra. `pip install ok-script` fails to resolve on Linux. **Requires a fork.**

### V4 — Wine accepts synthetic X11 events [VERIFIED]

Wine `+key` debug channel, `xdotool key --window` with focus elsewhere:

```
X11DRV_KeyEvent type 2, window 5600001, state 0x0000, keycode 38
X11DRV_KeyEvent KeyPress : keysym=61 (a), # of chars=1 / "a"
X11DRV_KeyEvent keycode 38 converted to vkey 0x41 scan 001e
X11DRV_send_keyboard_input hwnd 0x1009e vkey=0041 scan=001e flags=0000
```

Wine's `x11drv` does **not** discard `send_event` records. The full path X keysym → Win32 vkey → message queue is live.

### V5 — but XSendEvent is focus-bound [VERIFIED]

| Condition | Text landed? |
|---|---|
| `xdotool type --window`, focus elsewhere | ❌ no |
| `xdotool windowfocus` + `type --window` | ✅ yes |

Events enter Wine's **hardware input path** (`X11DRV_send_keyboard_input` — `SendInput` semantics, which respect focus), not `PostMessage` semantics. Note `windowfocus` grants keyboard focus *without raising*, so the window may stay visually behind others — but it owns the keyboard, so the user cannot type elsewhere. **Insufficient for true background operation.**

### V6 — PostMessage from inside the prefix works unfocused [VERIFIED] ← the decisive result

A ~40-line C shim (mingw-cross-compiled, run under `wine`) replicating `post_message.py`'s protocol, targeting a window that did **not** hold X input focus:

```c
HWND top = FindWindowW(NULL, L"Untitled - Notepad");
HWND edit = FindWindowExW(top, NULL, L"Edit", NULL);
PostMessageW(top, WM_ACTIVATE, WA_ACTIVE, 0);
PostMessageW(edit, WM_CHAR, (WPARAM)*p, 0);              /* input_text path  */
PostMessageW(edit, WM_KEYDOWN, vk, (scan<<16)|1);        /* send_key   path  */
PostMessageW(edit, WM_KEYUP,   vk, down|(1<<30)|(1<<31));
```

Result: `POSTMSG_CHAR_OK keydn` rendered in the app, X input focus never on it. Both the `WM_CHAR` and the `WM_KEYDOWN`/`WM_KEYUP`-with-scan-code paths delivered. The lowercase `keydn` confirms `TranslateMessage` applied real shift-state semantics — genuine Win32 behavior, not an accident.

### V7 — X11 per-window capture works on Xwayland [VERIFIED]

| Condition | Result |
|---|---|
| `XGetImage` on a Wine/Xwayland window | ✅ correct content |
| Occluded but mapped | ✅ byte-identical to unoccluded (diff = 0) |
| **Minimized (`WM_STATE` = Iconic)** | ❌ capture fails |
| Full-root capture (`import -window root`) | ❌ unavailable under rootless Xwayland |

Xwayland backs each toplevel with its own buffer, so occlusion is a non-issue — but **never minimize the game**, and don't plan on whole-screen grabs.

### V8 — X window ↔ Linux PID correlation works [VERIFIED]

Wine sets `_NET_WM_PID` on its X windows; `xdotool getwindowpid <win>` returned the correct `notepad.exe` Linux PID. This is the mechanism the Linux capture side uses to find the game's X window. No guessing required.

### V9 — target environment [VERIFIED]

```
Fedora 44, kernel 7.1.12-200.fc44.x86_64, KDE, XDG_SESSION_TYPE=wayland
Xwayland :0 running rootless        → X11 toolchain applies to Proton games
/dev/uinput  ACL user:max:rw-       → uinput available without root (fallback path)
python3.12 + python3.14 present     → use 3.12; 3.14 conflicts with pinned wheels
x86_64-w64-mingw32-gcc present      → can build the shim
wine-11.0 (Staging)
xdotool, wmctrl, ImageMagick present
Wuthering Waves installed: appid 3513350, StateFlags 4, 89 GB
  prefix: ~/.local/share/Steam/steamapps/compatdata/3513350/pfx
  exe:    <lib>/steamapps/common/Wuthering Waves/Client/Binaries/Win64/Client-Win64-Shipping.exe
  Proton: dwproton-11.0-12
          ~/.local/share/Steam/compatibilitytools.d/DW-Proton Latest/   ← note the space
          toolmanifest: require_tool_appid 4183110 (SteamLinuxRuntime_4), use_sessions "1"
protontricks present at /usr/bin/protontricks
```

### V10 — a second `proton run` joins the game's wineserver, and PostMessage crosses [VERIFIED] ← resolves the old GATE-1

Tested against a **scratch** Proton prefix (the game's prefix was never touched), using the user's actual Proton build (dwproton-11.0-12):

1. `proton run C:\windows\system32\notepad.exe` — process A, window created.
2. Focus moved to a different window (verified: `getwindowfocus` ≠ notepad).
3. `proton run C:\shim.exe` — process B, a **separate** `proton run` invocation.
4. Result: the injected text appeared in process A's unfocused window.

Run twice; the text appears twice (`POSTMSG_CHAR_OK keydnPOSTMSG_CHAR_OK keydn`), confirming both invocations delivered. So separate `proton run` calls **share one wineserver session** keyed by `STEAM_COMPAT_DATA_PATH`, and `PostMessage` works across them. This holds with `use_sessions "1"` and ntsync active.

Also verified: `proton run` worked **directly on this host without the SteamLinuxRuntime_4 container entry point**, despite `require_tool_appid`. Keep the SLR entry point as a documented fallback for distros whose host libs are too old (likely relevant on NixOS).

Exact working invocation:

```sh
STEAM_COMPAT_DATA_PATH=~/.local/share/Steam/steamapps/compatdata/3513350 \
STEAM_COMPAT_CLIENT_INSTALL_PATH=~/.local/share/Steam \
"$PROTON_DIR/proton" run 'C:\okww-input-shim.exe'
```

### V11 — `WM_CLASS` is useless under Proton; `_NET_WM_PID` is mandatory [VERIFIED]

Every Proton window reports the same class:

```
WM_CLASS(STRING) = "steam_proton", "steam_proton"
_NET_WM_PID(CARDINAL) = 87814          # correct Linux PID of notepad.exe
```

`xdotool search --class notepad` found **nothing**, while the window plainly existed. The game's Win32 class (`UnrealWindow`, from `config.py`) is **not visible from the X11 side at all** — it exists only inside Wine. Consequence: X11-side window discovery **must** go through `_NET_WM_PID` → `/proc/<pid>/cmdline`. Class/title matching is not a usable fallback here; treat it as a last-resort tiebreak only.

### V12 — the shim's stdout is swallowed under `proton run` [VERIFIED]

The shim's `printf` output appeared when run under plain `wine`, but **not** under `proton run` (exit 0, injection confirmed working, no stdout). The shim must therefore report status over its socket or to a file — **never** rely on stdout/stderr for liveness, errors, or the port/token handshake.

### V13 — python-xlib cannot do MIT-SHM [VERIFIED] ← contradicts the old Phase 3

`python-xlib` 0.33 ships these extensions and no others:

```
composite  damage  dpms  ge  nvcontrol  randr  record  res
screensaver  security  shape  xfixes  xinerama  xinput  xtest
```

`from Xlib.ext import shm` → `ImportError: cannot import name 'shm' from 'Xlib.ext'`. There is **no MIT-SHM binding in python-xlib at any version.** The old plan simultaneously required `XShmGetImage` (Phase 3) and "talk to X11 through python-xlib in the shipped code" (Phase 6). Those are incompatible.

**Resolution:** the capture path binds `libX11.so.6` + `libXext.so.6` through `ctypes` directly. This is ~120 lines: an `XImage` struct (note its trailing `funcs` struct of 6 pointers — `XDestroyImage` is a C *macro*, so you must call `img.contents.f.destroy_image` through a `CFUNCTYPE`), an `XShmSegmentInfo` struct, and `shmget`/`shmat`/`shmctl` from `libc`. python-xlib is still the right tool for the *window* layer (Phase 2: tree walk, properties, geometry, RandR, and the `xtest`/`composite`/`damage` extensions) — keep it there.

Useful side effects of that extension list: `randr` gives `get_monitors_bounds` (Phase 2), `damage` gives an optional skip-unchanged-frames optimization, and `xtest` gives a strictly better fallback backend than `XSendEvent` (see §4d).

### V14 — capture throughput measured; GATE-3 effectively resolved [VERIFIED]

Measured on this machine (Fedora 44 / KDE Wayland / rootless Xwayland :0), against a real mapped 1920×1080 Xwayland toplevel, 120 iterations each:

| Path | Rate | Per frame |
|---|---|---|
| `XGetImage` | 73.7 fps | 13.57 ms |
| `XShmGetImage` | **805.3 fps** | **1.24 ms** |

The image format came back exactly as the plan assumed: `depth=24 bits_per_pixel=32 bytes_per_line=7680 byte_order=0 (LSBFirst) masks R=ff0000 G=ff00 B=ff` — i.e. **BGRA in memory**. `bytes_per_line` is not necessarily `width*4`; stride the buffer, don't assume.

Two corrections follow:

1. **Plain `XGetImage` is not disqualifying.** The old text said it "will not sustain the capture rate ok-ww needs" — at 73 fps it plainly does. MIT-SHM is still worth having (11× headroom, and it is what makes the XComposite path cheap), but it is an optimization, not a gate. Ship the ctypes `XGetImage` path first if that unblocks you.
2. **The expensive step is the BGRA→BGR conversion, not the grab.** Measured at 1920×1080, 200 iterations:

   | Conversion | Per frame |
   |---|---|
   | `arr[:, :, :3]` (a *view*, no copy) | 0.00 ms |
   | `arr[:, :, :3].copy()` | 10.10 ms |
   | `np.ascontiguousarray(arr[:, :, :3])` | 9.69 ms |
   | `arr.copy()` (full BGRA) | 0.99 ms |
   | **`cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)`** | **0.15 ms** |

   A naive strided numpy copy costs **67×** what `cv2.cvtColor` costs and would dominate the frame budget. See the Phase 3 note on why a copy of *some* kind is mandatory.

### V15 — `HwndWindow.visible` means FOREGROUND, not mapped [VERIFIED] ← a functional bug in the old Phase 2

`hwnd_window.py:285` sets `visible = self.is_foreground()`, and `is_foreground()` (`hwnd_window.py:352-358`) tests `is_foreground_window(self.hwnd)` then each entry of `self.hwnds`. `is_foreground_window` itself (`ok/util/window.py:121-122`) is `IsWindowVisible(hwnd) and GetForegroundWindow() == hwnd`. So `visible` is a *focus* predicate, not a mapped/iconic predicate.

The old Phase 2 defined it as "`WM_STATE` != Iconic **and** mapped". Under that definition `visible` is **True for the entire duration of background play** — which inverts two consumers:

- `src/task/MouseResetTask.py:39` guards on `... and not self.hwnd.visible and ...`. It pins the physical cursor **only when the game is not in the foreground** — i.e. exactly during background play, which is this port's whole purpose. With a mapped-based `visible`, background mouse-pinning silently never runs.
- `hwnd_window.py:364` — `set_mute_state(self.hwnd, 0 if self.visible else 1)`, the mute-while-in-background feature.
- `BaseWindowsCaptureMethod.clickable()` (`base.py:83-84`) returns `self._hwnd_window is not None and self._hwnd_window.visible`.

**Correct Linux mapping:** `visible` = "this window currently holds input focus" — compare the root's `_NET_ACTIVE_WINDOW` against `hwnd` (and fall back to `XGetInputFocus` walking up to the toplevel). Iconic/minimized belongs in `pos_valid` and in the capture layer's error, **not** in `visible`.

### V16 — the exact module-level offender list, from an AST scan [VERIFIED, **membership corrected 2026-09-01 third pass — see [V23]**]

Four symbols are absent from Linux CPython. Verified on python3.12.14:

```
python3.12 -c "from ctypes import windll"
# ImportError: cannot import name 'windll' from 'ctypes' (/usr/lib64/python3.12/ctypes/__init__.py)
python3.12 -c "import winreg"
# ModuleNotFoundError: No module named 'winreg'
python3.12 -c "import ctypes; print(hasattr(ctypes,'HRESULT'), hasattr(ctypes,'WINFUNCTYPE'))"
# False False
```

`from ctypes import wintypes` is fine — it imports cleanly on Linux, and `ctypes.wintypes.LONG` exists, which is why `ok/rotypes/types.py` (`HRESULT = LONG`) is **not** an offender.

Earlier drafts of this section were produced first by grep and then by a buggy AST scanner, and were wrong in both directions. The list below is from an AST walk of every module's top-level body that **skips function/method/class bodies** (harmless on Linux until called), **skips `if` statements whose test mentions `sys.platform` / `os.name` / `platform.system`** (upstream's own guards — those branches never execute on Linux), and **skips `try:` blocks**. The corrected scanner is in the appendix.

**Group A — module-level `import win32*` / `pydirectinput` / `winreg`, outside any platform guard (22 modules):**

```
ok/alas/emulator_windows.py                          winreg
ok/device/capture_methods/bitblt_utils.py            win32con win32gui win32ui
ok/device/capture_methods/browser.py                 win32gui          ← see the note below
ok/device/capture_methods/desktop_duplication.py     win32api win32con
ok/device/capture_methods/hwnd_window.py             win32api win32con win32gui win32process
ok/device/capture_methods/types.py                   win32gui
ok/device/capture_methods/windows_graphics.py        win32gui
ok/device/interaction_methods/foreground_post_message.py  pydirectinput
ok/device/interaction_methods/genshin.py             win32api win32con win32gui  + ctypes.windll
ok/device/interaction_methods/keys.py                win32con          ← see [V25]
ok/device/interaction_methods/post_message.py        win32api win32con win32gui
ok/device/interaction_methods/pydirect.py            pydirectinput
ok/notification/messenger_images.py                  win32api win32con win32gui win32process
ok/notification/windows_messenger.py                 win32api win32clipboard win32con win32gui win32process win32ui
ok/rotypes/Windows/Foundation/__init__.py            ctypes.HRESULT ctypes.windll   ← CALLS windll.LoadLibrary at import
ok/rotypes/delegate.py                               ctypes.HRESULT ctypes.WINFUNCTYPE
ok/ui/qt/debug/DebugTab.py                           ctypes.windll     (debug hotkey)
ok/ui/qt/debug/OverlayWidget.py                      win32api
ok/ui/qt/start/StartCard.py                          ctypes.windll     (global start/stop hotkey)
ok/ui/qt/tasks/RecordScript.py                       win32gui
ok/util/print_hwnd.py                                win32gui win32process
ok/util/window.py                                    win32api win32con win32gui win32process
                                                     + ctypes.WinDLL   ← CALLS ctypes.WinDLL('user32') at line 18
```

**Group B — module-level *attribute* access to a missing `ctypes` symbol (5 more modules):**

```
ok/capture/windows/d3d11.py          ctypes.oledll.d3d11.D3D11CreateDevice          (line 71)
ok/rotypes/Windows/Graphics/DirectX/Direct3D11/__init__.py
                                     ctypes.oledll.d3d11.CreateDirect3D11Device...  (line 34)
ok/rotypes/inspectable.py            windll.ole32.CoTaskMemFree      (via `from ctypes import *`)
ok/rotypes/roapi.py                  windll.LoadLibrary('combase.dll')   ← CALLS at import (line 7)
ok/rotypes/winstring.py              ctypes.windll.LoadLibrary('combase.dll') ← CALLS at import (line 6)
```

27 modules total. `StartCard.py` and `DebugTab.py` are not cosmetic — they implement the **global start/stop and debug hotkeys** via `windll.user32.RegisterHotKey` + a `PeekMessageW` pump (`StartCard.py:124,137`; `DebugTab.py:117,135,137`); see §6.

**Two modules that earlier drafts listed here are NOT offenders — upstream already guards them [V23]. Do not touch them, and do not budget work for them:**

```
ok/ui/overlay/win32_gdi.py            all Win32 code sits inside `if os.name == "nt":` (line 22)
                                      and `if os.name != "nt":` fallbacks (lines 209, 221, 1007)
ok/ui/qt/util/windows_thumbnail.py    all Win32 code sits inside `if sys.platform == 'win32':` (line 14);
                                      `WindowsThumbnailReader.open()` already returns False on
                                      non-win32 at line 125-126 — exactly the fallback §6 wants
```

Verified by executing `import ok.ui.overlay` on Linux with **no stub installed**: it succeeds. So `ok/ui/overlay/__init__.py` needs **no** guard, and the §6 "import-time hazard" claim about these two was wrong.

`ok/rotypes/types.py` is likewise **not** an offender: it does `from ctypes.wintypes import *` then `HRESULT = LONG`, both of which work on Linux unmodified. (The old scanner flagged it by mistaking the assignment *target* `HRESULT` for a read of `ctypes.HRESULT`.)

**Group C — modules that import cleanly themselves but drag Group A/B in:**

```
ok/device/capture.py                 `from ok.device.capture_methods import *` AND `import bitblt` by name
ok/device/interaction.py             `from ok.device.interaction_methods import *`
ok/device/capture_methods/update.py  imports bitblt/desktop_duplication/windows_graphics + ok.util.window
ok/ui/overlay/__init__.py            `from ok.ui.overlay.win32_gdi import Win32GdiOverlay`  ← harmless, see above
```

`capture.py` and `interaction.py` are the two that matter most: `DeviceManager.py:9-12` imports from **those**, not from the `*_methods` packages, and `_LAZY_IMPORTS` routes every capture/interaction name through them.

**Four of the 27 CALL a Windows DLL loader at module level.** This is the detail that breaks the naive stub — see **[V21]**:

```
ok/util/window.py:18                       user32 = ctypes.WinDLL('user32', use_last_error=True)
ok/rotypes/roapi.py:7                      combase = windll.LoadLibrary('combase.dll')
ok/rotypes/winstring.py:6                  combase = ctypes.windll.LoadLibrary("combase.dll")
ok/rotypes/Windows/Foundation/__init__.py:9  _kernel32 = windll.LoadLibrary('kernel32.dll')
```

**Entries that earlier drafts listed and that are NOT offenders** (their `ctypes.windll` use is inside functions; leave them alone, the stub covers them if they are ever called). All verified importable on Linux under the stub:

```
ok/util/Analytics.py   ok/util/windows_schedule.py   ok/util/process.py   ok/util/file.py
ok/ui/web/app.py       ok/ui/web/server.py           ok/alas/platform_windows.py
ok/ui/qt/MainWindow.py ok/third_party/paperclip.py   ok/util/explorer.py
```

### V17 — `find_hwnd` and `get_window_bounds` are required contracts the plan never mentioned [VERIFIED]

`ok/util/window.py` is win32-only at module level and supplies functions that the whole device layer is built on:

- `find_hwnd(title, exe_names, frame_width, frame_height, player_id=-1, class_name=None, selected_hwnd=0, top_hwnd_class=None, last_hwnd=0)` → 8-tuple `(name, hwnd, full_path, real_x_offset, real_y_offset, real_width, real_height, hwnds)`. Called from `DeviceManager.py:257` (builds the `windows` entry in `device_dict` — **without it no PC device appears and `do_start` never takes the windows branch**), `DeviceManager.py:388`, and `hwnd_window.py:247` (every poll).
- `get_window_bounds(hwnd)` → 7-tuple `(x, y, window_width, window_height, width, height, scaling)`. Upstream returns `(0, 0, 0, 0, 0, 0, 1)` on any exception — keep that fallback shape.
- `is_foreground_window`, `show_title_bar`, `resize_window`, `find_all_visible_windows`, `windows_graphics_available`, **and four more that earlier drafts missed — see [V24] for the complete 11-name contract.**

Note `find_hwnd`'s 8th element, `hwnds`: on a successful match upstream returns **`[biggest]`** — a one-element list of 9-tuples `(hwnd, full_path, width, height, x, y, title, class_name, scaling)` — and only returns `[]` on the no-match paths. Phase 2 returns `[]` on Linux instead; that is a deliberate deviation, and it is safe: all four consumers (`hwnd_window.py:220` `capture_target_signature`, `:264` assignment, `:355` `is_foreground`, and `post_message.py:200-215`'s hit-test) handle an empty list correctly. Do not "fix" it back.

Plus, in `hwnd_window.py` itself (**not** in `ok/util/window.py` — do not look for them there): `get_monitors_bounds()` (→ XRandR via python-xlib), `is_window_in_screen_bounds`, `check_pos`, `get_mute_state`, `set_mute_state`.

Phase 2 must supply Linux equivalents of these with byte-identical return shapes, not just an `X11Window` class.

### V18 — `find_hwnd`'s `real_width`/`real_height` are the window size, never 0 [VERIFIED] ← a functional bug in the old Phase 2

`ok/util/window.py:429` initialises them from the matched window, not from zero:

```python
x_offset, y_offset, real_width, real_height = 0, 0, biggest[2], biggest[3]
```

They are only overwritten when a letterboxed child window is found (`enum_child_windows`), which cannot happen on Linux — Wine gives one X toplevel **[V11]**.

The old text said "On Linux `real_*` are all `0`". That is wrong for the last two, and the failure is silent and total:

- `DeviceManager.py:257` unpacks positions 5 and 6 as `width, height` and writes them straight into the PC device dict (`"width"`, `"height"`, `"resolution": f"{width}x{height}"`). Zeros give a `0x0` device.
- `hwnd_window.py:263-266` assigns them to `self.real_width` / `self.real_height`, which feed `get_capture_origin()` and `capture_target_signature` (so change-detection would never fire).

**Correct Linux contract:** `real_x_offset = real_y_offset = 0`; `real_width, real_height = <the window's width, height>`.

### V19 — the SteamLinuxRuntime container boundary is untested [GATE-1b]

`compatibilitytools.d/DW-Proton Latest/toolmanifest.vdf` (read during this audit):

```
"commandline"        "/proton %verb%"
"require_tool_appid" "4183110"
"use_sessions"       "1"
```

`4183110` is `SteamLinuxRuntime_4`, installed at `steamapps/common/SteamLinuxRuntime_4`. When the user launches WW from Steam, Steam runs Proton **inside** that pressure-vessel container — a separate mount namespace.

**[V10] did not test this.** In V10 both process A (the target) and process B (the shim) were launched by bare `proton run` from the host, outside any container. Whether a host-side `proton run` can reach the wineserver of a containerised game — same `/tmp/.wine-1000` socket directory, same prefix device/inode, same `WINEPREFIX` string — is unproven and is a plausible failure point.

This is **[GATE-1b]** and it is upstream of [GATE-2]: both are answered in the same spike session (§4b), but if GATE-1b fails you must switch to the `_v2-entry-point` launch (§4b fallback 1) *before* GATE-2 means anything.

### V20 — `PynputInteraction` already runs on Linux; no `X11SendEvent` backend is needed [VERIFIED]

`ok/device/interaction_methods/pynput.py` has **no** module-level Windows imports (confirmed by the [V16] scan). Its only Windows touch is `is_admin()` from `ok/util/process.py`:

```python
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
```

On Linux that raises inside a bare `except` and returns `False`, so the constructor logs one error line and the backend works. `pynput` on Linux drives **XTEST** natively — exactly the transport §4d was going to hand-write. Its `clickable()` calls `self.hwnd_window.is_foreground()`, which Phase 2 supplies anyway.

Consequence: the foreground-only fallback is a config entry, not a new class. See §4d.
### V21 — the `win32_stub` sketched in earlier drafts FAILS at import [VERIFIED — executed]

Running the exact `_Missing`-based stub from the old Phase 1c on python3.12 against the real tree:

```
FAIL  ok.rotypes.winstring          NotImplementedError: Windows-only symbol called on Linux: ctypes.windll.LoadLibrary
FAIL  ok.rotypes.roapi              NotImplementedError: ... ctypes.windll.LoadLibrary
FAIL  ok.rotypes.Windows.Foundation NotImplementedError: ... ctypes.windll.LoadLibrary
FAIL  ok.capture.windows.d3d11      NotImplementedError: ... ctypes.windll.LoadLibrary
FAIL  ok.util.window                NotImplementedError: ... ctypes.WinDLL
```

Two independent defects:

1. **`_Missing.__call__` raises, and four modules call a loader at import time** (list above). Relaxing `__call__` to return another `_Missing` for loader-shaped names fixes those four, but then exposes defect 2.
2. **`ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE` is not sufficient.** `ok/rotypes/inspectable.py:12` uses the **COM vtable** constructor form, which only Windows ctypes prototypes support:

   ```python
   (0, 'QueryInterface', WINFUNCTYPE(check_hresult, REFGUID, VOIDPP)(0, "QueryInterface")),
   #                                                               ^^^^^^^^^^^^^^^^^^^^^
   # TypeError: function takes exactly 1 argument (2 given)
   ```

   A `CFUNCTYPE` prototype accepts only `(address_or_callable)`. There is no pure-Python way to give `rotypes` a working `WINFUNCTYPE` on Linux.

**Resolution: do not try to make `ok/rotypes` or `ok/capture/windows` importable.** They are only ever imported from *inside functions* — `ok/util/window.py:windows_graphics_available()` and `ok/device/capture_methods/windows_graphics.py:189-196,241` — and on Linux neither function body runs (`WINDOWS_BUILD_NUMBER == -1`, and WGC is not in the Linux `capture_method` list). Keep `ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE` and `ctypes.HRESULT = ctypes.c_long` anyway: `ok/rotypes/delegate.py` is fine with them, and they cost nothing. Just never import `ok.rotypes.*` on Linux, and exclude it from the Phase 1 exit-criterion sweep.

### V22 — the true Phase-1 minimum, measured [VERIFIED — executed] ← replaces the old Phase 1b

Setup: python3.12 venv with `numpy opencv-python-headless psutil Pillow python-xlib pynput typing-extensions requests darkdetect mouse`; ok-script 2.0.5 source on `PYTHONPATH`; the corrected `win32_stub` installed; **no `_WINDOWS` guards added to any aggregator**; `ok/util/window.py` replaced by a stand-in exporting its 11 public names **[V24]**.

Result:

```
OK    ok.device.capture_methods
OK    ok.device.interaction_methods
OK    ok.device.capture
OK    ok.device.interaction
OK    ok.device.DeviceManager
LAZY FAILURES: 1
    ('MainWindow', 'ok.ui.qt.MainWindow', ModuleNotFoundError, "No module named 'pyappify'")
```

All **71** `_LAZY_IMPORTS` entries resolve except `MainWindow`, and that one fails on an *uninstalled dependency* (`pyappify`), not on anything Windows-related. `bitblt`, `post_message`, `genshin`, `pydirect`, `foreground_post_message`, `windows_graphics`, `desktop_duplication`, `browser`, `types`, `keys` and `hwnd_window` all imported unmodified.

Before the `ok/util/window.py` stand-in was in place, **every one of those failed with the same single error** — `ctypes.WinDLL` at `ok/util/window.py:18`. It is the sole choke point.

Two consequences, both of which shrink the plan:

1. **Do not guard the aggregators.** The old Phase 1b's `if _WINDOWS:` blocks in `capture_methods/__init__.py` and `interaction_methods/__init__.py` are unnecessary, are a large diff against a fast-moving upstream (contradicting Phase 0), and are actively harmful: `DeviceManager.py:11-12` imports `PostMessageInteraction, GenshinInteraction, ForegroundPostMessageInteraction, PyDirectInteraction` **at module level**, so guarding them out means `DeviceManager` does not import at all, and 17 `_LAZY_IMPORTS` names stop resolving.
2. The Windows backends being *importable* on Linux is harmless — they are never *selected*, because `config['windows']['capture_method']` and `['interaction']` are overridden in Phase 5b and `update_capture_method` only instantiates what the config names.

### V23 — the AST scanner shipped in the appendix is buggy [VERIFIED]

Run as written against ok-script 2.0.5 it prints **30** modules, not 27, because it (a) walks into upstream's own module-level `if sys.platform == 'win32':` / `if os.name == "nt":` guards and (b) counts `HRESULT = LONG`'s assignment target as a read. The corrected scanner is in the appendix; use that one, and re-run it after every rebase.

### V24 — `ok/util/window.py`'s export contract is 11 names, not 7 [VERIFIED]

Every name imported from that module anywhere in the tree:

| Name | Imported by |
|---|---|
| `find_hwnd` | `hwnd_window.py:13`, `browser.py:11`, `DeviceManager.py:20` |
| `get_window_bounds` | `hwnd_window.py:13`, `DeviceManager.py:238` (in-function) |
| `is_foreground_window` | `hwnd_window.py:13` |
| `show_title_bar` | `hwnd_window.py:13` |
| `resize_window` | `hwnd_window.py:13`, `browser.py:11`, `core/start_controller.py:309` (in-function) |
| `windows_graphics_available` | `update.py:4`, `browser.py:11`, `DeviceManager.py:20`, `ok/__init__.py:92` |
| `find_all_visible_windows` | `DeviceManager.py:238` (in-function) |
| **`find_display`** | **`desktop_duplication.py:5`** — missing from earlier drafts |
| **`ratio_text_to_number`** | **`ok/task/TaskExecutor.py:12`** — missing, and on the core path |
| **`WINDOWS_BUILD_NUMBER`** | **`windows_graphics.py:9`** — missing; a module-level constant, not a function |
| **`WGC_NO_BORDER_MIN_BUILD`** | **`windows_graphics.py:9`** — missing; ditto |

Omitting any one of them turns into `ImportError: cannot import name … from 'ok.util.window'` across the entire device layer — that is exactly how the missing `WINDOWS_BUILD_NUMBER` was found.

Two of these already behave correctly on Linux in the upstream source and can be transcribed verbatim:

```python
WGC_NO_BORDER_MIN_BUILD = 20348
WINDOWS_BUILD_NUMBER = int(platform.version().split(".")[-1]) if sys.platform == "win32" else -1
```

and `windows_graphics_available()` therefore falls off the end and returns **`None`** on Linux (not `False`) — falsy at every call site, so returning `False` explicitly is fine but is a behaviour change, not a fix. `ratio_text_to_number` and `find_display` are pure logic; copy them unchanged.

### V25 — `win32con` needs 94 constants, and the VK_* family is the load-bearing half [VERIFIED]

`grep -rhoP "win32con\.\w+" --include=*.py ok | sort -u` yields **94** distinct names. Earlier drafts said "~60 `WM_*`/`MK_*`/`WA_*`/`SW_*`/`GWL_*`/`CTRL_*`" and omitted the 40 `VK_*` constants entirely — the ones `ok/device/interaction_methods/keys.py` uses to build `vk_key_dict`, which is what `post_message.py:59` looks every keypress up in. The exact set to transcribe:

```
CF_DIB CF_UNICODETEXT CTRL_CLOSE_EVENT CTRL_C_EVENT CTRL_LOGOFF_EVENT CTRL_SHUTDOWN_EVENT
GWL_EXSTYLE GWL_STYLE GW_HWNDNEXT GW_OWNER HWND_NOTOPMOST HWND_TOPMOST IDI_APPLICATION
IMAGE_ICON LR_DEFAULTSIZE LR_LOADFROMFILE MK_LBUTTON MK_MBUTTON MK_RBUTTON
MONITOR_DEFAULTTONEAREST SM_CXSCREEN SM_CYSCREEN SRCCOPY SWP_FRAMECHANGED SWP_NOMOVE
SWP_NOSIZE SWP_SHOWWINDOW SW_RESTORE SW_SHOW VK_BACK VK_CAPITAL VK_CONTROL VK_DELETE
VK_DOWN VK_END VK_ESCAPE VK_F1 VK_F2 VK_F3 VK_F4 VK_F5 VK_F6 VK_F7 VK_F8 VK_F9 VK_F10
VK_F11 VK_F12 VK_HOME VK_INSERT VK_LCONTROL VK_LEFT VK_LMENU VK_LSHIFT VK_LWIN VK_MENU
VK_NEXT VK_NUMLOCK VK_PRIOR VK_RCONTROL VK_RETURN VK_RIGHT VK_RMENU VK_RSHIFT VK_RWIN
VK_SCROLL VK_SHIFT VK_SNAPSHOT VK_SPACE VK_TAB VK_UP WA_ACTIVE WA_INACTIVE WHEEL_DELTA
WM_ACTIVATE WM_CHAR WM_CLOSE WM_DESTROY WM_KEYDOWN WM_KEYUP WM_LBUTTONDOWN WM_LBUTTONUP
WM_MBUTTONDOWN WM_MBUTTONUP WM_MOUSEMOVE WM_MOUSEWHEEL WM_RBUTTONDOWN WM_RBUTTONUP
WM_SETFOCUS WM_USER WS_CAPTION WS_OVERLAPPED WS_POPUP WS_SYSMENU
```

**This is a silent-corruption hazard, not an import error.** With `win32con` stubbed as a `_Missing`, `keys.py` *imports fine* and `vk_key_dict['F1']` becomes a `_Missing` object rather than `0x70`; the shim would then be handed nonsense virtual-key codes with no exception anywhere. Ship the real constants module and add a unit test asserting `isinstance(vk_key_dict['F1'], int)`.

For reference, the corresponding surfaces on the other two stubs (all *called*, so `_Missing` is correct for them):

```
win32api: EnumDisplayMonitors GetAsyncKeyState GetCursorPos GetModuleHandle GetMonitorInfo
          GetSystemMetrics MAKELONG MapVirtualKey MonitorFromWindow SetConsoleCtrlHandler
          SetCursorPos VkKeyScan
win32gui:  BringWindowToTop ClientToScreen CreateWindow DeleteObject EnumChildWindows EnumWindows
          GetClassName GetClientRect GetDC GetForegroundWindow GetParent GetTopWindow GetWindow
          GetWindowDC GetWindowLong GetWindowRect GetWindowText IsIconic IsWindow IsWindowEnabled
          IsWindowVisible LoadIcon LoadImage PostMessage PostQuitMessage PumpMessages RegisterClass
          ReleaseDC ScreenToClient SendMessage SetForegroundWindow SetWindowLong SetWindowPos
          ShowWindow WNDCLASS
```

`win32api.MAKELONG(a, b) == (b << 16) | a` — needed in Phase 4c.

### V26 — stale line references and four unmentioned repo files [VERIFIED]

Corrected in place throughout; recorded here so you do not re-derive them.

| Claim in an earlier draft | Actual (ok-script 2.0.5) |
|---|---|
| `make_lparam` at `post_message.py:56-62` | **`:50-55`**. `:57-63` is `get_key_by_str`. |
| `post()` at `post_message.py:85-92` | **`:91-97`** |
| `visible = self.is_foreground()` at `hwnd_window.py:283` | **`:285`** |
| `get_frame` at `base.py:31-41` / `33-41` | **`:31-44`** |
| `get_mute_state`/`set_mute_state` at `hwnd_window.py:415-445` | **`:414-446`** |
| `available_capture_methods` consumed at `ok/ui/web/app.py:428` | **`:427`** (`_capture_methods` starts at `:424`) |
| `find_hwnd` returns `hwnds = []` | on a **match** it returns `[biggest]`, a 1-element list of 9-tuples `(hwnd, full_path, width, height, x, y, title, class_name, scaling)`; `[]` only on the no-match paths. Returning `[]` on Linux is safe — see **[V17]**. |
| `browser.py` imports `win32gui` + three `ok.util.window` names | plus **`from ok.device.capture_methods.windows_graphics import WindowsGraphicsCaptureMethod`** at `:15` |
| `SelectInteractionListView` "only renders a picker when the value is a list" | it wraps a bare string at `:23-24`; a list is needed to offer **two** choices, not to render at all |

Confirmed-correct references that earlier drafts got right, listed so you can skip re-checking: `hwnd_window.py:22` (constructor signature), `:27-71` (attributes), `:247` (`find_hwnd` call), `:263-266` (`real_*` assignment), `:292-301` (pause-on-`pos_valid`), `:352-358` (`is_foreground`), `:364` (`handle_mute`), `:385-398` (`check_pos`/`get_monitors_bounds`), `:401` (20-px tolerance); `ok/util/window.py:429`; `post_message.py:112`/`:115` (swipe), `:185-236` (`update_mouse_pos`), `:245-246` (`mouse_up`), `:248-249` (`should_capture`); `DeviceManager.py:257` (find_hwnd → `width`, `height` at positions 5 and 6), `:388`, `:626-628` (`ensure_hwnd`); `config.py:189-203` (the `windows` block, quoted verbatim in Phase 5b), `config.py:167-168` (`use_openvino`/`use_npu` both `True`), `config.py:210-214` (`supported_resolution`); `src/globals.py:21`; `MouseResetTask.py:38-52` and `:39`; `CombatCheck.py:223-230`; `tests/TestMouseResetTask.py:56-57`; `ok/__init__.py:705-706` and `:1042-1054`.

**Four ok-ww repo files were never mentioned by any earlier draft.** All four are real Windows coupling outside `src/`:

```
requirements.txt   pip-compile lockfile, NO platform markers: pywin32==311,
                   pycaw==20240210, pydirectinput==1.0.4, comtypes==1.4.16
                   -> `pip install -r requirements.txt` fails on Linux, same as [V3]
pyappify.yml       Windows installer manifest (uac, use_pythonw, git_url updaters)
deploy.txt         updater file manifest; lists ok-ww.exe and pyappify
setup.py           classifier "Operating System :: Microsoft :: Windows";
                   cythonize() over src/**/*.pyx -- but there are ZERO .pyx files
                   in the repo, so it is a no-op and needs no change to build
```

Handled in Phase 1a and Phase 5e. Also verified: the four `main*.py` entry points are pure `from config import config; OK(config).start()`, and `tests/TestMouseResetTask.py` is the **only** file under `tests/` that touches Win32.

---

## 3. Target architecture

```
┌──────────────────────── Linux (native) ─────────────────────────┐
│  ok-ww  (unchanged game logic: src/char, src/combat, src/task)  │
│  ok-script-linux (fork)                                         │
│    ├─ X11Window            ← window discovery/geometry, python-xlib
│    ├─ X11CaptureMethod     ← XGetImage + MIT-SHM  [BaseCaptureMethod]
│    └─ WinePostMessageInteraction  ────────┐      [BaseInteraction]
│  OCR: onnxocr + OpenVINO (native, fast)   │                      │
└───────────────────────────────────────────┼──────────────────────┘
                                            │ TCP 127.0.0.1, line protocol
┌───────────────── Game's Proton prefix ────┼──────────────────────┐
│  okww-input-shim.exe  ────────────────────┘                      │
│    FindWindow/EnumWindows → HWND                                 │
│    PostMessageW(WM_KEYDOWN/UP, WM_CHAR, WM_MOUSEMOVE, WM_*BUTTON*)│
│    GetCursorPos / SetCursorPos                                   │
│                          ↓                                       │
│  Client-Win64-Shipping.exe  (Wuthering Waves)                    │
└──────────────────────────────────────────────────────────────────┘
```

**Design rationale.** Heavy CV/OCR stays native (no Wine penalty, NPU/GPU reachable). Only a few KB of input logic runs in the prefix. `ok-script`'s existing `PostMessageInteraction` semantics are preserved exactly, so upstream task logic behaves identically.

**Split of responsibility (important — avoids double-mapping bugs):**
- **Linux side** owns capture-space → client-space coordinate mapping (it knows the letterbox crop, via `get_crop_point`).
- **Shim** receives **client-area coordinates** and does only `GetClientRect`/`ClientToScreen`/`ScreenToClient` on the target HWND.

---

## 4. Work plan

### Phase 0 — Fork ok-script

1. Fork `ok-script` 2.0.5 → `ok-script-linux`. Pin ok-ww to it (path/git dep in `pyproject.toml`).
2. Rebase-friendly layout: keep all Linux code in **new files**; touch existing files only for import guards and registry entries. Upstream tracks fast, and ok-ww pins `>=2.0.5`.

### Phase 1 — Make `import ok` work on Linux

**1a. Dependency markers** (`pyproject.toml` of the fork):

```toml
"pywin32!=312,>=306 ; sys_platform == 'win32'",
"pydirectinput==1.0.4 ; sys_platform == 'win32'",
"pycaw==20240210 ; sys_platform == 'win32'",
"ok-d3dshot>=0.1.5 ; sys_platform == 'win32'",   # in the 'default' extra
# add:
"python-xlib>=0.33 ; sys_platform == 'linux'",
```

`mouse`, `pynput`, `psutil`, `numpy`, `Pillow`, `OpenCC`, PySide6 stack — all cross-platform, leave alone.

**Also fix ok-ww's own lockfile — earlier drafts never mentioned it.** `requirements.txt` in this repo is a `pip-compile` output with **no platform markers**, pinning `pywin32==311`, `pycaw==20240210`, `pydirectinput==1.0.4` and `comtypes==1.4.16`. `pip install -r requirements.txt` therefore fails on Linux exactly the way `pip install ok-script` does **[V3]**. After the fork's markers land, regenerate it:

```sh
pip-compile --pip-args='--index-url https://pypi.org/simple' pyproject.toml
```

Check the regenerated file no longer lists those four, and that `ok-script` points at the fork. Note `pyproject.toml`'s `web-test` extra pins a stale `ok-script[web]==2.0.0b7`; leave it or drop it, but do not let it pull an unforked ok-script into a Linux env.

**1b. Do NOT guard the aggregators — this step was measured away [V22].**

Earlier drafts wrapped the Windows backends in `if _WINDOWS:` blocks in `ok/device/capture_methods/__init__.py` and `ok/device/interaction_methods/__init__.py`, and then spent a page enumerating every name that had to be re-exported on both platforms. **Skip all of it.** Measured on this machine: with the `win32_stub` from 1c plus the Linux `ok/util/window.py` from Phase 2, all eleven Windows-flavoured device modules import unmodified on Linux and all 71 `_LAZY_IMPORTS` names resolve.

Guarding them is not merely wasted effort, it is a regression:

- `DeviceManager.py:11-12` does `from ok.device.interaction import PostMessageInteraction, GenshinInteraction, ForegroundPostMessageInteraction, PynputInteraction, PyDirectInteraction, BrowserInteraction, ADBInteraction` **at module level**. Guard any of those out and `DeviceManager` — the module the whole app is built on — stops importing.
- `DeviceManager.py:9-10` likewise does `from ok.device.capture import HwndWindow, BrowserCaptureMethod, update_capture_method, NemuIpcCaptureMethod, ADBCaptureMethod`.
- 17 of the 71 `_LAZY_IMPORTS` entries route through `ok.device.capture` / `ok.device.interaction` and would stop resolving.
- It is a large diff against a fast-moving upstream, which is exactly what Phase 0 says to avoid.

The Windows backends being *importable* on Linux is harmless: nothing selects them. `update_capture_method` (`update.py:16-44`) only instantiates the method names listed in `config['windows']['capture_method']`, and `DeviceManager`'s two interaction ladders only instantiate what `config['windows']['interaction']` names — both overridden in Phase 5b.

**The only edits this phase needs in `ok/device/`:**

1. `ok/device/capture_methods/__init__.py` — add the two new Linux modules and make `HwndWindow` resolve to the Linux class:

   ```python
   import sys
   # ... leave every existing import exactly as it is, including line 21's
   #     `from ...hwnd_window import HwndWindow, check_pos, get_monitors_bounds,
   #      get_mute_state, is_window_in_screen_bounds, set_mute_state`
   #     — then shadow that whole group on Linux:
   if sys.platform == 'linux':
       from ok.device.capture_methods.x11_window import (
           X11Window, check_pos, get_monitors_bounds, get_mute_state,
           is_window_in_screen_bounds, set_mute_state,
       )
       from ok.device.capture_methods.x11_capture import X11CaptureMethod
       HwndWindow = X11Window          # DeviceManager.py:9 and ensure_hwnd() use this name
   ```

   Rebinding after the upstream import line is a small diff and keeps every other export intact. (`ok/device/capture.py` re-exports via `import *` — the package defines no `__all__`, so the rebound names win — and `DeviceManager.ensure_hwnd` constructs `HwndWindow` at `DeviceManager.py:626-628`.) Verified: **`ok/device/capture_methods/__init__.py:21` is the only place in the tree that imports those five helpers**; nothing else references them by name, so shadowing them here is sufficient and complete.

2. `ok/device/interaction_methods/__init__.py` — one added import:

   ```python
   if sys.platform == 'linux':
       from ok.device.interaction_methods.wine_post_message import WinePostMessageInteraction
   ```

3. `ok/device/capture_methods/update.py` — register the new capture methods (Phase 3).

`ok/device/capture.py`, `ok/device/interaction.py`, `ok/device/capture_methods/types.py` and `ok/ui/overlay/__init__.py` need **no** changes: measured importable as-is under the stub. (`types.py`'s `is_valid_hwnd` already has its own `sys.platform == "win32"` branch at line 36; only its module-level `import win32gui` is Windows-flavoured, and the stub covers that.)

**One thing that genuinely is platform-neutral and should still move:** `get_crop_point` and `parse_reg_flag` live in `bitblt_utils.py` but are pure geometry. Move them to a new `ok/device/capture_methods/geometry.py` and re-export from `bitblt_utils` so the Linux capture path can import `get_crop_point` without dragging in the BitBlt machinery. Transcribe `get_crop_point` **verbatim** — the asymmetry is deliberate, do not "fix" it:

```python
def get_crop_point(frame_width, frame_height, target_width, target_height):
    x = round((frame_width - target_width) / 2)
    y = (frame_height - target_height) - x
    return x, y
```

**`browser.py` must be ported, not guarded out.** It is in Group A of **[V16]** (module-level `import win32gui`, plus `from ok.util.window import resize_window, windows_graphics_available, find_hwnd` at line 11 **and `from ok.device.capture_methods.windows_graphics import WindowsGraphicsCaptureMethod` at line 15** — earlier drafts missed that last one). `BrowserCaptureMethod` is in `_LAZY_IMPORTS`, is imported at module level by `DeviceManager`, and `hwnd_window.do_update_window_size` opens with an `isinstance(self.device_manager.capture_method, BrowserCaptureMethod)` check (`hwnd_window.py:236-239`, a function-level import). §6 promises the cloud-game backend keeps working, so it needs the Linux `ok/util/window.py` contracts from Phase 2 — which, per **[V22]**, is all it needs: it imported cleanly in the measurement.

**1c. The compatibility shim — corrected [V21]. The version in earlier drafts does not work.**

The full list of module-level offenders is in **[V16]** — 27 modules, most of them GUI leaves whose Windows code is never reached on Linux. Cover them with a `sitecustomize`-style shim installed **before** `import ok`:

```python
# ok/compat/win32_stub.py  — install() runs before anything imports ok.*
import ctypes, sys

# Names whose *call* at import time must succeed and yield another stub, because
# four modules load a DLL at module level [V16]:
#   ok/util/window.py:18, ok/rotypes/roapi.py:7,
#   ok/rotypes/winstring.py:6, ok/rotypes/Windows/Foundation/__init__.py:9
_LOADERS = ('LoadLibrary', 'WinDLL', 'OleDLL', 'CDLL', 'windll', 'oledll')


class _Missing:
    def __init__(self, path):
        self._path = path

    def __getattr__(self, n):
        if n.startswith('__'):          # keep copy/pickle/inspect from getting a _Missing
            raise AttributeError(n)
        return _Missing(f'{self._path}.{n}')

    def __call__(self, *a, **k):
        leaf = self._path.rsplit('.', 1)[-1]
        if leaf in _LOADERS:
            return _Missing(f'{self._path}(...)')   # a DLL handle stub, not an error
        raise NotImplementedError(f'Windows-only symbol called on Linux: {self._path}')


def install():
    if sys.platform == 'win32':
        return

    # --- ctypes: symbols that do not exist on Linux [V16] ------------------
    ctypes.windll = _Missing('ctypes.windll')      # makes `from ctypes import windll` work
    ctypes.oledll = _Missing('ctypes.oledll')
    ctypes.WinDLL = _Missing('ctypes.WinDLL')
    ctypes.OleDLL = _Missing('ctypes.OleDLL')
    # HRESULT and WINFUNCTYPE are used as *types*, at module level, in
    # ok/rotypes/delegate.py. A _Missing here raises during import.
    ctypes.HRESULT = ctypes.c_long                 # pywin32/rotypes define HRESULT = LONG
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE          # NOT sufficient for ok/rotypes — see below

    # --- modules ----------------------------------------------------------
    for m in ('win32api', 'win32gui', 'win32process', 'win32ui', 'win32file',
              'win32clipboard', 'pythoncom', 'pydirectinput', 'pycaw',
              'comtypes', 'd3dshot', 'winreg'):
        sys.modules.setdefault(m, _Missing(m))
    sys.modules.setdefault('win32con', _win32con_constants())  # NOT a _Missing — see below
```

Measured behaviour of this corrected stub on python3.12: `from ctypes import windll` succeeds, `import win32gui` succeeds, `win32gui.PostMessage(...)` raises `NotImplementedError: Windows-only symbol called on Linux: win32gui.PostMessage`, and every device-path module imports **[V22]**. That is what you want — imports succeed, and any path that *actually* needs Windows fails loudly, naming the symbol, instead of silently no-opping.

Four details that are easy to get wrong. The first two were defects in the previous draft of this plan; both were found by running it.

- **`_Missing.__call__` must not raise for DLL loaders [V21].** Four modules call one at module level. With a plain always-raising `__call__` the stub dies with `NotImplementedError: ... ctypes.windll.LoadLibrary` on `import ok.rotypes.winstring`, `ok.rotypes.roapi`, `ok.rotypes.Windows.Foundation`, and — the one that blocks the entire device layer — `ok.util.window`. (`ok/util/window.py` is replaced wholesale in Phase 2, but the other three are not.)
- **`ok/rotypes` cannot be stubbed into importability at all, and must not be [V21].** `ok/rotypes/inspectable.py:12` uses the COM vtable prototype form `WINFUNCTYPE(...)(0, "QueryInterface")`, which `CFUNCTYPE` rejects with `TypeError: function takes exactly 1 argument (2 given)`. There is no pure-Python fix. This is fine, because `ok.rotypes` and `ok.capture.windows` are **only ever imported from inside functions** (`ok/util/window.py:windows_graphics_available()`, `ok/device/capture_methods/windows_graphics.py:189-196,241`), and on Linux neither body runs: `WINDOWS_BUILD_NUMBER == -1` short-circuits the first, and WGC is not in the Linux `capture_method` list. **Never import `ok.rotypes.*` or `ok.capture.windows.*` on Linux, and exclude them from the exit-criterion sweep.**
- **`ctypes.HRESULT` and `ctypes.WINFUNCTYPE` must still be real objects.** `ok/rotypes/delegate.py:9-11` does `WINFUNCTYPE(HRESULT, c_void_p, ...)` at module level; a `_Missing` there raises during import.
- **`winreg` must be stubbed as a module**, not left absent — `ok/alas/emulator_windows.py:5` imports it at module level and `ModuleNotFoundError` is not caught anywhere.
- **`from ctypes import *` picks the patched names up.** `ctypes` defines no `__all__`, so a star-import re-exports whatever `install()` set. That is what makes `ok/rotypes/{roapi,inspectable}.py` importable *as far as they get*. It also means `install()` **must** run before the first `import ok.*`, not lazily.

**One exception: `win32con` must be real, and it needs 94 constants including the whole `VK_*` family [V25].** Its members are integers used in comparisons, bit-arithmetic and — critically — as the *values* of `vk_key_dict` in `ok/device/interaction_methods/keys.py`. A `_Missing` there does **not** raise; it silently makes every virtual-key code a `_Missing` object, and the shim receives garbage. The exact 94-name list is in **[V25]**. `win32con` in pywin32 is itself pure Python, so this is transcription, not reimplementation. Add a unit test: `assert isinstance(vk_key_dict['F1'], int)`.

`ok/rotypes/types.py` is **not** an offender and needs no help: it does `from ctypes.wintypes import *` and `HRESULT = LONG`, both of which work on Linux unmodified.

`ok/__init__.py` imports `win32api`/`win32con` **lazily inside functions** (`:705-706` `win32api.SetConsoleCtrlHandler`, `:1042-1054` the `win32con.CTRL_*_EVENT` comparisons) — give that a Linux branch (`signal.signal(SIGINT/SIGTERM)`) rather than letting the stub raise.

**Exit criterion Phase 1 (replaces the old one — see [V2], the old one was a false green; corrected again per [V21][V22]):**

```python
# tools/check_linux_imports.py
import importlib
from ok.compat.win32_stub import install; install()   # must precede `import ok`
import ok
from ok import _LAZY_IMPORTS

# Skip names whose *extras* are absent, or you will chase a failure that is not yours:
#   run_web    -> ok.ui.web.server -> fastapi/uvicorn/pywebview  (ok-script's 'web' extra)
#   MainWindow -> ok.ui.qt.MainWindow -> pyappify, PySide6       (installed by ok-ww, but
#                 not in a bare checkout; keep it in the sweep once deps are installed)
SKIP = {'run_web'}

failed = []
for name, (mod, attr) in _LAZY_IMPORTS.items():
    if name in SKIP:
        continue
    try:
        getattr(importlib.import_module(mod), attr)
    except Exception as e:
        failed.append((name, mod, type(e).__name__, e))
assert not failed, failed
```

Every lazily-mapped symbol must resolve — that is what actually exercises `MainWindow`, `DeviceManager`, `check_mutex`, `windows_graphics_available`, `Analytics`. `_LAZY_IMPORTS` is module-level in `ok/__init__.py:94` (it is not in `__all__`, but the import works). There are **71** entries; the pass condition is `failed == []` with only `run_web` skipped.

**Do not add `ok.rotypes` or `ok.capture.windows` to this sweep** — they are unreachable on Linux by design **[V21]**, and adding them turns a green build red for no reason.

This check only resolves *module-level* code. `MainWindow` reaches `ok/ui/qt/tasks/TemplateTab.py:19` (→ `windows_thumbnail`, which is already platform-guarded and whose `open()` returns `False` on Linux **[V16]**) from inside `__init__`, not at import. Follow the script with a headless `OK(config)` construction (`QT_QPA_PLATFORM=offscreen`) up to the point where `do_start` selects a capture method — that is the step that actually proves the GUI leaves are covered.


### Phase 2 — `X11Window` (replaces `HwndWindow`)

New file `ok/device/capture_methods/x11_window.py`. It must be **attribute-compatible** with `HwndWindow` — the rest of ok-script and ok-ww read these directly.

**Exact constructor signature** (`hwnd_window.py:22`) — keep it byte-identical, `DeviceManager` calls it positionally and by keyword:

```python
def __init__(self, exit_event, title, exe_name=None, frame_width=0, frame_height=0,
             player_id=-1, hwnd_class=None, global_config=None, device_manager=None,
             top_hwnd_class=None):
```

The constructor must, in this order: set every attribute below, call `get_monitors_bounds()`, take `self.mute_option = global_config.get_config(basic_options)` and install `self.mute_option.validator = self.validate_mute_config`, call `update_window(...)`, then start a **daemon** thread running `update_window_size`.

Required attributes (from `hwnd_window.py:27-71` — the full set, including the ones an earlier draft omitted):

```
# geometry / identity
hwnd, top_hwnd, hwnds, exists, visible, title, exe_full_path, exe_names,
x, y, width, height, window_width, window_height,
client_width, client_height, real_width, real_height,
real_x_offset, real_y_offset, top_offset_x, top_offset_y,
scaling, frame_width, frame_height, frame_aspect_ratio,
pos_valid, player_id, monitors_bounds, visible_monitors,
hwnd_class, top_hwnd_class

# lifecycle / collaborators — all read from outside the class
app_exit_event, stop_event, thread,
global_config, device_manager, mute_option, to_handle_mute, last_mute_check,
_hwnd_title
```

Required methods (same semantics as the Windows original):

```python
get_abs_cords(x, y)            # -> (self.x + x, self.y + y)
get_capture_origin()           # real_*_offset, else get_crop_point(client_w, client_h, w, h)
get_top_window_cords(x, y)     # -> (x - top_offset_x, y - top_offset_y)
capture_target_signature       # @property, tuple; used to detect target change
hwnd_title                     # @property, cached window title
update_window(title, exe_name, frame_width, frame_height, player_id=-1,
              hwnd_class=None, top_hwnd_class=None)
update_frame_size(width, height)     # note: sets self.hwnd = 0 then re-polls
do_update_window_size()        # the poll body
update_window_size()           # daemon thread loop (constructor starts it)
try_resize_to(resize_to)
bring_to_front()
is_foreground()
handle_mute(mute=None)
frame_ratio(size)
validate_mute_config(key, value)
_front_hwnd_candidates()
_top_hwnd_info(hwnds)
stop()
__str__()
```

**Implementation notes:**

- `hwnd` = the X11 window id (an int — keeps every `if hwnd > 0` check in the codebase valid). Set `top_hwnd = hwnd`, `top_offset_x = top_offset_y = 0`; Wine gives one X toplevel for the game, so the Windows child-window/top-window distinction collapses. `hwnds = []`.
- **Window discovery — `_NET_WM_PID` is the only reliable key [V8][V11].** Enumerate toplevels; read `_NET_WM_PID`; resolve `/proc/<pid>/cmdline`; match against `config['windows']['exe']` (`Client-Win64-Shipping.exe`).
  **Do not use `WM_CLASS`:** every Proton window reports `"steam_proton"`, and the Win32 class `UnrealWindow` from `config.py` is invisible from X11 — it exists only inside Wine **[V11]**. Do not match on window title alone either; the game changes it. If PID matching ever needs a tiebreak (multiple toplevels on one PID — the game plus Wine's 1×1 `Default IME` helper windows, which were present in testing), discriminate by **geometry**: ignore windows smaller than `min_size` from `config.py`'s `supported_resolution`.
- **Geometry:** `XGetGeometry` + `XTranslateCoordinates(win, root, 0, 0)` for absolute `x, y`. Under Wine there are no separate client/window rects worth distinguishing for a fullscreen-borderless Unreal window: set `client_width == width`, `client_height == height`. If the game runs windowed with decorations, subtract the frame via `_NET_FRAME_EXTENTS`.
- **`visible` means FOREGROUND, not mapped — do not get this wrong [V15].** Upstream sets `visible = self.is_foreground()`. Implement it as "`hwnd` currently holds input focus": compare the root window's `_NET_ACTIVE_WINDOW` against `hwnd`, falling back to `XGetInputFocus` walked up to the toplevel. Defining it as mapped-and-not-Iconic (as an earlier draft of this plan did) makes it permanently `True` during background play, which silently disables `MouseResetTask`'s cursor pinning — the exact scenario this port exists for — and inverts `clickable()`.
- **Iconic/minimized is a *different* signal — and `check_pos` will not catch it for you.** Upstream `check_pos(x, y, width, height, monitors_bounds)` is only `width >= 0 and height >= 0 and is_window_in_screen_bounds(...)`. An iconic X11 window keeps its last geometry, so a naive port leaves `pos_valid` True forever, the executor is never paused, and capture just throws in a loop with no user-visible explanation. Compute it as:

  ```python
  iconic = self._wm_state(hwnd) == 3        # WM_STATE IconicState, or unmapped
  pos_valid = (not iconic) and check_pos(x, y, width, height, self.monitors_bounds)
  ```

  Upstream already pauses the executor and emits the "Paused because game window is minimized or out of screen!" notification on `pos_valid` going False (`hwnd_window.py:292-301`), so this one line restores the correct behaviour for free. Also surface it as a distinguishable `CaptureException` from the capture layer **[V7]**.
- **Supply the `ok/util/window.py` contracts too, not just the class [V17].** `X11Window` is not sufficient on its own: `DeviceManager.update_pc_device` (`DeviceManager.py:257`) calls `find_hwnd` to build the `windows` entry of `device_dict`, and if that returns nothing the `windows` branch of `do_start` is never taken and no capture starts at all. `ok/device/capture_methods/browser.py` imports `resize_window`, `windows_graphics_available` and `find_hwnd` from the same module. Port, with identical return shapes:
  - `find_hwnd(title, exe_names, frame_width, frame_height, player_id=-1, class_name=None, selected_hwnd=0, top_hwnd_class=None, last_hwnd=0)` → `(name, hwnd, full_path, real_x_offset, real_y_offset, real_width, real_height, hwnds)`.
    **`real_width` and `real_height` are the window's width and height, NOT zero [V18].** Only the two offsets are `0`, and `hwnds` is `[]` (no child-window enumeration — Wine gives one X toplevel; upstream returns `[biggest]` here, and `[]` is a deliberate, verified-safe deviation — see **[V17]**). Returning zeros produces a `0x0` PC device in `DeviceManager.py:257` and breaks `capture_target_signature`. The no-match return stays `(None, 0, None, 0, 0, 0, 0, [])`, exactly as upstream.
  - `get_window_bounds(hwnd)` → `(x, y, window_width, window_height, width, height, scaling)`; return `(0, 0, 0, 0, 0, 0, 1)` on error, as upstream does.
  - `is_foreground_window`, `find_all_visible_windows`, `show_title_bar` (no-op), `resize_window`, `windows_graphics_available` (→ `False`).
  - **And the four contracts earlier drafts missed [V24]** — omitting any one of them breaks the whole device layer with `ImportError: cannot import name … from 'ok.util.window'`:
    - `find_display(hmonitor, displays)` — imported by `desktop_duplication.py:5`. Pure logic; transcribe unchanged.
    - `ratio_text_to_number(supported_ratio)` — imported by **`ok/task/TaskExecutor.py:12`**, i.e. the core path, not a Windows leaf. Pure logic; transcribe unchanged.
    - `WINDOWS_BUILD_NUMBER` and `WGC_NO_BORDER_MIN_BUILD` — module-level constants imported by `windows_graphics.py:9`. Upstream already computes `WINDOWS_BUILD_NUMBER` as `-1` on non-win32; keep that line verbatim, it is what makes `windows_graphics_available()` short-circuit on Linux and never touch `ok.rotypes` **[V21]**.
  - **These five live in `hwnd_window.py`, not in `ok/util/window.py`** — port them alongside `X11Window`: `get_monitors_bounds()`, `check_pos`, `is_window_in_screen_bounds`, `get_mute_state`, `set_mute_state`.
    `get_monitors_bounds()` → RandR `get_monitors` via python-xlib (the `randr` extension is present **[V13]**), returning `(left, top, right, bottom)` rects so `is_window_in_screen_bounds`/`check_pos` keep working unchanged. Keep upstream's 20-pixel tolerance.
- `device_manager` is read inside `do_update_window_size` for `device_manager.config['selected_exe']`, `device_manager.capture_method`, and `device_manager.executor`; `global_config` for `get_config('Basic Options')` in `try_resize_to` and for `'Exit App when Game Exits'`.
- `do_update_window_size` logs `win32gui.GetClassName(self.hwnd)` on the hwnd-changed branch; drop that from the Linux copy (the Win32 class is invisible from X11 **[V11]**).
- `scaling = 1.0` (Xwayland reports device pixels; if the user runs fractional scaling, read `_NET_WM_...`/randr and adjust — treat as an enhancement, not v1).
- `bring_to_front()`: `_NET_ACTIVE_WINDOW` client message via python-xlib (or shell out to `wmctrl -i -a`). Under KDE Wayland focus-stealing prevention may refuse; log and continue — **it must not raise**. Upstream returns `True`/`False` and retries once after a forced `do_update_window_size()`; keep that shape.
- `try_resize_to()`: `XResizeWindow`. Note upstream also reads the screen size via `win32api.GetSystemMetrics(0)` / `(1)` to pick the largest entry of `resize_to` that fits, and derives `border = window_width - width` / `title_height = window_height - height` from `get_window_bounds`. On Linux take the screen size from the RandR monitor list you already built for `get_monitors_bounds()` (use the monitor the window is on, not a hardcoded primary). Under Proton the game usually controls its own resolution; make failure non-fatal and let the existing `supported_resolution` logic in `config.py` (`resize_to`, `min_size`) handle mismatch.
- **Polling cadence is `time.sleep(0.2)`** in `update_window_size`'s `while not app_exit_event.is_set() and not stop_event.is_set()` loop. Keep 0.2 s exactly — downstream change-detection and the 2-second `last_mute_check` interval are tuned to it. On loop exit, upstream unmutes (`set_mute_state(self.hwnd, 0)`) if the mute option is on; reproduce that with the pactl equivalent (§6).

### Phase 3 — `X11CaptureMethod`

New file `ok/device/capture_methods/x11_capture.py`, subclassing **`BaseWindowsCaptureMethod`** (not `BaseCaptureMethod`): `get_capture()` in `update.py` constructs it as `target_method(hwnd_window)` and then assigns `.hwnd_window` and `.exit_event`, and the base gives you that property plus `get_abs_cords()` — which `CombatCheck.py:225` and `MouseResetTask.py:40` call as `interaction.capture.get_abs_cords(...)`. Override `clickable()` to return `True` (the base returns `hwnd_window.visible`, which is a *foreground* test **[V15]** and would read False for the whole of background play).

Scope note on that override: `PostMessageInteraction` — and therefore `WinePostMessageInteraction` — never calls the capture object's `clickable()`. Only `PynputInteraction`, `PyDirectInteraction` and `ForegroundPostMessageInteraction` gate on it, and they define their own `clickable()` against `hwnd_window.is_foreground()`. So the override is correct and costs nothing, but it is not what makes background play work; **[V15]**'s load-bearing consumer is `MouseResetTask`, not `clickable()`.

Only `do_get_frame()` (plus `close`, `get_name`, `connected`, `clickable`) is required — the base class already handles size tracking, the `<=10px` guard, and BGRA→BGR (`base.py:31-44`).

```python
class X11CaptureMethod(BaseWindowsCaptureMethod):
    name = "X11"
    description = "X11/Xwayland per-window capture"

    def do_get_frame(self):
        # XShmGetImage into a persistent shared segment; reallocate on size change
        # -> contiguous np.ndarray (h, w, 3) BGR
```

**Requirements:**

- **Bind libX11/libXext through `ctypes` — python-xlib cannot do this [V13].** `from Xlib.ext import shm` does not exist at any version. Use python-xlib for the window layer (Phase 2) and raw `ctypes` for the pixel path. Watch two details: `XImage` ends in a `funcs` struct of six pointers and `XDestroyImage` is a C macro, so free via `CFUNCTYPE(c_int, POINTER(XImage))(img.contents.f.destroy_image)(img)`; and `bytes_per_line` is the stride (7680 for 1920px here) — slice by it, never assume `width*4`.
- **MIT-SHM is an optimization, not a gate [V14].** Measured at 1920×1080 on this machine: `XGetImage` 73.7 fps / 13.57 ms, `XShmGetImage` 805.3 fps / 1.24 ms. Both clear ok-ww's needs. Implement plain `XGetImage` first to unblock, then add SHM. Allocate one shared segment, reuse it, reallocate only on size change, and `shmctl(IPC_RMID)` immediately after `XShmAttach` so the segment is reclaimed even if the process dies.
- Depth 24/32 TrueColor → `ZPixmap` is BGRA on little-endian; verified `byte_order=0`, masks `R=ff0000 G=ff00 B=ff`, `bits_per_pixel=32` **[V14]**. **Do not** colour-swap manually — you will double-swap.
- **You must return a copy, and it must be `cv2.cvtColor`, not numpy slicing [V14].** The SHM segment is overwritten by the next `XShmGetImage`, while `TaskExecutor` holds frames across calls — so returning a view into the segment corrupts in-flight frames. Measured cost of the copy at 1080p: `arr[:, :, :3].copy()` 10.10 ms, `np.ascontiguousarray(...)` 9.69 ms, `arr.copy()` (full BGRA) 0.99 ms, **`cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)` 0.15 ms**. Return the 3-channel result directly; the base class's `if frame.shape[2] == 4` slice is then skipped. Total ≈1.4 ms/frame end to end.
  (A double-buffered pair of SHM segments would avoid even that, but at 0.15 ms it is not worth the complexity.)
- Raise `CaptureException` (the base class wraps exceptions already) with a distinguishable message when the window is Iconic **[V7]**, so the UI can tell the user "un-minimize the game" instead of showing a generic failure. Note the Xwayland root window is *not* capturable under rootless mode — `XGetImage` on it returns `BadMatch` (confirmed again during this audit), consistent with **[V7]**.
- Optional: the `damage` extension is available in python-xlib **[V13]**. Subscribing to `XDamageNotify` on the game window lets the poll loop skip grabs when nothing changed. Pure win, but not v1.
- **Occlusion needs no special handling** on Xwayland **[V7]**. For robustness on plain X11 (non-Wayland sessions, other distros), add an optional XComposite path: `XCompositeRedirectWindow(dpy, win, CompositeRedirectAutomatic)` + `XCompositeNameWindowPixmap`, then `XShmGetImage` the pixmap. Use `Automatic` (never `Manual` — `Manual` makes you responsible for painting and will blank the game). Select it via config: `capture_method: ['X11', 'X11_Composite']`.
- Implement `clickable()` → `True`, `connected()` → window still exists.

**Register in `update_capture_method`** (`ok/device/capture_methods/update.py`), alongside the existing `WGC`/`BitBlt`/`DXGI` branches:

```python
elif method_name in ('X11', 'X11_Composite'):
    if x11 := get_capture(capture_method, X11CaptureMethod, hwnd, exit_event):
        return x11
```

Also add them to `DeviceManager.available_capture_methods` so the GUI's capture-method picker lists them.

### Phase 4 — Input: the Wine PostMessage shim

This is the heart of the port. **[V6]** proves the mechanism.

#### 4a. The shim (`shim/okww-input-shim.c`)

A single-file C program, cross-compiled to a Windows exe, run inside the game's prefix. Keep it in C with no dependencies: it must start fast, and adding a Windows Python runtime to the prefix would be a large, fragile install.

- Bind a TCP listener on `127.0.0.1`, **port 0** (kernel-assigned). Write the chosen port plus a random 32-byte hex token to a file the Linux side reads. **Reject any connection that does not present the token as its first line.** Bind loopback only. This keeps a process that can synthesize input into your game off the network and away from other local users.
  **Path note:** the shim runs inside the prefix, so `$XDG_RUNTIME_DIR` is not directly addressable as a Windows path. Write the handshake file to a location visible on both sides — the prefix's `drive_c` (Linux: `$COMPATDATA/pfx/drive_c/okww-shim.port`; Wine: `C:\okww-shim.port`), or via the `Z:\` mapping of the host root. Ensure the file is created with restrictive permissions and deleted on exit.
- **Report status over the socket or that file, never stdout — `proton run` swallows stdout [V12].** Startup errors (target not found, bind failure) must be discoverable by the Linux side; a shim that dies silently must be detectable via the handshake file's absence plus a connect timeout.
- Resolve the target HWND with `EnumWindows`, matching process image name against `Client-Win64-Shipping.exe` (`GetWindowThreadProcessId` → `QueryFullProcessImageNameW`), with window-class `UnrealWindow` as a secondary filter. Re-resolve on `IsWindow(hwnd) == FALSE` and expose a `FINDWIN` command to force it.
- Line protocol, ASCII, one command per line, reply `OK`/`ERR <msg>`/`<value>`:

| Command | Maps to |
|---|---|
| `HELLO <token>` | auth |
| `FINDWIN` | re-resolve HWND; replies `hwnd=<h>` or `ERR notfound` |
| `GEOM` | `GetClientRect` + `ClientToScreen` → `x y w h` |
| `ACTIVATE` | `PostMessageW(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)` — mirrors `try_activate()` |
| `DEACTIVATE` | `PostMessageW(hwnd, WM_ACTIVATE, WA_INACTIVE, 0)` — mirrors `deactivate()` (`post_message.py:128-129`); earlier drafts omitted this row while still listing `deactivate` as a method to port |
| `KEYDOWN <vk>` | `WM_KEYDOWN`, lparam `(MapVirtualKeyW(vk,0)<<16)\|1` |
| `KEYUP <vk>` | `WM_KEYUP`, lparam `\| (1<<30) \| (1<<31)` |
| `CHAR <codepoint>` | `WM_CHAR` |
| `MOUSEMOVE <x> <y> [<mk>]` | `WM_MOUSEMOVE`, lparam `MAKELPARAM(x,y)`, wparam = button mask |
| `LDOWN/LUP/RDOWN/RUP/MDOWN/MUP <x> <y>` | `WM_?BUTTONDOWN/UP` with `MK_?BUTTON` |
| `WHEEL <x> <y> <delta>` | `WM_MOUSEWHEEL`, wparam `MAKELONG(0, WHEEL_DELTA*delta)` |
| `GETCURSOR` | `GetCursorPos` → `x y` |
| `SETCURSOR <x> <y>` | `SetCursorPos` |
| `PING` / `QUIT` | liveness / shutdown |

Match `post_message.py` exactly on lparam construction (`make_lparam`, **`post_message.py:50-55`** — earlier drafts said 56-62, which is `get_key_by_str`) — the scan-code and transition bits are what make the game accept the key. The exact upstream body:

```python
def make_lparam(self, vk_code, is_up=False):
    scan_code = win32api.MapVirtualKey(vk_code, 0)
    lparam = (scan_code << 16) | 1
    if is_up:
        lparam |= (1 << 30) | (1 << 31)
    return lparam
```

`MapVirtualKey(vk, 0)` (`MAPVK_VK_TO_VSC`) must run **inside Wine**, so the scan code matches what the game's Unreal input layer expects — do not precompute it on the Linux side. **[V6]** confirmed this exact lparam form works under Wine.

`GETCURSOR`/`SETCURSOR` exist because two ok-ww call sites need the **real** OS cursor, not a synthesized message:
- `CombatCheck.py:223-230` — the tab-wheel radial menu reads actual cursor position; it warps the cursor, selects, then restores.
- `MouseResetTask.py:38-52` — pins the physical cursor so background play doesn't drag the user's pointer around.

Under Wine, `SetCursorPos` maps to `XWarpPointer` in the game's own coordinate space — the correct equivalent, and it keeps both behaviours identical to Windows. Do **not** reimplement these on the Linux side with `XWarpPointer` against a different display connection; you would fight Wine over cursor state.

Build:

```sh
x86_64-w64-mingw32-gcc -O2 -s -o okww-input-shim.exe shim/okww-input-shim.c -lws2_32
```

Commit the built exe **and** the source; not every user will have mingw. Reproducible from source on both distros (Fedora: `mingw64-gcc`; NixOS: `pkgsCross.mingwW64.stdenv.cc`).

#### 4b. Launching the shim into the running prefix — **mechanism [VERIFIED], see [V10]**

The shim must join the **same `wineserver` instance** as the game — `PostMessage` cannot cross prefixes or wineserver sessions. **[V10] proves separate `proton run` invocations share one wineserver session and that `PostMessage` crosses between them**, using the user's real Proton build.

> **[GATE-1b] — what [V10] did NOT prove [V19].** In V10 *both* processes were launched by bare `proton run` from the host. The real game is launched by Steam **inside** the SteamLinuxRuntime_4 pressure-vessel container (`toolmanifest.vdf`: `require_tool_appid 4183110`). A host-side `proton run` and a containerised game may not see the same `/tmp/.wine-1000` socket directory or resolve `WINEPREFIX` to the same path. Test this **before** [GATE-2] — it is the same spike session, and it decides whether the primary method below or fallback 1 is the primary method.

**Primary method** (verified against a scratch prefix, both sides host-side — see [GATE-1b] above):

```sh
STEAM_COMPAT_DATA_PATH="$COMPATDATA"   \  # .../steamapps/compatdata/3513350
STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" \
"$PROTON_DIR/proton" run 'C:\okww-input-shim.exe'
```

**Resolving `$PROTON_DIR` — do not hardcode.** Read line 1 of `compatdata/3513350/config_info`, which holds the Proton build name; subsequent lines give absolute paths into the tool directory. Re-confirmed during this audit — the actual file here is:

```
dwproton-11.0-12
/home/max/.local/share/Steam/compatibilitytools.d/DW-Proton Latest/files/share/fonts/
/home/max/.local/share/Steam/compatibilitytools.d/DW-Proton Latest/files/lib/
/home/max/.local/share/Steam
...
```

So `PROTON_DIR` = line 2 with the trailing `files/share/fonts/` stripped, and line 4 is `STEAM_COMPAT_CLIENT_INSTALL_PATH` handed to you directly — use it rather than guessing the Steam root. Users run dwproton, GE-Proton, Valve Proton, proton-cachyos; this machine carries 6 custom builds in `compatibilitytools.d` (`DW-Proton Latest`, `GE-Proton9-20`, `GE-Proton10-25`, `GE-Proton10-34`, `GE-Proton11-5-x86_64`, `proton-cachyos-11.0-20260703-slr-x86_64`) plus the Valve builds under `steamapps/common`. Also handle **spaces in the path** (`DW-Proton Latest`); quote everywhere. Note `~/.steam/steam` is a symlink to `~/.local/share/Steam` here, so de-duplicate resolved library paths or you will scan the same tree twice.

**Fallbacks, in order:**
1. **SteamLinuxRuntime entry point** — needed where host libs are too old for `proton` to run directly (expect this on NixOS), **and the likely primary method if [GATE-1b] fails**, since it puts the shim in the same container the game runs in. The toolmanifest declares `require_tool_appid 4183110` → `SteamLinuxRuntime_4` (installed at `steamapps/common/SteamLinuxRuntime_4`, verified):
   ```sh
   "$STEAM_ROOT/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point" \
       --verb=run -- "$PROTON_DIR/proton" run 'C:\okww-input-shim.exe'
   ```
   Implement **both** paths in the launcher and try the container entry point automatically when the direct `proton run` produces no handshake file within the connect timeout. Do not make the user choose.
2. **protontricks** (present on this machine): `protontricks -c 'wine C:\okww-input-shim.exe' 3513350`
3. **Steam launch-option wrapper** starting the shim alongside the game.

**Shim placement.** Copy the exe into the prefix (`$COMPATDATA/pfx/drive_c/`) and reference it as a DOS path, or map it through `Z:\`. The verified run used `C:\shim.exe`.

**Caution — prefix upgrades.** The first `proton run` against a prefix whose recorded version differs triggers `Proton: Upgrading prefix from X to Y`. Against the game's prefix with the *same* build this is a no-op, but launching the shim with a **different** Proton build than the game was last run with will rewrite the prefix. **Always resolve `$PROTON_DIR` from that prefix's own `config_info`** — never from a default or a user setting that might drift.

**Remaining gates before Phase 4 Linux-side code — [GATE-1b] then [GATE-2]:**
1. Launch WW through Steam normally; reach a state with the game window up.
2. Launch the shim with the direct `proton run` invocation above. If no handshake file appears, retry through `_v2-entry-point` (fallback 1). **Which of the two works is [GATE-1b]; record the answer, the launcher must implement it.**
3. Send `FINDWIN` — must return a non-zero HWND for `Client-Win64-Shipping.exe`. A failure here means the shim started but is in a *different* wineserver: still [GATE-1b], not [GATE-2].
4. Send `GEOM` — must return plausible client geometry.
5. With focus on another window, send a harmless key (e.g. the map key) and confirm the game reacts. **This is [GATE-2] proper.**

Steps 2–3 are [GATE-1b]; step 5 is [GATE-2]. Note the shim reports over its socket, not stdout **[V12]** — a silent exit 0 is indistinguishable from success without the handshake file.

#### 4c. `WinePostMessageInteraction` (Linux side)

New file `ok/device/interaction_methods/wine_post_message.py`, subclassing `BaseInteraction`. Port `PostMessageInteraction` method-for-method (`send_key`, `send_key_down`, `send_key_up`, `input_text`, `move`, `click`, `right_click`, `mouse_down`, `mouse_up`, `swipe`, `scroll`, `activate`, `deactivate`, `try_activate`), with each `self.post(...)` replaced by a shim command.

- Reuse `vk_key_dict` from `ok/device/interaction_methods/keys.py` — but that module does `import win32con` at module level. Extract the pure key table into `keys_common.py` (no Win32 import) and have both platforms use it. The VK codes are plain integers; nothing Windows-specific about the data.
- `VkKeyScan` (used by `get_key_by_str` for characters outside the table) has no Linux equivalent — add a `VKKEYSCAN <char>` shim command and cache results, or precompute an ASCII table. Caching matters: a network round-trip per keypress is unacceptable in combat loops.
- **Persistent connection, not per-command.** Combat sends keys at high frequency. Keep one socket open, `TCP_NODELAY` on, auto-reconnect with backoff on drop.
- **Make the hot path fire-and-forget; only four commands need a reply.** Upstream's `post()` (**`post_message.py:91-97`** — earlier drafts said 85-92) swallows every exception and returns nothing — no caller ever reads a result from a `PostMessage`. So `KEYDOWN`/`KEYUP`/`CHAR`/`MOUSEMOVE`/`*DOWN`/`*UP`/`WHEEL`/`ACTIVATE` should be written to the socket and **not** waited on. Only `FINDWIN`, `GEOM`, `GETCURSOR`, `VKKEYSCAN` (and `PING`) are request/response. This removes the round-trip from every combat keypress and from `swipe`, which issues up to 100 `move()` calls back-to-back. Errors surface through `PING` and the shim's status file, matching upstream's error semantics exactly. Log and count write failures rather than raising.
- **`update_mouse_pos` collapses to the identity on Linux — do not proxy it to the shim.** Upstream (`post_message.py:185-236`) does `ClientToScreen(base_hwnd, …)` → picks a child from `hwnd_window.hwnds` by hit-test → `ScreenToClient(target, …)`. With `hwnds == []` and `top_hwnd == hwnd` (Phase 2 — Wine gives one X toplevel), `target_hwnd == base_hwnd` and the two conversions cancel. **Keep the `-1` branch — it is not optional:** `click(x=-1, y=-1)`, `right_click(-1, -1)` and `mouse_down(-1, -1)` all take it, and it must reuse the cached position *without* overwriting it.
  ```python
  def update_mouse_pos(self, x, y, activate=True):
      self.try_activate()
      if x == -1 or y == -1:
          x, y = getattr(self, 'bg_mouse_pos', (0, 0))
      else:
          x, y = self.hwnd_window.get_top_window_cords(x, y)   # top_offset_* are 0
          self.bg_mouse_pos = (x, y)
      return (int(y) << 16) | (int(x) & 0xFFFF)   # == win32api.MAKELONG(x, y)
  ```
  `_dynamic_target_hwnd` can be dropped: with `hwnds == []` it is always `base_hwnd`, and the `hwnd` property already falls back to `top_hwnd or hwnd`. Proxying any of this would add a blocking round-trip to every mouse move for a guaranteed no-op.
- Reproduce the `try_activate()` call sites exactly — `send_key_down`, `input_text`, `scroll`, `update_mouse_pos` all call it in the original. Skipping it will cause intermittent input loss. Since `ACTIVATE` is fire-and-forget this costs one small write. Upstream's `try_activate` posts to `hwnd_window.hwnd` and, if different, to the current `hwnd`; on Linux those are the same window, so one `ACTIVATE` per call.
- Also port `should_capture()` → `True` and the `hwnd` property; `BaseInteraction` defines neither, and `TaskExecutor` reads `should_capture`.
- Implement `get_cursor_pos()` / `set_cursor_pos()` on the interaction interface (see Phase 5).
- **Two upstream bugs you will inherit if you port verbatim. Fix both in the Linux backend; leave the Windows original untouched.**
  1. `swipe`: `steps = int(duration / 100)` with the default `duration=3` gives `steps == 0` → `ZeroDivisionError` on `dx / steps` (`post_message.py:112` and `:115`). Guard with `steps = max(1, int(duration / 100))`.
  2. `mouse_up`: it posts at `win32api.MAKELONG(self.mouse_pos[0], self.mouse_pos[1])` (`post_message.py:245-246`), but `self.mouse_pos` is set to `(0, 0)` at `post_message.py:20` and **never written again** — only `bg_mouse_pos` is updated, by `update_mouse_pos` (`:194`). So every drag and swipe releases the button at client `(0, 0)`. Use `bg_mouse_pos` in the Linux backend, and add a unit test pinning the release coordinate.

Register in `interaction_methods/__init__.py` and in `DeviceManager`'s selection chain — **in both places**: the constructor ladder (`DeviceManager.py:107-119`) *and* the one in `set_interaction()` (`def` at `DeviceManager.py:593`, ladder at `:606-620`), which repeats it for runtime switching from the GUI picker.

```python
elif selected_interaction == 'WinePostMessage':
    self.win_interaction_class = WinePostMessageInteraction
```

Cheaper alternative that avoids touching `DeviceManager` at all: both ladders accept a **class** and pass it through — the constructor's is `elif selected_interaction: self.win_interaction_class = selected_interaction` (`DeviceManager.py:116-117`), and `set_interaction`'s is `elif interaction and interaction != 'PyDirect':` (`DeviceManager.py:617-618`), which is not the same expression but has the same effect for a class object. Better still, **both ladders already resolve a saved config string back to a class object** by matching `item.__name__` against it (constructor `:98-105`, `set_interaction` `:596-604`), so a class entry survives a save/reload round-trip through `self.config['interaction']`. `available_interaction_methods()` (`:564-573`) renders such an entry via `method_name()` (`__name__`). So `config['windows']['interaction'] = [WinePostMessageInteraction, 'Pynput']` works with zero upstream edits. Prefer this if rebase cost dominates.

#### 4d. Foreground-only fallback — use `PynputInteraction`, write no new class [V20]

If [GATE-2] fails, the port degrades to foreground-only play. **You do not need to build a backend for that.** `PynputInteraction` already ships in ok-script, has no module-level Windows imports, and `pynput` on Linux injects through **XTEST** — precisely the transport an `X11SendEventInteraction` would have hand-rolled, but with correct modifier and auto-repeat handling and no `xdotool` subprocess. Its `clickable()` calls `hwnd_window.is_foreground()`, which Phase 2 supplies.

The whole fallback is one config entry:

```python
config['windows']['interaction'] = ['WinePostMessage', 'Pynput']
```

`ok/ui/qt/start/SelectInteractionListView.py:22` reads exactly this key (`windows_capture_config.get('interaction', [])`), so listing both is all the GUI picker needs to switch at runtime. Note it normalises a bare string with `if isinstance(methods, str): methods = [methods]` (`:23-24`) — so a string is *not* rejected; the list is needed simply because you want **two** entries to choose between.

One cosmetic wart to expect: `PynputInteraction.__init__` calls `is_admin()`, which on Linux hits `ctypes.windll.shell32` inside a bare `except` and returns `False`, so it logs `You must be an admin to use PynputInteraction` once and then works normally. Either give `is_admin()` a Linux branch (`os.geteuid() == 0`) or suppress the message; do not treat it as a failure.

Do **not** implement `X11SendEventInteraction`. `XSendEvent` **[V4][V5]** is strictly worse than XTEST — it depends on the client honouring `send_event`-flagged records — and everything it would buy you is already in `pynput`. **[V4]** and **[V5]** remain in §2 as the evidence for *why* the Linux-side injection path cannot do background play; they are no longer a build instruction.

A `uinput` backend is a third option (`/dev/uinput` is writable without root here **[V9]**), but it is strictly worse than XTEST for this use case — fully global, steals the physical keyboard — so implement it only if both others fail.

### Phase 5 — ok-ww repo changes

**5a. `config.py` — game discovery.** Replace the `winreg` functions (`_find_most_recently_run_pc_exe`, `_find_pc_exe_from_registry`, `_read_registry_value`) with a platform branch. Keep the Windows path intact for upstream parity.

Note `import winreg` in `config.py` is already **inside** those functions (lines 15 and 46), so `config.py` imports cleanly on Linux today — this is a behaviour change, not an import fix, and it can be done independently of Phase 1. Add:

```python
def _find_pc_exe_linux():
    # 1. Parse ~/.steam/steam/steamapps/libraryfolders.vdf for library paths
    # 2. Find appmanifest_3513350.acf, read "installdir"
    # 3. <library>/steamapps/common/<installdir>/.../Client-Win64-Shipping.exe
    # 4. Fallback: scan compatdata/3513350/pfx for the install
```

Both `libraryfolders.vdf` and `appmanifest_3513350.acf` were confirmed present **[V9]**. Do not hardcode `~/.local/share/Steam` — read the library list (this machine has both `~/.steam/steam` and `~/.local/share/Steam` pointing to the same place, and other users differ).

**5a-bis. Proton environment resolution (new module, `src/linux_steam.py` or in the fork).**

The game is launched by the user through Steam; ok-ww attaches to it. Implement one resolver used by both the game-path lookup and the shim launcher:

```python
def resolve_steam_env(appid=3513350):
    """-> steam_root, library_path, install_dir, exe_path, compatdata, proton_dir"""
    # steam_root:  ~/.steam/steam or ~/.local/share/Steam (both existed here;
    #              also check ~/.var/app/com.valvesoftware.Steam for Flatpak Steam)
    # libraries:   parse steamapps/libraryfolders.vdf -> "path" entries
    # install_dir: appmanifest_<appid>.acf -> "installdir"  (= "Wuthering Waves")
    # exe_path:    <lib>/steamapps/common/<installdir>/Client/Binaries/Win64/Client-Win64-Shipping.exe
    # compatdata:  <lib>/steamapps/compatdata/<appid>
    # proton_dir:  parse compatdata/<appid>/config_info  (line 1 = build name,
    #              later lines = absolute paths inside the tool dir)
```

Rules: never hardcode `~/.local/share/Steam`; quote paths (`DW-Proton Latest` contains a space); handle Flatpak Steam; fail with an actionable message ("game not found — launch it once through Steam") rather than a traceback. **Detect that the game is actually running** (a process whose cmdline ends in `Client-Win64-Shipping.exe`) before attempting to launch the shim.

**5b. `config.py` — device config.** Make the `windows` block platform-conditional. Keep the key name `'windows'` (renaming means touching `DeviceManager` and every downstream reader for no benefit); override the two values that matter:

Upstream `config.py:189-203` is exactly:

```python
'windows': {
    'top_hwnd_class': [...],
    'calculate_pc_exe_path': calculate_pc_exe_path,
    'exe': 'Client-Win64-Shipping.exe',
    'hwnd_class': 'UnrealWindow',
    'interaction': 'PostMessage',
    'capture_method': ['WGC', 'BitBlt_RenderFull'],
    'check_hdr': False,            # already False upstream — leave it
    'force_no_hdr': False,
    'check_night_light': True,     # this is the one that must flip
    'force_no_night_light': False,
},
```

so the Linux override is:

```python
if sys.platform == 'linux':
    config['windows']['capture_method'] = ['X11', 'X11_Composite']
    config['windows']['interaction'] = ['WinePostMessage', 'Pynput']   # [V20]
    config['windows']['check_night_light'] = False   # Windows display API
    # check_hdr is already False upstream; force_no_hdr / force_no_night_light
    # are only read when the corresponding check_* is True, so leave both alone.
```

Note the widening: upstream sets `'interaction': 'PostMessage'` — a bare **string**. `DeviceManager` accepts either, and so does the GUI's `SelectInteractionListView` (it wraps a string in a list at `:23-24`); making it a **two-element** list on Linux is what gives the user the WinePostMessage↔Pynput switch. `capture_method` is already a list upstream. Both GUI pickers read `windows_capture_config` directly, so no `DeviceManager.available_capture_methods` change is strictly needed — that method (`DeviceManager.py:540-549`) is only consumed by the web UI (`ok/ui/web/app.py:427`), and it derives its answer from the same config key.

`top_hwnd_class` (launcher/CEF dialog classes) is Windows-launcher-specific; under Proton these dialogs are also Wine windows, so leave the list in place — it is harmless if unmatched.

**5c. Cursor call sites.** Route both through the interaction backend rather than `win32api`:

- `src/combat/CombatCheck.py:223-230` — replace `win32api.GetCursorPos()` / `SetCursorPos(abs_pos)` with `self.executor.interaction.get_cursor_pos()` / `.set_cursor_pos(abs_pos)`.
- `src/task/MouseResetTask.py:38-52` — same substitution.

Add `get_cursor_pos()` / `set_cursor_pos()` to `BaseInteraction` with sensible defaults (Windows backends → `win32api`; Wine shim → `GETCURSOR`/`SETCURSOR`; others → no-op returning last known). This is a strict improvement to upstream: it removes a direct Win32 dependency from task code, and the behaviour is identical on Windows.

Update `tests/TestMouseResetTask.py:56-57` in the same commit — it patches `src.task.MouseResetTask.win32api`, which stops existing **[V1]**. Repoint it at the interaction backend's `get_cursor_pos`/`set_cursor_pos`.

`MouseResetTask` polls at 2 ms (`post_mouse_reset(0.002)`) — a shim round-trip per poll would saturate the link. `GETCURSOR` is one of the few commands that *cannot* be fire-and-forget, so add a client-side cache with a ~50 ms refresh for `get_cursor_pos()` in the Wine backend, or raise the poll interval on Linux. The task's purpose (detect a >200 px jump) tolerates 50 ms latency.

Also note the task's guard, `... and not self.hwnd.visible and ...` — with `visible` correctly meaning *foreground* **[V15]**, this fires precisely during background play. Verify it does, on the real game; it is the cheapest single confirmation that Phase 2 got `visible` right.

**5d. `pyproject.toml`.** Point `ok-script` at the fork; keep everything else.

**5e. The four repo files earlier drafts never mentioned [V26].**

- **`requirements.txt`** — a `pip-compile` lockfile with no platform markers, pinning `pywin32==311`, `pycaw==20240210`, `pydirectinput==1.0.4`, `comtypes==1.4.16`. It is what `pyappify.yml` installs, and it fails on Linux. Regenerate after Phase 1a; see the note there.
- **`pyappify.yml`** — the Windows installer manifest (`uac: true`, `use_pythonw: true`, `main_script: main.py`, `requirements: requirements.txt`, plus the two `git_url` update remotes). Leave it for the Windows build; the Linux distribution is Phase 6's AppImage/Flatpak/Nix, and the in-app updater is disabled on Linux (§6).
- **`deploy.txt`** — the file manifest the updater ships; lists `ok-ww.exe` and `pyappify`. Windows-only; not used by the Linux packaging path.
- **`setup.py`** — declares `Operating System :: Microsoft :: Windows` and runs `cythonize()` over `src/**/*.pyx`. **There are currently no `.pyx` files in the repo**, so `cythonize([])` is a no-op and `setup.py` does not need changing to build on Linux. Fix the classifier if you publish; otherwise leave it. The four `main*.py` entry points (`main.py`, `main_debug.py`, `main_web.py`, `main_web_debug.py`) are pure `from config import config; OK(config).start()` and need no changes — but `install()` from the `win32_stub` must run before their `from ok import OK`, so add it as the first line of each, or ship it as a real `sitecustomize`/`.pth` in the Linux package.

### Phase 6 — Packaging (Fedora + NixOS + others)

**Runtime dependencies** beyond Python packages:
- `libX11`, `libXext` (MIT-SHM), `libXcomposite`, `libXfixes`
- Xwayland (or a plain X11 session)
- Steam + Proton (user-provided)
- `mingw64-gcc` — build-time only; ship the prebuilt exe so runtime doesn't need it

**Fedora 44:**
```sh
sudo dnf install python3.12 libX11 libXext libXcomposite libXfixes mingw64-gcc
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .
```

**NixOS** — needs a `flake.nix`, since NixOS is not FHS and pip-installed binary wheels (PySide6, OpenCV, OpenVINO, onnxruntime) will not find their loaders:

- Provide a dev shell with `pkgs.python312`, the X11 libs, and `pkgs.pkgsCross.mingwW64.stdenv.cc` for the shim.
- Wrap binary wheels with `autoPatchelfHook`, **or** — far simpler and strongly recommended for v1 — use `pkgs.buildFHSEnv` so upstream wheels work unmodified. OpenVINO + onnxruntime + PySide6 under pure nixpkgs Python packaging is a large, ongoing maintenance burden that is not worth carrying to get this working.
- Expose an `okww` package plus a `devShell`. Do not attempt to package Proton — reference the user's Steam install.

**Distro-neutral requirements (do not violate these):**
- No hardcoded paths. Use `XDG_RUNTIME_DIR`, `XDG_DATA_HOME`, and the Steam library VDF.
- No assumption of a specific Wine/Proton build — read `config_info`.
- No assumption of `/dev/uinput` (needed only by the optional third fallback).
- Detect X11 vs Wayland at runtime; if `DISPLAY` is unset and no Xwayland is present, fail with an actionable message rather than a traceback.
- Do not assume ImageMagick/xdotool/wmctrl at runtime — those were diagnostic tools. Talk to X11 through python-xlib in the shipped code **for the window layer**, and through `ctypes` bindings to `libX11`/`libXext` for the pixel layer — python-xlib has no MIT-SHM **[V13]**. Both need `libX11.so.6`/`libXext.so.6` present at runtime; on NixOS that means they must be in the FHS env or `autoPatchelf` closure, not merely in the dev shell.

### Phase 7 — Testing

- **Keep `tests/` green.** They cover template matching and combat logic and are platform-neutral; they must pass unchanged on Linux. Note `run_tests.ps1` is PowerShell — add `run_tests.sh`.
- **New unit tests:** coordinate math (`get_abs_cords`, `get_capture_origin`, `get_top_window_cords`) against the Windows implementations' expected values; shim protocol parsing (fake socket, no Wine needed). Add four regression tests for the defects this audit found, because every one of them fails silently:
  - `find_hwnd` on Linux returns non-zero `real_width`/`real_height` for a matched window **[V18]**.
  - `update_mouse_pos(-1, -1)` reuses `bg_mouse_pos` and does not overwrite it.
  - `mouse_up()` releases at the last `bg_mouse_pos`, not `(0, 0)`.
  - `X11Window.pos_valid` is False when the window is Iconic even though its geometry is still on-screen.
  - **`isinstance(vk_key_dict['F1'], int)`** — pins the `win32con` constants module **[V25]**. Without it, a `_Missing` `win32con` makes every virtual-key code a stub object and the shim silently receives garbage; nothing else in the suite would notice.
  - `ok/util/window.py` exports all 11 names of **[V24]** (`for n in (...): assert hasattr(mod, n)`). This is what catches the `WINDOWS_BUILD_NUMBER`-class failure, which otherwise surfaces as an `ImportError` from an unrelated module.
- **New import test, runs everywhere:** `tools/check_linux_imports.py` from Phase 1, as a pytest case, plus `tools/scan_module_level_win32.py` asserting `TOTAL == 27` and an empty `CALLED-AT-IMPORT` delta. Together they are the only thing that catches an upstream rebase adding a 28th module-level `win32` import, or a new module-level DLL load that breaks the stub **[V21]**.
- **New integration test, no game required:** the notepad harness from this session — launch `wine notepad` in a throwaway prefix, run the shim, assert text lands while unfocused. This is a genuine regression test for the whole input path and runs in CI with `wine` + `Xvfb`.
- **Capture benchmark — [GATE-3, resolved [V14]]:** the standalone numbers are in. Re-run the same measurement against the *real game window* once it is up — a DXVK/Vulkan-presented surface is not the same object as a plain X client's — and keep the benchmark as a regression test. Budget: ≤5 ms/frame at 1080p. Also add `run_tests.sh` (upstream ships only `run_tests.ps1`, PowerShell).

---

## 5. Verification gates — do not skip

| Gate | Question | Blocks | If it fails |
|---|---|---|---|
| ~~GATE-1~~ | ~~Does a second `proton run` join an existing Proton wineserver?~~ | — | **RESOLVED — passes, host-side. See [V10].** Separate `proton run` invocations share a wineserver; PostMessage crosses. Scope limit: both processes were outside the SLR container — see GATE-1b. |
| **GATE-1b** | Does a host-side shim join the wineserver of a game Steam launched **inside** the SteamLinuxRuntime_4 container? | everything downstream | **[V19]** — untested; the toolmanifest declares `require_tool_appid 4183110`. If it fails, launch the shim through `_v2-entry-point` (§4b fallback 1) so it lands in the same container. If *that* also fails, fall back to protontricks, then to a Steam launch-option wrapper that starts the shim alongside the game. |
| **GATE-2** | Does **Wuthering Waves** (Unreal, likely RawInput/DirectInput) respond to `PostMessage` under Wine as it does on Windows? | background input | Upstream ships `PostMessage` as WW's default on Windows, so the Win32 path is known-good there; the risk is Wine's translation. If it fails, test `ForegroundPostMessage`, then fall back to `Pynput` (§4d **[V20]**), then uinput. |
| ~~GATE-3~~ | ~~Can X11 capture sustain the needed frame rate at 1080p?~~ | — | **RESOLVED — passes with large margin. See [V14].** `XShmGetImage` 1.24 ms + `cv2.cvtColor` 0.15 ms ≈ 700 fps at 1080p; even plain `XGetImage` gives 73 fps. Re-measure against the real game window (Vulkan/DXVK-backed surfaces may differ from a plain X client), but this is no longer a design risk. |
| **GATE-4** | Does OpenVINO/onnxocr run acceptably on Linux? | OCR-dependent tasks | Set `use_openvino: False` to fall back to onnxruntime CPU; `use_npu: True` is Windows-NPU-oriented — expect to disable it. `use_openvino` also selects `OpenVinoYolo8Detect` vs `OnnxYolo8Detect` in `src/globals.py:21`, so flipping it changes the echo detector too — benchmark both. |

**GATE-1b and GATE-2 are the two things standing between this plan and confirmed background operation, in that order.** Both are answered by one spike session — the shim plus a running game, a few hours. Do it first, before building out Phases 2–3: every remaining design choice is downstream of the answers. GATE-1b failing changes *how* the shim is launched (§4b fallback 1); GATE-2 failing switches the project to the foreground-only fallback (§4d), which is now a config entry rather than a build.

---

## 6. Known losses and degradations

Be explicit with users; do not silently no-op:

| Feature | Status on Linux |
|---|---|
| Game audio mute-on-background (`pycaw`) | **Recoverable — implement it, don't stub it.** Upstream's `get_mute_state`/`set_mute_state` (`hwnd_window.py:414-446`) already import pycaw *inside* the function; only the module-level `win32process` needs guarding. Both `pactl` and `wpctl` are present on this machine (verified). The Linux equivalent is a direct match: WW under Proton owns a PipeWire/PulseAudio **sink-input**, so `pactl list sink-inputs` → match `application.process.id` against the Wine PID you already resolved via `_NET_WM_PID` **[V8]** → `pactl set-sink-input-mute <id> 1/0`. Same per-application granularity, same call sites, no GUI change. Fall back to stubbing only if `pactl`/`wpctl` is absent. |
| Global start/stop and debug hotkeys | **At risk — not previously listed [V16].** `ok/ui/qt/start/StartCard.py:124,137` and `ok/ui/qt/debug/DebugTab.py:117,135,137` use `windll.user32.RegisterHotKey` + a `PeekMessageW` pump. Replace with an X11 `XGrabKey` on the root window via python-xlib (works while the game has focus, which is the point of a hotkey), or accept the loss and disable the hotkey config rows. Do not leave the stub raising here — it is on a GUI thread. |
| Overlay window (`ok/ui/overlay/win32_gdi.py`) and template thumbnails (`ok/ui/qt/util/windows_thumbnail.py`) | **Lost, but free — and NOT import-time hazards [V23].** Earlier drafts were wrong about these: upstream already wraps all Win32 code in `if os.name == "nt":` (`win32_gdi.py:22`, with `if os.name != "nt":` fallbacks at `:209`, `:221`, `:1007`) and `if sys.platform == 'win32':` (`windows_thumbnail.py:14`). `import ok.ui.overlay` succeeds on Linux with **no stub at all** — verified by executing it. `WindowsThumbnailReader.open()` already returns `False` on non-win32 at `windows_thumbnail.py:125-126`, which is exactly the fallback `TemplateTab` (`:227-228`) needs. **Budget zero work here.** |
| HDR / Night Light detection (`check_hdr`, `check_night_light`) | **Lost.** Windows display-API concepts. Set both `False`. |
| Windows notifications (`windows_messenger`, `notification/system.py`) | Replace with `notify-send`/D-Bus, or no-op. |
| `pyappify` installer + auto-update (`update_pyappify` in `config.py`) | **Not applicable.** The `zip_url` points to `ok-ww-win32.zip`. Disable the updater on Linux; distribute via AppImage/Flatpak/Nix. |
| `windows_schedule.py` (task scheduler) | Replace with systemd user timers, or drop. |
| Minimizing the game window | **Unsupported** — capture fails when Iconic **[V7]**. Occlusion is fine; minimizing is not. Detect and warn. |
| Emulator/ADB backends | Unaffected — `adb.py`, `nemu_ipc.py`, `image.py` and their interaction counterparts have no module-level Windows imports **[V16]**. Cheap to verify, keep working. |
| Browser (cloud game) backend | **Keep working, and it is nearly free [V22].** `ok/device/capture_methods/browser.py` is in [V16] group A: module-level `import win32gui`, `from ok.util.window import resize_window, windows_graphics_available, find_hwnd` (`:11`) and `from ok.device.capture_methods.windows_graphics import WindowsGraphicsCaptureMethod` (`:15`). It cannot be guarded out — `BrowserCaptureMethod` is in `_LAZY_IMPORTS`, `DeviceManager` imports it at module level, and `do_update_window_size` isinstance-checks against it on every poll (`hwnd_window.py:236-239`). But it imported cleanly in the measurement with only the stub + the Phase 2 `ok/util/window.py`; no per-file work needed. |
| Whole-desktop capture (`DesktopDuplication`/DXGI) | Not ported; unnecessary (per-window capture is the correct model) and unavailable under rootless Xwayland **[V7]**. |

---

## 7. Effort estimate

| Phase | Estimate |
|---|---|
| 0–1 — fork, markers (incl. ok-ww's `requirements.txt`), `win32_stub` + the 94-constant `win32con` ([V21][V25]). **No aggregator guards — [V22] measured them away**, so this is smaller than earlier drafts assumed | **0.5–1 day** |
| **GATE-1b + GATE-2 spike** (GATE-1 host-side and GATE-3 already resolved) | **0.5 day — do this first** |
| 2 — `X11Window` **+ all 11 `ok/util/window.py` contracts [V17][V24]**. `browser.py` needs no per-file work **[V22]** | 2–3 days |
| 3 — `X11CaptureMethod` (ctypes X11/XShm, benchmark) | 1–2 days |
| 4 — shim + `WinePostMessageInteraction` (fallback is now config-only, **[V20]**) | 2–3 days |
| 5 — ok-ww repo changes | 1 day |
| 6 — Fedora + NixOS packaging | 2–3 days |
| 7 — tests, live debugging against the game | open-ended |

Roughly **2–3 weeks** to a solid port, with a usable foreground-only build reachable in about one week.

---

## 8. Notes for the implementer

- **Read before writing.** `ok/device/capture_methods/hwnd_window.py`, `ok/device/interaction_methods/post_message.py`, `ok/device/capture_methods/update.py`, `ok/util/window.py`, and `ok/device/capture_methods/base.py` define every contract you are implementing against. Read `ok/device/capture.py` and `ok/device/interaction.py` too — they are two-line shims, but they are what `DeviceManager` and `_LAZY_IMPORTS` actually go through, so a guard that misses them accomplishes nothing. The Linux versions should read as siblings of the Windows ones.
- **`BaseCaptureMethod.get_frame` already does the work you might be tempted to duplicate** (`base.py:31-44`): it checks `exit_event`, drops frames `<= 10px` on either axis, updates `self._size`, slices `frame[:, :, :3]` if the frame still has 4 channels, and wraps everything in `CaptureException`. Implement only `do_get_frame`.
- **Verify the version before trusting a line number.** Every `file:line` in this plan is against ok-script **2.0.5**; see the appendix for how to fetch that exact tree. Line numbers in earlier drafts of this document were off by a few in several places (`make_lparam`, `post()`, `visible = …`, `base.py`); the ones here were re-checked against the source on 2026-09-01, but a rebase invalidates them.
- **Do not refactor upstream ok-script beyond the guards.** Every unnecessary change costs you on the next rebase.
- **Preserve timing.** `post_message.py` has deliberate `time.sleep` calls (`down_time=0.01` between key down/up, `0.01` between chars, 100-step swipe interpolation). The game is timing-sensitive; keep these values, and do not let network latency silently extend them — measure round-trip time and log if it exceeds the intended sleep.
- **Ban risk: not measurably changed, but do not claim parity.** What the game receives is identical to the Windows build — synthesized `PostMessage` input, same messages, same lparams. WW runs Anti-Cheat Expert, and the project's own README already warns that use may result in account bans. But the *process topology* is not identical: upstream posts from a separate native Windows process, whereas this port runs a foreign PE (`okww-input-shim.exe`) inside the **same wineserver session and prefix as ACE**. Whether that is more visible to ACE is unverified, and this plan contains no evidence either way. Tell users the risk is at least as high as upstream's, never that Linux is "safer" — nothing here evades or interferes with anticheat, by design.
- **Proton breaks WW periodically.** The game is not officially supported on desktop Linux; community Proton builds carry the fixes — this machine runs **dwproton-11.0-12**, and has 12 Proton builds installed side by side. Read the build from `config_info` at runtime and surface it in logs and bug reports; most user issues will be Proton-version-related, not ok-ww bugs. Never assume Valve Proton, and never assume one build.
- **The game is launched by the user through Steam**, not by ok-ww. Design the attach flow accordingly: poll for the game process/window, attach when it appears, degrade cleanly when it vanishes (the user alt-F4s, Proton crashes). Do not attempt to launch the game yourself — `config.py`'s `calculate_pc_exe_path` exists for Windows launch support; on Linux, treat the exe path as identification data only.

---

## Appendix — reproducing the spikes

Artifacts from these sessions live in the scratchpad (session-scoped; recreate as needed). The one exception is `shim/spike-notepad.c`, which is committed in this repo.

**Getting the ok-script source.** Every file:line reference in this plan is against **ok-script 2.0.5**, and you will be reading it constantly (§8). It is a pure-Python wheel, so:

```sh
python3.12 -m pip download ok-script==2.0.5 --no-deps -d /tmp/oks
cd /tmp/oks && unzip -q ok_script-2.0.5-*.whl -d okx      # -> /tmp/oks/okx/ok/...
find okx/ok -name '*.py' | wc -l      # 255  [V2]
```

Confirm the version before trusting any line number: `cat okx/ok_script-2.0.5.dist-info/METADATA | head`.

**Wine accepts synthetic X events [V4]:**
```sh
WINEPREFIX=/tmp/spikeprefix WINEDEBUG=+key wine notepad &
xdotool key --window $(xdotool search --class notepad | head -1) a
grep X11DRV_send_keyboard_input wine.log     # -> event reached the Win32 queue
```

**PostMessage works unfocused [V6]:** the proof-of-concept is committed as **`shim/spike-notepad.c`** (not `okww-input-shim.c` — that is the Phase 4a file you are going to write). Build it with
`x86_64-w64-mingw32-gcc -O2 -o shim.exe shim/spike-notepad.c`, launch `wine notepad`,
focus a different window, run `wine shim.exe`, then
`import -window <notepad-win> out.png` and confirm the injected text is present.

**Capture behaviour [V7]:**
```sh
import -window <win> a.png     # works; occluded == unoccluded
xdotool windowminimize <win>
import -window <win> b.png     # fails — Iconic
```

**Proton wineserver sharing + cross-process PostMessage [V10]** — the important one.
Uses a scratch prefix, so it never touches the game's:
```sh
export STEAM_COMPAT_DATA_PATH=/tmp/protontest
export STEAM_COMPAT_CLIENT_INSTALL_PATH=~/.local/share/Steam
P="$HOME/.local/share/Steam/compatibilitytools.d/DW-Proton Latest"

"$P/proton" run 'C:\windows\system32\notepad.exe' &        # process A
cp shim.exe "$STEAM_COMPAT_DATA_PATH/pfx/drive_c/"
xdotool windowfocus <some-other-window>                     # A must NOT be focused
"$P/proton" run 'C:\shim.exe'                               # process B, separate call

# find A's window by _NET_WM_PID (NOT by class — all Proton windows are "steam_proton")
wmctrl -l
import -window <A-win> out.png   # injected text present -> wineserver shared, PostMessage crossed
```
Cleanup: `STEAM_COMPAT_DATA_PATH=/tmp/protontest "$P/files/bin/wineserver" -k`

**python-xlib has no MIT-SHM [V13]:**
```sh
python3.12 -m venv /tmp/x && /tmp/x/bin/pip -q install python-xlib
/tmp/x/bin/python -c "from Xlib.ext import shm"
# ImportError: cannot import name 'shm' from 'Xlib.ext'
/tmp/x/bin/python -c "import Xlib.ext,pkgutil; print([m.name for m in pkgutil.iter_modules(Xlib.ext.__path__)])"
# ['composite','damage','dpms','ge','nvcontrol','randr','record','res',
#  'screensaver','security','shape','xfixes','xinerama','xinput','xtest']
```

**Capture throughput [V14]:** create a 1920×1080 Xwayland toplevel (`Xlib` `create_window` + `map`, or any real window), then ctypes-bind `libX11`/`libXext` and time `XGetImage` vs `XShmGetImage` over ≥100 iterations, plus the four BGRA→BGR conversion variants over a `(1080,1920,4)` uint8 array. Results on this machine are tabulated in §2 V14. Gotcha that will cost you an hour: `XDestroyImage` is a macro — call `img.contents.f.destroy_image` via `CFUNCTYPE`, and lay out `XImage`'s trailing `funcs` struct as exactly six `c_void_p`, or you get a segfault instead of an error.

**`visible` is a foreground test, not a mapped test [V15]:**
```sh
grep -n "visible = self.is_foreground\|def is_foreground" ok/device/capture_methods/hwnd_window.py
grep -n "not self.hwnd.visible" src/task/MouseResetTask.py
```

**`find_hwnd`'s `real_*` defaults [V18]:**
```sh
grep -n "x_offset, y_offset, real_width, real_height = " ok/util/window.py
# ok/util/window.py:429:    x_offset, y_offset, real_width, real_height = 0, 0, biggest[2], biggest[3]
grep -n "hwnds = find_hwnd" ok/device/DeviceManager.py     # positions 5,6 become device width/height
```

**`PynputInteraction` is Linux-clean [V20]:**
```sh
grep -nE "^(import|from) (win32|pydirectinput)" ok/device/interaction_methods/pynput.py   # no output
grep -n -A5 "def is_admin" ok/util/process.py    # windll inside a bare except -> False on Linux
```

**Missing Linux `ctypes` symbols [V16]:**
```sh
python3.12 -c "from ctypes import windll"
# ImportError: cannot import name 'windll' from 'ctypes'
python3.12 -c "import winreg"
# ModuleNotFoundError: No module named 'winreg'
python3.12 -c "import ctypes; print(hasattr(ctypes,'HRESULT'), hasattr(ctypes,'WINFUNCTYPE'))"
# False False
python3.12 -c "from ctypes import wintypes; print('wintypes is fine')"
```

**Regenerating the [V16] offender list.** Do this after every upstream rebase; grep is not good enough, because it cannot tell a module-level import from one inside a function. **Use the version below, not the one earlier drafts shipped** — that one descended into upstream's own platform guards and counted assignment targets, and printed 30 instead of 27 **[V23]**.

```python
# tools/scan_module_level_win32.py — run against the ok-script source tree
import ast, os

WIN_MODS = {'win32api','win32con','win32gui','win32process','win32ui','win32clipboard',
            'win32file','pydirectinput','pycaw','comtypes','pythoncom','winreg','d3dshot'}
CTYPES_MISSING = {'windll','WinDLL','oledll','OleDLL','HRESULT','WINFUNCTYPE'}
PLATFORM_SRC = ('sys.platform', 'os.name', 'platform.system')
LOADERS = ('windll', 'oledll', 'WinDLL', 'OleDLL')


def is_platform_guard(test):
    return any(s in ast.unparse(test) for s in PLATFORM_SRC)


def scan(body, hits, called):
    for node in body:
        # function/method/class bodies are lazy -> harmless on Linux until called
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        # upstream's own `if sys.platform == 'win32':` blocks never execute on Linux
        if isinstance(node, ast.If) and is_platform_guard(node.test):
            continue
        if isinstance(node, ast.Try):          # already tolerated by the author
            continue
        if isinstance(node, ast.Import):
            hits |= {a.name for a in node.names if a.name.split('.')[0] in WIN_MODS}
        elif isinstance(node, ast.ImportFrom):
            if (node.module or '').split('.')[0] in WIN_MODS:
                hits.add(node.module)
            if node.module == 'ctypes':
                hits |= {'ctypes.' + a.name for a in node.names if a.name in CTYPES_MISSING}
        for x in ast.walk(node):
            if isinstance(x, ast.Call):
                f = ast.unparse(x.func)
                if any(f.startswith(p) or ('.' + p) in f for p in LOADERS):
                    called.add(f)              # <- these break a naive stub [V21]
            if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) \
                    and x.value.id == 'ctypes' and x.attr in CTYPES_MISSING:
                hits.add('ctypes.' + x.attr)
            elif isinstance(x, ast.Name) and x.id in CTYPES_MISSING \
                    and not isinstance(getattr(x, 'ctx', None), ast.Store):
                hits.add(x.id)                 # Store excludes `HRESULT = LONG`


total = 0
for root, _, files in os.walk('ok'):
    for f in sorted(files):
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        hits, called = set(), set()
        scan(ast.parse(open(p, encoding='utf-8').read()).body, hits, called)
        if hits or called:
            total += 1
            extra = f'   CALLED-AT-IMPORT:{sorted(called)}' if called else ''
            print(f'{p:60s} {" ".join(sorted(hits))}{extra}')
print('TOTAL', total)
```

On ok-script 2.0.5 this prints exactly the **27** modules tabulated in **[V16]**, and flags the **4** that call a DLL loader at import time (`ok/util/window.py`, `ok/rotypes/roapi.py`, `ok/rotypes/winstring.py`, `ok/rotypes/Windows/Foundation/__init__.py`) — the ones that break the naive stub **[V21]**. If the `TOTAL` changes after a rebase, or a new module appears in the `CALLED-AT-IMPORT` column, the stub needs revisiting before anything else.

**Reproducing the Phase-1 measurement [V21][V22].** This is worth re-running once at the start of implementation; it takes about two minutes and it is what proves the aggregators need no guards.

```sh
# 1. get the ok-script 2.0.5 source (the wheel is pure Python; no build needed)
python3.12 -m pip download ok-script==2.0.5 --no-deps --no-binary :none: -d /tmp/oks
cd /tmp/oks && unzip -q ok_script-2.0.5-*.whl -d okx        # -> /tmp/oks/okx/ok/...

# 2. a venv with the cross-platform deps only (no PySide6 needed for the device layer)
python3.12 -m venv /tmp/okvenv
/tmp/okvenv/bin/pip -q install numpy opencv-python-headless psutil Pillow \
    python-xlib pynput typing-extensions requests darkdetect mouse

# 3. install the corrected win32_stub, stand in for ok/util/window.py with its
#    11 names [V24], then import the device layer and resolve every _LAZY_IMPORTS entry.
PYTHONPATH=/tmp/oks/okx /tmp/okvenv/bin/python your_check.py
```

Expected: `ok.device.capture_methods`, `ok.device.interaction_methods`, `ok.device.capture`, `ok.device.interaction` and `ok.device.DeviceManager` all import, and `LAZY FAILURES: 1` — `MainWindow`, on `No module named 'pyappify'`. Without the `ok/util/window.py` stand-in, every one of them fails with the same error: `NotImplementedError: Windows-only symbol called on Linux: ctypes.WinDLL` (from `ok/util/window.py:18`).


**GATE-1b — the container boundary [V19]:**
```sh
cat "$HOME/.local/share/Steam/compatibilitytools.d/DW-Proton Latest/toolmanifest.vdf"
#   "require_tool_appid" "4183110"   ← SteamLinuxRuntime_4
#   "use_sessions"       "1"
ls -d "$HOME/.local/share/Steam/steamapps/common/SteamLinuxRuntime_4"

# With WW running from Steam, compare what the two sides see:
ls /tmp/.wine-$(id -u)/                      # host-visible wineserver sockets
pgrep -af Client-Win64-Shipping.exe          # confirm the game is up
# then run the shim host-side and check FINDWIN over its socket (NOT stdout [V12]).
```

**Confirming `WM_CLASS` is useless under Proton [V11]:**
```sh
xprop -id <win> WM_CLASS _NET_WM_PID
# WM_CLASS(STRING) = "steam_proton", "steam_proton"
# _NET_WM_PID(CARDINAL) = <the real Linux pid>
```
