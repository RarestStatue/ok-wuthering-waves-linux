/* VERIFIED PROOF-OF-CONCEPT -- see PORT.md [V6].
 * Proves PostMessage from inside a Wine prefix reaches an UNFOCUSED HWND.
 * Confirmed: WM_CHAR and WM_KEYDOWN/WM_KEYUP (scan-code lparam) both delivered
 * to wine notepad while X input focus was on another window.
 * Build: x86_64-w64-mingw32-gcc -O2 -o shim.exe shim/spike-notepad.c
 * This is the mechanism spike, NOT the full shim -- Phase 4a in PORT.md
 * specifies the socket protocol and game-window resolution to add.
 */
#include <windows.h>
#include <stdio.h>

/* Replicates ok-script post_message.py: PostMessage into an unfocused HWND. */
int main(void) {
    HWND top = FindWindowW(NULL, L"Untitled - Notepad");
    if (!top) { printf("RESULT=NOTFOUND\n"); return 1; }
    HWND edit = FindWindowExW(top, NULL, L"Edit", NULL);
    HWND target = edit ? edit : top;
    printf("top=%p edit=%p target=%p\n", (void*)top, (void*)edit, (void*)target);

    /* ok-script try_activate() */
    PostMessageW(top, WM_ACTIVATE, WA_ACTIVE, 0);

    /* WM_CHAR path (input_text) */
    const wchar_t *s = L"POSTMSG_CHAR_OK ";
    for (const wchar_t *p = s; *p; ++p) {
        PostMessageW(target, WM_CHAR, (WPARAM)*p, 0);
        Sleep(8);
    }

    /* WM_KEYDOWN/UP path with real scan-code lparam (send_key) */
    const char *keys = "KEYDN";
    for (const char *k = keys; *k; ++k) {
        UINT vk = (UINT)*k;
        UINT scan = MapVirtualKeyW(vk, 0);
        LPARAM down = ((LPARAM)scan << 16) | 1;
        LPARAM up   = down | (1L << 30) | (1L << 31);
        PostMessageW(target, WM_KEYDOWN, vk, down);
        Sleep(12);
        PostMessageW(target, WM_KEYUP, vk, up);
        Sleep(8);
    }
    printf("RESULT=POSTED\n");
    return 0;
}
