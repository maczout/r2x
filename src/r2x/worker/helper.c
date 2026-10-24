/* r2x helper: runs inside the same Wine prefix as Response-2000 and answers one command per line
 * on stdin. Every reply is one line starting with "ok" or "err"; "tree" replies "ok N" followed by
 * N lines. Build: i686-w64-mingw32-gcc -O2 -o helper.exe helper.c -luser32
 *
 * Commands
 *   main                     handle and title of Response's visible main window
 *   tree                     all descendants of the main window
 *   dialogs                  other visible top-level windows of Response's process (message boxes)
 *   kids <hwnd>              all descendants of a window
 *   cmd <id> [hwnd]          post WM_COMMAND id (to the main window by default)
 *   key <hwnd> <vk>          post WM_KEYDOWN/WM_KEYUP
 *   rclick <hwnd>            post a right-click at the window's client centre
 *   popup                    "ok 1" if a context menu is open, else "ok 0"
 *   menukey <vk>             post a key to the open context menu
 *   clipseq                  clipboard sequence number
 *   clipclear                empty the clipboard
 *   clip                     CF_TEXT contents, hex-encoded
 *   quit
 */
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HWND g_main;

static BOOL CALLBACK find_main_cb(HWND h, LPARAM lp) {
    char cls[64], txt[256];
    (void)lp;
    GetClassNameA(h, cls, sizeof cls);
    GetWindowTextA(h, txt, sizeof txt);
    if (!strcmp(cls, "OWL_Window") && !strncmp(txt, "Response", 8) && IsWindowVisible(h)) {
        g_main = h;
        return FALSE;
    }
    return TRUE;
}

static HWND find_main(void) {
    if (g_main && IsWindow(g_main)) return g_main;
    g_main = NULL;
    EnumWindows(find_main_cb, 0);
    return g_main;
}

static void print_window(HWND h) {
    char cls[64], txt[256];
    RECT r;
    GetClassNameA(h, cls, sizeof cls);
    GetWindowTextA(h, txt, sizeof txt);
    for (char *p = txt; *p; p++) if (*p == '\n' || *p == '\r') *p = ' ';
    GetWindowRect(h, &r);
    printf("%lx\t%lx\t%d\t%ld\t%ld\t%ld\t%ld\t%s\t%s\n", (unsigned long)(ULONG_PTR)h,
           (unsigned long)(ULONG_PTR)GetParent(h), IsWindowVisible(h) ? 1 : 0,
           r.left, r.top, r.right, r.bottom, cls, txt);
}

#define MAXW 512
static HWND g_list[MAXW];
static int g_n;

static BOOL CALLBACK collect_cb(HWND h, LPARAM lp) {
    (void)lp;
    if (g_n < MAXW) g_list[g_n++] = h;
    return TRUE;
}

static BOOL CALLBACK dialogs_cb(HWND h, LPARAM lp) {
    char cls[64];
    (void)lp;
    GetClassNameA(h, cls, sizeof cls);
    /* message boxes and dialogs (#32770) on the desktop; Response is the only app in the prefix */
    if (!strcmp(cls, "#32770") && IsWindowVisible(h) && g_n < MAXW) g_list[g_n++] = h;
    return TRUE;
}

static HWND parse_hwnd(const char *s) { return (HWND)(ULONG_PTR)strtoul(s ? s : "0", NULL, 16); }

/* Response opens the clipboard, empties it (which already bumps the sequence number), sets the
 * text and closes it; while it holds the clipboard, OpenClipboard fails. Retry for up to ~1 s. */
static BOOL open_clipboard(void) {
    for (int i = 0; i < 100; i++) {
        if (OpenClipboard(NULL)) return TRUE;
        Sleep(10);
    }
    return FALSE;
}

static void do_clip(void) {
    if (!open_clipboard()) { printf("err open clipboard\n"); return; }
    HANDLE h = GetClipboardData(CF_TEXT);
    if (!h) { CloseClipboard(); printf("err no text\n"); return; }
    const unsigned char *p = GlobalLock(h);
    if (!p) { CloseClipboard(); printf("err lock\n"); return; }
    printf("ok ");
    for (; *p; p++) printf("%02x", *p);
    printf("\n");
    GlobalUnlock(h);
    CloseClipboard();
}

int main(void) {
    char line[1024];
    _setmode(_fileno(stdout), _O_BINARY);
    setvbuf(stdout, NULL, _IOFBF, 1 << 16);
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        char *cmd = strtok(line, " "), *a1 = strtok(NULL, " "), *a2 = strtok(NULL, " ");
        if (!cmd) continue;
        HWND m = find_main();

        if (!strcmp(cmd, "quit")) { printf("ok\n"); fflush(stdout); break; }
        else if (!strcmp(cmd, "main")) {
            if (m) {
                char txt[256];
                GetWindowTextA(m, txt, sizeof txt);
                printf("ok %lx\t%s\n", (unsigned long)(ULONG_PTR)m, txt);
            } else printf("err no main window\n");
        } else if (!m && strcmp(cmd, "dialogs") && strcmp(cmd, "kids")) {
            printf("err no main window\n");
        } else if (!strcmp(cmd, "tree") || !strcmp(cmd, "dialogs") || (!strcmp(cmd, "kids") && a1)) {
            g_n = 0;
            if (cmd[0] == 't') EnumChildWindows(m, collect_cb, 0);
            else if (cmd[0] == 'k') EnumChildWindows(parse_hwnd(a1), collect_cb, 0);
            else EnumWindows(dialogs_cb, 0);
            printf("ok %d\n", g_n);
            for (int i = 0; i < g_n; i++) print_window(g_list[i]);
        } else if (!strcmp(cmd, "cmd") && a1) {
            HWND t = a2 ? parse_hwnd(a2) : m;
            printf(PostMessageA(t, WM_COMMAND, MAKEWPARAM(atoi(a1), 0), 0) ? "ok\n" : "err post\n");
        } else if (!strcmp(cmd, "key") && a1 && a2) {
            HWND t = parse_hwnd(a1);
            WPARAM vk = strtoul(a2, NULL, 0);
            PostMessageA(t, WM_KEYDOWN, vk, 1);
            PostMessageA(t, WM_KEYUP, vk, 0xC0000001);
            printf("ok\n");
        } else if (!strcmp(cmd, "rclick") && a1) {
            HWND t = parse_hwnd(a1);
            RECT r;
            GetClientRect(t, &r);
            LPARAM lp = MAKELPARAM(r.right / 2, r.bottom / 2);
            PostMessageA(t, WM_RBUTTONDOWN, MK_RBUTTON, lp);
            PostMessageA(t, WM_RBUTTONUP, 0, lp);
            printf("ok\n");
        } else if (!strcmp(cmd, "popup")) {
            HWND p = FindWindowA("#32768", NULL);
            printf("ok %d\n", p && IsWindowVisible(p) ? 1 : 0);
        } else if (!strcmp(cmd, "menukey") && a1) {
            HWND p = FindWindowA("#32768", NULL);
            if (!p) { printf("err no popup\n"); }
            else {
                WPARAM vk = strtoul(a1, NULL, 0);
                PostMessageA(p, WM_KEYDOWN, vk, 1);
                PostMessageA(p, WM_KEYUP, vk, 0xC0000001);
                printf("ok\n");
            }
        } else if (!strcmp(cmd, "clipseq")) {
            printf("ok %lu\n", (unsigned long)GetClipboardSequenceNumber());
        } else if (!strcmp(cmd, "clipclear")) {
            if (open_clipboard()) { EmptyClipboard(); CloseClipboard(); printf("ok\n"); }
            else printf("err open clipboard\n");
        } else if (!strcmp(cmd, "clip")) {
            do_clip();
        } else {
            printf("err unknown command\n");
        }
        fflush(stdout);
    }
    return 0;
}
