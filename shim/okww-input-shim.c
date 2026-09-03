/* okww-input-shim -- the Wine half of ok-ww's Linux input path (PORT.md Phase 4a).
 *
 * Runs *inside* the game's Proton prefix and posts messages to the game's HWND on behalf
 * of ok-ww, which runs natively on Linux. `PostMessage` delivers to an unfocused window
 * [PORT.md V6]; nothing reachable from the Linux side does (XSendEvent is focus-bound
 * [V5], XTEST is global), which is the whole reason this program exists.
 *
 * Build:
 *     x86_64-w64-mingw32-gcc -O2 -s -mwindows -o shim/okww-input-shim.exe \
 *         shim/okww-input-shim.c -lws2_32
 *
 * `-mwindows` is not cosmetic. Without it this is a console program, and Wine gives every
 * console program a `conhost.exe` window -- a visible, focusable window on the user's
 * desktop for every shim launch, sitting in front of the game they are playing. It also
 * means nothing this program prints goes anywhere, which is correct: `proton run` swallows
 * stdout regardless [PORT.md V12], and status belongs in the handshake file and the
 * socket.
 *
 * Usage (the Linux side does this for you -- ok/compat/proton_shim.py in the fork):
 *     proton run 'C:\okww-input-shim.exe' [--exe NAME] [--class NAME]
 *                                         [--child-class NAME]
 *                                         [--handshake C:\okww-shim.port]
 *                                         [--idle-exit SECONDS]
 *
 * Protocol: ASCII, one command per line, LF-terminated, on a loopback TCP socket bound to
 * port 0 (kernel-assigned). The port and a 32-byte hex token are written to the handshake
 * file, which is inside the prefix's drive_c and therefore visible from both sides. The
 * first line a client sends must be `HELLO <token>`; anything else is dropped.
 *
 * Two rules that the Linux client depends on:
 *
 *  1. **Only reply-bearing commands reply.** The hot path (keys, mouse moves, buttons,
 *     wheel, activate, setcursor) is fire-and-forget in both directions: upstream's
 *     `PostMessageInteraction.post()` swallows every error and returns nothing, so no
 *     caller ever reads a result, and a reply nobody reads would fill the socket buffer
 *     and eventually block this process mid-combat. Errors on those commands are counted
 *     and reported by PING/STATS instead.
 *  2. **Every reply is tagged with its command** (`GEOM 0 0 2560 1440`, `ERR GEOM ...`),
 *     so a client that missed one reply -- or got an unsolicited error -- resynchronises
 *     by discarding lines until the tag matches, instead of pairing the wrong answer with
 *     the wrong question.
 *
 * Status is reported over the socket and the handshake file, never stdout: `proton run`
 * swallows stdout [PORT.md V12].
 */

#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LINE_MAX_LEN 4096
#define TOKEN_BYTES 32

static wchar_t g_exe_name[MAX_PATH] = L"Client-Win64-Shipping.exe";
static wchar_t g_class_name[128] = L"UnrealWindow";
/* Optional: post to a *child* of the resolved window instead of the window itself. The
 * game needs nothing of the sort -- Unreal's toplevel is the input target, which is what
 * upstream posts to on Windows -- but `wine notepad`, the offline test target, keeps its
 * text in an `Edit` child and drops WM_CHAR sent to the frame. Without this the notepad
 * harness "passes" on a blinking caret while no character is ever inserted. */
static wchar_t g_child_class[128] = L"";
static wchar_t g_handshake[MAX_PATH] = L"C:\\okww-shim.port";
static char g_token[TOKEN_BYTES * 2 + 1];

static HWND g_hwnd = NULL;
static DWORD g_last_resolve = 0;      /* GetTickCount of the last EnumWindows sweep */
static unsigned long long g_posts = 0;
static unsigned long long g_errors = 0;
static unsigned long long g_unauthorized = 0;

/* ---------------------------------------------------------------- token ---- */

/* RtlGenRandom, which Wine implements, with a coarse fallback. The token only has to be
 * unguessable by another local user for the lifetime of one game session. */
static void gen_token(void) {
    unsigned char buf[TOKEN_BYTES];
    int have = 0;
    HMODULE adv = LoadLibraryA("advapi32.dll");
    if (adv) {
        BOOLEAN(WINAPI * rnd)(PVOID, ULONG) =
            (BOOLEAN(WINAPI *)(PVOID, ULONG))(void *)GetProcAddress(adv, "SystemFunction036");
        if (rnd && rnd(buf, (ULONG)sizeof buf)) have = 1;
    }
    if (!have) {
        LARGE_INTEGER qpc;
        QueryPerformanceCounter(&qpc);
        unsigned long long x = (unsigned long long)qpc.QuadPart ^
                               ((unsigned long long)GetCurrentProcessId() << 32) ^
                               (unsigned long long)GetTickCount64();
        for (int i = 0; i < TOKEN_BYTES; ++i) {  /* splitmix64 */
            x += 0x9E3779B97F4A7C15ULL;
            unsigned long long z = x;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            buf[i] = (unsigned char)((z ^ (z >> 31)) & 0xFF);
        }
    }
    for (int i = 0; i < TOKEN_BYTES; ++i)
        sprintf(g_token + i * 2, "%02x", buf[i]);
    g_token[TOKEN_BYTES * 2] = '\0';
}

/* Length-independent compare, so the token cannot be probed byte by byte. */
static int token_equal(const char *given) {
    size_t want = strlen(g_token);
    size_t got = strlen(given);
    unsigned char diff = (unsigned char)((want ^ got) != 0);
    for (size_t i = 0; i < want; ++i)
        diff |= (unsigned char)(g_token[i] ^ given[i < got ? i : 0]);
    return diff == 0;
}

/* --------------------------------------------------------------- window ---- */

typedef struct {
    HWND best;
    int best_score;
    long best_area;
} FindCtx;

static const wchar_t *base_name(const wchar_t *path) {
    const wchar_t *slash = wcsrchr(path, L'\\');
    if (!slash) slash = wcsrchr(path, L'/');
    return slash ? slash + 1 : path;
}

static BOOL CALLBACK enum_proc(HWND hwnd, LPARAM lparam) {
    FindCtx *ctx = (FindCtx *)lparam;
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (!pid) return TRUE;

    HANDLE proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!proc) proc = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (!proc) return TRUE;

    wchar_t path[MAX_PATH * 2];
    DWORD len = (DWORD)(sizeof path / sizeof path[0]);
    BOOL got = QueryFullProcessImageNameW(proc, 0, path, &len);
    CloseHandle(proc);
    if (!got) return TRUE;
    if (_wcsicmp(base_name(path), g_exe_name) != 0) return TRUE;

    /* The process matches. Rank its windows: the game's real window has the right class,
     * is visible, and is the biggest -- but a window that fails one of those is still a
     * better answer than nothing, because the launcher and the game share a process
     * lineage and a splash window can be up before the Unreal window is. */
    wchar_t cls[256] = L"";
    GetClassNameW(hwnd, cls, (int)(sizeof cls / sizeof cls[0]));
    RECT rc;
    if (!GetWindowRect(hwnd, &rc)) return TRUE;
    long area = (long)(rc.right - rc.left) * (long)(rc.bottom - rc.top);
    if (area <= 0) return TRUE;

    int score = 0;
    if (g_class_name[0] && _wcsicmp(cls, g_class_name) == 0) score += 4;
    if (IsWindowVisible(hwnd)) score += 2;
    if (!GetWindow(hwnd, GW_OWNER)) score += 1;

    if (score > ctx->best_score || (score == ctx->best_score && area > ctx->best_area)) {
        ctx->best = hwnd;
        ctx->best_score = score;
        ctx->best_area = area;
    }
    return TRUE;
}

static HWND resolve_window(void) {
    FindCtx ctx = {NULL, -1, 0};
    EnumWindows(enum_proc, (LPARAM)&ctx);
    g_last_resolve = GetTickCount();
    g_hwnd = ctx.best;
    if (g_hwnd && g_child_class[0]) {
        HWND child = FindWindowExW(g_hwnd, NULL, g_child_class, NULL);
        if (child) g_hwnd = child;
    }
    return g_hwnd;
}

/* Cheap liveness check on the hot path: only sweep again when the handle actually died,
 * and at most twice a second, so a game that is shutting down cannot turn every keypress
 * into a full EnumWindows. */
static HWND live_window(void) {
    if (g_hwnd && IsWindow(g_hwnd)) return g_hwnd;
    DWORD now = GetTickCount();
    if (!g_hwnd || (DWORD)(now - g_last_resolve) >= 500) return resolve_window();
    return NULL;
}

/* ------------------------------------------------------------ handshake ---- */

/* The Linux side pre-creates this file with 0600 permissions and we truncate it in place,
 * so the token is never briefly world-readable. OPEN_ALWAYS keeps that mode; CREATE_ALWAYS
 * would too under Wine, but only because Wine maps it onto open(O_TRUNC) -- do not rely
 * on it. */
static int write_handshake(unsigned short port, int hwnd_known) {
    HANDLE fh = CreateFileW(g_handshake, GENERIC_WRITE, FILE_SHARE_READ, NULL,
                            OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (fh == INVALID_HANDLE_VALUE) return 0;

    char body[1024];
    int n = snprintf(body, sizeof body,
                     "port=%u\ntoken=%s\npid=%lu\nhwnd=%llu\nstatus=%s\n",
                     (unsigned)port, g_token, (unsigned long)GetCurrentProcessId(),
                     (unsigned long long)(ULONG_PTR)g_hwnd,
                     hwnd_known ? "ready" : "ready-nowindow");
    DWORD written = 0;
    BOOL ok = WriteFile(fh, body, (DWORD)n, &written, NULL) && written == (DWORD)n;
    SetEndOfFile(fh);
    CloseHandle(fh);
    return ok;
}

/* -------------------------------------------------------------- replies ---- */

static void send_line(SOCKET s, const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof buf - 2, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    buf[n] = '\n';
    buf[n + 1] = '\0';
    int off = 0, total = n + 1;
    while (off < total) {
        int wrote = send(s, buf + off, total - off, 0);
        if (wrote <= 0) return;
        off += wrote;
    }
}

/* --------------------------------------------------------------- posting --- */

static void post_msg(SOCKET s, const char *cmd, UINT msg, WPARAM wparam, LPARAM lparam) {
    (void)s;
    HWND hwnd = live_window();
    if (!hwnd) {
        g_errors++;
        return;
    }
    if (PostMessageW(hwnd, msg, wparam, lparam))
        g_posts++;
    else
        g_errors++;
    (void)cmd;
}

static LPARAM key_lparam(UINT vk, int is_up) {
    /* Byte-for-byte `PostMessageInteraction.make_lparam` (post_message.py:50-55). The
     * scan code must be produced *inside* Wine so it matches what the game's Unreal input
     * layer expects; do not precompute it on the Linux side. */
    UINT scan = MapVirtualKeyW(vk, 0);
    LPARAM lparam = ((LPARAM)scan << 16) | 1;
    if (is_up) lparam |= (1L << 30) | (1L << 31);
    return lparam;
}

static LPARAM point_lparam(int x, int y) {
    return (LPARAM)(((y & 0xFFFF) << 16) | (x & 0xFFFF));
}

/* -------------------------------------------------------------- commands --- */

/* Splits on spaces in place. Returns the token count. */
static int split(char *line, char **argv, int max) {
    int argc = 0;
    char *p = line;
    while (*p && argc < max) {
        while (*p == ' ' || *p == '\t') ++p;
        if (!*p) break;
        argv[argc++] = p;
        while (*p && *p != ' ' && *p != '\t') ++p;
        if (*p) *p++ = '\0';
    }
    return argc;
}

static int arg_int(char **argv, int argc, int index, int fallback) {
    if (index >= argc) return fallback;
    return (int)strtol(argv[index], NULL, 0);
}

/* Returns 0 to keep the connection, 1 to close it (QUIT), -1 to exit the process. */
static int handle_line(SOCKET s, char *line, int *authed) {
    char *argv[8];
    int argc = split(line, argv, 8);
    if (argc == 0) return 0;
    const char *cmd = argv[0];

    if (!*authed) {
        if (strcmp(cmd, "HELLO") == 0 && argc >= 2 && token_equal(argv[1])) {
            *authed = 1;
            HWND hwnd = live_window();
            send_line(s, "HELLO ok hwnd=%llu", (unsigned long long)(ULONG_PTR)hwnd);
            return 0;
        }
        g_unauthorized++;
        return 1;  /* no error reply: an unauthenticated peer learns nothing */
    }

    if (strcmp(cmd, "PING") == 0) {
        HWND hwnd = live_window();
        send_line(s, "PING pong hwnd=%llu posts=%llu errors=%llu",
                  (unsigned long long)(ULONG_PTR)hwnd, g_posts, g_errors);
    } else if (strcmp(cmd, "STATS") == 0) {
        send_line(s, "STATS posts=%llu errors=%llu unauthorized=%llu",
                  g_posts, g_errors, g_unauthorized);
    } else if (strcmp(cmd, "FINDWIN") == 0) {
        HWND hwnd = resolve_window();
        if (hwnd)
            send_line(s, "FINDWIN hwnd=%llu", (unsigned long long)(ULONG_PTR)hwnd);
        else
            send_line(s, "ERR FINDWIN notfound");
    } else if (strcmp(cmd, "GEOM") == 0) {
        HWND hwnd = live_window();
        RECT rc;
        POINT origin = {0, 0};
        if (!hwnd) {
            send_line(s, "ERR GEOM notfound");
        } else if (!GetClientRect(hwnd, &rc) || !ClientToScreen(hwnd, &origin)) {
            send_line(s, "ERR GEOM geometry");
        } else {
            send_line(s, "GEOM %ld %ld %ld %ld", (long)origin.x, (long)origin.y,
                      (long)(rc.right - rc.left), (long)(rc.bottom - rc.top));
        }
    } else if (strcmp(cmd, "WININFO") == 0) {
        /* Diagnostics: which window did this shim actually pick? Without it, a shim that
         * resolved the wrong window and one that resolved the right window look identical
         * from Linux -- both post successfully and nothing happens. */
        HWND hwnd = live_window();
        if (!hwnd) {
            send_line(s, "ERR WININFO notfound");
        } else {
            wchar_t cls[128] = L"", title[256] = L"";
            char cls8[256] = "", title8[512] = "";
            RECT rc = {0, 0, 0, 0};
            GetClassNameW(hwnd, cls, 128);
            GetWindowTextW(hwnd, title, 256);
            GetClientRect(hwnd, &rc);
            WideCharToMultiByte(CP_UTF8, 0, cls, -1, cls8, sizeof cls8, NULL, NULL);
            WideCharToMultiByte(CP_UTF8, 0, title, -1, title8, sizeof title8, NULL, NULL);
            send_line(s, "WININFO hwnd=%llu class=%s visible=%d w=%ld h=%ld title=%s",
                      (unsigned long long)(ULONG_PTR)hwnd, cls8, IsWindowVisible(hwnd) ? 1 : 0,
                      (long)(rc.right - rc.left), (long)(rc.bottom - rc.top), title8);
        }
    } else if (strcmp(cmd, "GETCURSOR") == 0) {
        POINT pt;
        if (GetCursorPos(&pt))
            send_line(s, "GETCURSOR %ld %ld", (long)pt.x, (long)pt.y);
        else
            send_line(s, "ERR GETCURSOR failed");
    } else if (strcmp(cmd, "VKKEYSCAN") == 0) {
        if (argc < 2) {
            send_line(s, "ERR VKKEYSCAN missing");
        } else {
            /* The argument is a decimal codepoint, not a raw character: a space or a
             * newline would not survive the line protocol. */
            int cp = arg_int(argv, argc, 1, 0);
            SHORT scan = VkKeyScanW((wchar_t)cp);
            send_line(s, "VKKEYSCAN %d", (int)scan);
        }
    } else if (strcmp(cmd, "SETCURSOR") == 0) {
        /* Screen coordinates, as `win32api.SetCursorPos`. Wine maps this onto
         * XWarpPointer in the game's own space -- the correct equivalent. */
        SetCursorPos(arg_int(argv, argc, 1, 0), arg_int(argv, argc, 2, 0));
    } else if (strcmp(cmd, "ACTIVATE") == 0) {
        post_msg(s, cmd, WM_ACTIVATE, WA_ACTIVE, 0);
    } else if (strcmp(cmd, "DEACTIVATE") == 0) {
        post_msg(s, cmd, WM_ACTIVATE, WA_INACTIVE, 0);
    } else if (strcmp(cmd, "KEYDOWN") == 0) {
        UINT vk = (UINT)arg_int(argv, argc, 1, 0);
        post_msg(s, cmd, WM_KEYDOWN, vk, key_lparam(vk, 0));
    } else if (strcmp(cmd, "KEYUP") == 0) {
        UINT vk = (UINT)arg_int(argv, argc, 1, 0);
        post_msg(s, cmd, WM_KEYUP, vk, key_lparam(vk, 1));
    } else if (strcmp(cmd, "CHAR") == 0) {
        post_msg(s, cmd, WM_CHAR, (WPARAM)arg_int(argv, argc, 1, 0), 0);
    } else if (strcmp(cmd, "MOUSEMOVE") == 0) {
        int x = arg_int(argv, argc, 1, 0), y = arg_int(argv, argc, 2, 0);
        post_msg(s, cmd, WM_MOUSEMOVE, (WPARAM)arg_int(argv, argc, 3, 0), point_lparam(x, y));
    } else if (strcmp(cmd, "WHEEL") == 0) {
        int x = arg_int(argv, argc, 1, 0), y = arg_int(argv, argc, 2, 0);
        int delta = arg_int(argv, argc, 3, 0);
        WPARAM wparam = (WPARAM)(DWORD)(((WHEEL_DELTA * delta) & 0xFFFF) << 16);
        post_msg(s, cmd, WM_MOUSEWHEEL, wparam, point_lparam(x, y));
    } else if (strcmp(cmd, "LDOWN") == 0 || strcmp(cmd, "RDOWN") == 0 ||
               strcmp(cmd, "MDOWN") == 0 || strcmp(cmd, "LUP") == 0 ||
               strcmp(cmd, "RUP") == 0 || strcmp(cmd, "MUP") == 0) {
        int x = arg_int(argv, argc, 1, 0), y = arg_int(argv, argc, 2, 0);
        int is_up = cmd[1] == 'U';
        UINT msg;
        WPARAM mk;
        if (cmd[0] == 'L') {
            msg = is_up ? WM_LBUTTONUP : WM_LBUTTONDOWN;
            mk = MK_LBUTTON;
        } else if (cmd[0] == 'R') {
            msg = is_up ? WM_RBUTTONUP : WM_RBUTTONDOWN;
            mk = MK_RBUTTON;
        } else {
            msg = is_up ? WM_MBUTTONUP : WM_MBUTTONDOWN;
            mk = MK_MBUTTON;
        }
        /* Upstream posts wparam 0 on release and the button mask on press
         * (post_message.py:150-155, :245-246); mirror it exactly. */
        post_msg(s, cmd, msg, is_up ? 0 : mk, point_lparam(x, y));
    } else if (strcmp(cmd, "QUIT") == 0) {
        send_line(s, "QUIT ok");
        return -1;
    } else {
        send_line(s, "ERR %s unknown", cmd);
    }
    return 0;
}

/* ----------------------------------------------------------------- main ---- */

static void parse_args(int argc, char **argv) {
    for (int i = 1; i < argc; ++i) {
        const char *value = (i + 1 < argc) ? argv[i + 1] : NULL;
        if (!value) break;
        if (strcmp(argv[i], "--exe") == 0)
            MultiByteToWideChar(CP_UTF8, 0, value, -1, g_exe_name, MAX_PATH), ++i;
        else if (strcmp(argv[i], "--class") == 0)
            MultiByteToWideChar(CP_UTF8, 0, value, -1, g_class_name, 128), ++i;
        else if (strcmp(argv[i], "--child-class") == 0)
            MultiByteToWideChar(CP_UTF8, 0, value, -1, g_child_class, 128), ++i;
        else if (strcmp(argv[i], "--handshake") == 0)
            MultiByteToWideChar(CP_UTF8, 0, value, -1, g_handshake, MAX_PATH), ++i;
    }
}

int main(int argc, char **argv) {
    int idle_exit_sec = 600;
    for (int i = 1; i < argc - 1; ++i)
        if (strcmp(argv[i], "--idle-exit") == 0) idle_exit_sec = atoi(argv[i + 1]);
    parse_args(argc, argv);
    if (g_class_name[0] == L'-') g_class_name[0] = L'\0';  /* `--class -` disables it */

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 2;

    SOCKET listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listener == INVALID_SOCKET) return 3;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);  /* loopback only, never the network */
    addr.sin_port = 0;                              /* kernel-assigned */
    if (bind(listener, (struct sockaddr *)&addr, sizeof addr) != 0) return 4;
    if (listen(listener, 4) != 0) return 5;

    int addr_len = (int)sizeof addr;
    if (getsockname(listener, (struct sockaddr *)&addr, &addr_len) != 0) return 6;
    unsigned short port = ntohs(addr.sin_port);

    gen_token();
    HWND initial = resolve_window();
    if (!write_handshake(port, initial != NULL)) return 7;

    DWORD last_activity = GetTickCount();
    for (;;) {
        fd_set readable;
        FD_ZERO(&readable);
        FD_SET(listener, &readable);
        struct timeval tv = {1, 0};
        int ready = select(0, &readable, NULL, NULL, &tv);
        if (ready < 0) break;
        if (ready == 0) {
            if (idle_exit_sec > 0 &&
                (DWORD)(GetTickCount() - last_activity) > (DWORD)idle_exit_sec * 1000)
                break;
            continue;
        }

        SOCKET client = accept(listener, NULL, NULL);
        if (client == INVALID_SOCKET) continue;
        BOOL nodelay = TRUE;
        setsockopt(client, IPPROTO_TCP, TCP_NODELAY, (const char *)&nodelay, sizeof nodelay);

        int authed = 0, quit_process = 0;
        char buf[LINE_MAX_LEN * 2];
        int used = 0;
        for (;;) {
            int got = recv(client, buf + used, (int)sizeof buf - used - 1, 0);
            if (got <= 0) break;
            used += got;
            buf[used] = '\0';

            int start = 0;
            for (int i = 0; i < used; ++i) {
                if (buf[i] != '\n') continue;
                buf[i] = '\0';
                int end = i;
                if (end > start && buf[end - 1] == '\r') buf[end - 1] = '\0';
                int verdict = handle_line(client, buf + start, &authed);
                start = i + 1;
                if (verdict != 0) {
                    quit_process = (verdict < 0);
                    goto close_client;
                }
            }
            if (start > 0) {
                memmove(buf, buf + start, used - start);
                used -= start;
            }
            if (used >= LINE_MAX_LEN) {  /* a line this long is a desynchronised client */
                send_line(client, "ERR - overlong");
                break;
            }
        }
    close_client:
        closesocket(client);
        last_activity = GetTickCount();
        if (quit_process) break;
    }

    closesocket(listener);
    DeleteFileW(g_handshake);
    WSACleanup();
    return 0;
}
