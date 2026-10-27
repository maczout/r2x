/* r2x helper: runs inside the same Wine prefix as Response-2000 and answers one command per line
 * on stdin. Every reply is one line starting with "ok" or "err"; "tree" replies "ok N" followed by
 * N lines. Build: i686-w64-mingw32-gcc -O2 -o helper.exe helper.c -luser32 -lgdi32
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
 *   popuprect                the open context menu's screen rectangle: "ok L T R B"
 *   menukey <vk>             post a key to the open context menu
 *   clipseq                  clipboard sequence number
 *   clipclear                empty the clipboard
 *   clip                     CF_TEXT contents, hex-encoded
 *   find <hwnd> <id>         first descendant of a window with this control ID (dialogs)
 *   gettext <hwnd>           a control's text (WM_GETTEXT), hex-encoded
 *   settext <hwnd> <hex>     set a control's text (WM_SETTEXT); text hex-encoded, "-" if empty
 *   click <hwnd>             post BM_CLICK to a button
 *   getcheck <hwnd>          a check box or radio button's state (0 or 1)
 *   alive <hwnd>             "ok 1" if the window exists and is visible, else "ok 0"
 *   cbitems <hwnd>           a combo box's items: "ok N", then N lines, each hex-encoded
 *   cbget <hwnd>             a combo box's selected index (-1: none)
 *   cbselect <hwnd> <index>  select a combo box item and notify its parent (CBN_SELCHANGE, sent)
 *   clipformats              clipboard format IDs, space-separated
 *   clipemf <width> <hexpath>  render the clipboard's enhanced metafile (Copy Chart Picture) to a
 *                            24-bit BMP file this wide, height from its aspect; "ok W H"
 *   snap <hwnd> <hexpath>    the window as it is on screen, to a 24-bit BMP file; "ok W H"
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

static int g_find_id;
static HWND g_found;

static BOOL CALLBACK find_cb(HWND h, LPARAM lp) {
    (void)lp;
    if (GetDlgCtrlID(h) == g_find_id) { g_found = h; return FALSE; }
    return TRUE;
}

/* Messages to another process's controls go through SendMessageTimeout so a busy or hung
 * Response cannot block the helper. */
#define SEND_TIMEOUT_MS 5000

static int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static void do_gettext(HWND h) {
    char buf[1024];
    DWORD_PTR n = 0;
    if (!IsWindow(h)) { printf("err no window\n"); return; }
    if (!SendMessageTimeoutA(h, WM_GETTEXT, sizeof buf, (LPARAM)buf, SMTO_ABORTIFHUNG,
                             SEND_TIMEOUT_MS, &n)) { printf("err gettext\n"); return; }
    buf[n < sizeof buf ? n : sizeof buf - 1] = 0;
    printf("ok ");
    for (const unsigned char *p = (const unsigned char *)buf; *p; p++) printf("%02x", *p);
    printf("\n");
}

static BOOL open_clipboard(void);

static int unhex(const char *hex, char *out, size_t size) {
    size_t n = 0;
    for (; hex[0] && hex[1] && n < size - 1; hex += 2) {
        int hi = hexval(hex[0]), lo = hexval(hex[1]);
        if (hi < 0 || lo < 0) return 0;
        out[n++] = (char)(hi * 16 + lo);
    }
    out[n] = 0;
    return 1;
}

/* A combo box's items: "ok N", then one line per item, hex-encoded. */
static void do_cbitems(HWND h) {
    DWORD_PTR n = 0;
    if (!IsWindow(h) || !SendMessageTimeoutA(h, CB_GETCOUNT, 0, 0, SMTO_ABORTIFHUNG,
                                             SEND_TIMEOUT_MS, &n) || (LRESULT)n < 0) {
        printf("err cbitems\n");
        return;
    }
    printf("ok %d\n", (int)n);
    for (int i = 0; i < (int)n; i++) {
        /* Wide characters: Wine passes the item text across processes as UTF-16. */
        WCHAR wbuf[256] = L"";
        char buf[512] = "";
        DWORD_PTR len = 0;
        if (SendMessageTimeoutW(h, CB_GETLBTEXTLEN, i, 0, SMTO_ABORTIFHUNG, SEND_TIMEOUT_MS, &len)
            && (LRESULT)len >= 0 && len < sizeof wbuf / sizeof wbuf[0])
            SendMessageTimeoutW(h, CB_GETLBTEXT, i, (LPARAM)wbuf, SMTO_ABORTIFHUNG,
                                SEND_TIMEOUT_MS, &len);
        WideCharToMultiByte(1252, 0, wbuf, -1, buf, sizeof buf, NULL, NULL);
        for (const unsigned char *p = (const unsigned char *)buf; *p; p++) printf("%02x", *p);
        printf("\n");
    }
}

/* Select a combo box item as the user would: set it, then tell the parent it changed. The
 * notification is sent, as a combo box sends it, so the reply comes once the parent has handled
 * it (for Response's view list: once the new view's charts are in place). */
static void do_cbselect(HWND h, int index) {
    DWORD_PTR r = 0;
    if (!IsWindow(h) || !SendMessageTimeoutA(h, CB_SETCURSEL, index, 0, SMTO_ABORTIFHUNG,
                                             SEND_TIMEOUT_MS, &r) || (LRESULT)r != index) {
        printf("err cbselect\n");
        return;
    }
    printf(SendMessageTimeoutA(GetParent(h), WM_COMMAND,
                               MAKEWPARAM(GetDlgCtrlID(h), CBN_SELCHANGE), (LPARAM)h,
                               SMTO_ABORTIFHUNG, SEND_TIMEOUT_MS, &r)
           ? "ok\n" : "err notify\n");
}

/* Write a bitmap selected out of any DC as a bottom-up 24-bit BMP file. */
static int save_bmp(HBITMAP bmp, int w, int h, const char *path) {
    BITMAPINFOHEADER bi;
    BITMAPFILEHEADER bf;
    int stride = (w * 3 + 3) & ~3;
    DWORD size = (DWORD)stride * h;
    unsigned char *px = malloc(size);
    HDC dc = GetDC(NULL);
    FILE *f;
    int ok;
    memset(&bi, 0, sizeof bi);
    bi.biSize = sizeof bi; bi.biWidth = w; bi.biHeight = h; bi.biPlanes = 1;
    bi.biBitCount = 24; bi.biCompression = BI_RGB;
    ok = px && GetDIBits(dc, bmp, 0, h, px, (BITMAPINFO *)&bi, DIB_RGB_COLORS) == h;
    ReleaseDC(NULL, dc);
    if (ok && (f = fopen(path, "wb"))) {
        memset(&bf, 0, sizeof bf);
        bf.bfType = 0x4D42;
        bf.bfOffBits = sizeof bf + sizeof bi;
        bf.bfSize = bf.bfOffBits + size;
        ok = fwrite(&bf, sizeof bf, 1, f) == 1 && fwrite(&bi, sizeof bi, 1, f) == 1 &&
             fwrite(px, 1, size, f) == size;
        ok = (fclose(f) == 0) && ok;
    } else ok = 0;
    free(px);
    return ok;
}

static void do_clipformats(void) {
    UINT fmt = 0;
    if (!open_clipboard()) { printf("err open clipboard\n"); return; }
    printf("ok");
    while ((fmt = EnumClipboardFormats(fmt))) printf(" %u", fmt);
    printf("\n");
    CloseClipboard();
}

static void do_clipemf(int width, const char *hexpath) {
    char path[MAX_PATH];
    HENHMETAFILE emf, own;
    ENHMETAHEADER hdr;
    if (width <= 0 || !unhex(hexpath, path, sizeof path)) { printf("err bad arguments\n"); return; }
    if (!open_clipboard()) { printf("err open clipboard\n"); return; }
    emf = (HENHMETAFILE)GetClipboardData(CF_ENHMETAFILE);
    own = emf ? CopyEnhMetaFileA(emf, NULL) : NULL;
    CloseClipboard();
    if (!own) { printf("err no metafile\n"); return; }
    GetEnhMetaFileHeader(own, sizeof hdr, &hdr);
    {
        LONG fw = hdr.rclFrame.right - hdr.rclFrame.left, fh = hdr.rclFrame.bottom - hdr.rclFrame.top;
        int height = fw > 0 ? (int)((double)width * fh / fw + 0.5) : width * 3 / 4;
        HDC screen = GetDC(NULL), mem = CreateCompatibleDC(screen);
        HBITMAP bmp = CreateCompatibleBitmap(screen, width, height);
        HGDIOBJ old = SelectObject(mem, bmp);
        RECT r = {0, 0, width, height};
        PatBlt(mem, 0, 0, width, height, WHITENESS);
        PlayEnhMetaFile(mem, own, &r);
        SelectObject(mem, old);
        if (save_bmp(bmp, width, height, path)) printf("ok %d %d\n", width, height);
        else printf("err save\n");
        DeleteObject(bmp); DeleteDC(mem); ReleaseDC(NULL, screen);
    }
    DeleteEnhMetaFile(own);
}

static void do_snap(HWND h, const char *hexpath) {
    char path[MAX_PATH];
    RECT r;
    int w, ht;
    if (!IsWindow(h) || !unhex(hexpath, path, sizeof path)) { printf("err bad arguments\n"); return; }
    GetWindowRect(h, &r);
    w = r.right - r.left; ht = r.bottom - r.top;
    {
        /* Copy from the window's own DC: Wine draws each top-level window into its own surface,
         * and the screen DC only shows the (empty) desktop. */
        HDC src = GetWindowDC(h), mem = CreateCompatibleDC(src);
        HBITMAP bmp = CreateCompatibleBitmap(src, w, ht);
        HGDIOBJ old = SelectObject(mem, bmp);
        BitBlt(mem, 0, 0, w, ht, src, 0, 0, SRCCOPY);
        SelectObject(mem, old);
        if (save_bmp(bmp, w, ht, path)) printf("ok %d %d\n", w, ht);
        else printf("err save\n");
        DeleteObject(bmp); DeleteDC(mem); ReleaseDC(h, src);
    }
}

static void do_settext(HWND h, const char *hex) {
    char buf[512];
    size_t n = 0;
    DWORD_PTR r;
    if (!IsWindow(h)) { printf("err no window\n"); return; }
    if (strcmp(hex, "-")) {
        for (; hex[0] && hex[1] && n < sizeof buf - 1; hex += 2) {
            int hi = hexval(hex[0]), lo = hexval(hex[1]);
            if (hi < 0 || lo < 0) { printf("err bad hex\n"); return; }
            buf[n++] = (char)(hi * 16 + lo);
        }
    }
    buf[n] = 0;
    if (!SendMessageTimeoutA(h, WM_SETTEXT, 0, (LPARAM)buf, SMTO_ABORTIFHUNG, SEND_TIMEOUT_MS, &r))
        printf("err settext\n");
    else printf("ok\n");
}

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
        } else if (!strcmp(cmd, "popuprect")) {
            HWND p = FindWindowA("#32768", NULL);
            RECT r;
            if (p && IsWindowVisible(p) && GetWindowRect(p, &r))
                printf("ok %ld %ld %ld %ld\n", r.left, r.top, r.right, r.bottom);
            else printf("err no popup\n");
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
        } else if (!strcmp(cmd, "find") && a1 && a2) {
            g_find_id = atoi(a2);
            g_found = NULL;
            EnumChildWindows(parse_hwnd(a1), find_cb, 0);
            if (g_found) printf("ok %lx\n", (unsigned long)(ULONG_PTR)g_found);
            else printf("err no control %s\n", a2);
        } else if (!strcmp(cmd, "gettext") && a1) {
            do_gettext(parse_hwnd(a1));
        } else if (!strcmp(cmd, "settext") && a1 && a2) {
            do_settext(parse_hwnd(a1), a2);
        } else if (!strcmp(cmd, "click") && a1) {
            HWND t = parse_hwnd(a1);
            printf(IsWindow(t) && PostMessageA(t, BM_CLICK, 0, 0) ? "ok\n" : "err click\n");
        } else if (!strcmp(cmd, "getcheck") && a1) {
            DWORD_PTR r = 0;
            HWND t = parse_hwnd(a1);
            if (IsWindow(t) && SendMessageTimeoutA(t, BM_GETCHECK, 0, 0, SMTO_ABORTIFHUNG,
                                                   SEND_TIMEOUT_MS, &r))
                printf("ok %d\n", r == BST_CHECKED ? 1 : 0);
            else printf("err getcheck\n");
        } else if (!strcmp(cmd, "clipformats")) {
            do_clipformats();
        } else if (!strcmp(cmd, "clipemf") && a1 && a2) {
            do_clipemf(atoi(a1), a2);
        } else if (!strcmp(cmd, "snap") && a1 && a2) {
            do_snap(parse_hwnd(a1), a2);
        } else if (!strcmp(cmd, "cbitems") && a1) {
            do_cbitems(parse_hwnd(a1));
        } else if (!strcmp(cmd, "cbget") && a1) {
            DWORD_PTR r = 0;
            HWND t = parse_hwnd(a1);
            if (IsWindow(t) && SendMessageTimeoutA(t, CB_GETCURSEL, 0, 0, SMTO_ABORTIFHUNG,
                                                   SEND_TIMEOUT_MS, &r))
                printf("ok %d\n", (int)(LRESULT)r);
            else printf("err cbget\n");
        } else if (!strcmp(cmd, "cbselect") && a1 && a2) {
            do_cbselect(parse_hwnd(a1), atoi(a2));
        } else if (!strcmp(cmd, "alive") && a1) {
            HWND t = parse_hwnd(a1);
            printf("ok %d\n", IsWindow(t) && IsWindowVisible(t) ? 1 : 0);
        } else {
            printf("err unknown command\n");
        }
        fflush(stdout);
    }
    return 0;
}
