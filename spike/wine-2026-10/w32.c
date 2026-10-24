// Spike helper: inspect and poke Response-2000 from inside the same Wine prefix.
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HWND g_main;

static BOOL CALLBACK find_main_cb(HWND h, LPARAM lp) {
    char cls[64], txt[256];
    GetClassNameA(h, cls, sizeof cls);
    GetWindowTextA(h, txt, sizeof txt);
    if (!strcmp(cls, "OWL_Window") && !strncmp(txt, "Response", 8) && IsWindowVisible(h)) {
        g_main = h; return FALSE;
    }
    return TRUE;
}

static HWND find_main(void) { g_main = NULL; EnumWindows(find_main_cb, 0); return g_main; }

static BOOL CALLBACK tree_cb(HWND h, LPARAM lp) {
    char cls[64], txt[256]; RECT r;
    GetClassNameA(h, cls, sizeof cls);
    GetWindowTextA(h, txt, sizeof txt);
    GetWindowRect(h, &r);
    printf("%08lx parent=%08lx vis=%d id=%ld rect=%ld,%ld,%ld,%ld class=%s text=%s\n",
           (long)(ULONG_PTR)h, (long)(ULONG_PTR)GetParent(h), IsWindowVisible(h),
           (long)GetDlgCtrlID(h), r.left, r.top, r.right, r.bottom, cls, txt);
    return TRUE;
}

static void dump_menu(HMENU m, int depth) {
    int n = GetMenuItemCount(m);
    for (int i = 0; i < n; i++) {
        char txt[256] = "";
        GetMenuStringA(m, i, txt, sizeof txt, MF_BYPOSITION);
        UINT st = GetMenuState(m, i, MF_BYPOSITION);
        HMENU sub = GetSubMenu(m, i);
        printf("%*s[%d] id=%u gray=%d sep=%d \"%s\"\n", depth * 2, "", i,
               sub ? 0 : GetMenuItemID(m, i), !!(st & (MF_GRAYED | MF_DISABLED)),
               !!(st & MF_SEPARATOR), txt);
        if (sub) dump_menu(sub, depth + 1);
    }
}

static int write_clip(const char *base) {
    if (!OpenClipboard(NULL)) { fprintf(stderr, "OpenClipboard failed\n"); return 1; }
    int rc = 1;
    HANDLE h = GetClipboardData(CF_TEXT);
    if (h) {
        const char *p = GlobalLock(h);
        char fn[512]; snprintf(fn, sizeof fn, "%s.a", base);
        FILE *f = fopen(fn, "wb"); fwrite(p, 1, strlen(p), f); fclose(f);
        GlobalUnlock(h); rc = 0;
    }
    h = GetClipboardData(CF_UNICODETEXT);
    if (h) {
        const WCHAR *p = GlobalLock(h);
        char fn[512]; snprintf(fn, sizeof fn, "%s.w", base);
        FILE *f = fopen(fn, "wb"); fwrite(p, sizeof(WCHAR), wcslen(p), f); fclose(f);
        GlobalUnlock(h);
    }
    UINT fmt = 0; printf("formats:");
    while ((fmt = EnumClipboardFormats(fmt))) printf(" %u", fmt);
    printf("\n");
    CloseClipboard();
    return rc;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage\n"); return 2; }
    const char *c = argv[1];
    HWND m = find_main();
    if (!strcmp(c, "main")) { printf("%08lx\n", (long)(ULONG_PTR)m); return !m; }
    if (!strcmp(c, "tree")) { EnumChildWindows(m, tree_cb, 0); return 0; }
    if (!strcmp(c, "menu")) { dump_menu(GetMenu(m), 0); return 0; }
    if (!strcmp(c, "cmd")) {   // cmd <id> [hwnd]  post WM_COMMAND
        HWND t = argc > 3 ? (HWND)(ULONG_PTR)strtoul(argv[3], 0, 16) : m;
        return !PostMessageA(t, WM_COMMAND, MAKEWPARAM(atoi(argv[2]), 0), 0);
    }
    if (!strcmp(c, "menustate")) {
        UINT st = GetMenuState(GetMenu(m), atoi(argv[2]), MF_BYCOMMAND);
        printf("%s\n", st == (UINT)-1 ? "missing" : (st & (MF_GRAYED|MF_DISABLED)) ? "gray" : "enabled");
        return 0;
    }
    if (!strcmp(c, "clipseq")) { printf("%lu\n", (unsigned long)GetClipboardSequenceNumber()); return 0; }
    if (!strcmp(c, "clipclear")) { OpenClipboard(NULL); EmptyClipboard(); CloseClipboard(); return 0; }
    if (!strcmp(c, "clip")) return write_clip(argv[2]);
    if (!strcmp(c, "popup")) {  // list items of the open context menu
        HWND p = FindWindowA("#32768", NULL);
        if (!p) { printf("none\n"); return 1; }
        HMENU hm = (HMENU)SendMessageA(p, 0x01E1 /* MN_GETHMENU */, 0, 0);
        printf("popup %08lx menu %p\n", (long)(ULONG_PTR)p, hm);
        if (hm) dump_menu(hm, 0);
        return 0;
    }
    if (!strcmp(c, "rclick")) {  // rclick <hwnd>: right button at client centre
        HWND t = (HWND)(ULONG_PTR)strtoul(argv[2], 0, 16); RECT r; GetClientRect(t, &r);
        LPARAM lp = MAKELPARAM(r.right / 2, r.bottom / 2);
        PostMessageA(t, WM_RBUTTONDOWN, MK_RBUTTON, lp);
        PostMessageA(t, WM_RBUTTONUP, 0, lp);
        return 0;
    }
    if (!strcmp(c, "key")) {  // key <hwnd> <vk>
        HWND t = (HWND)(ULONG_PTR)strtoul(argv[2], 0, 16); WPARAM vk = strtoul(argv[3], 0, 0);
        PostMessageA(t, WM_KEYDOWN, vk, 1); PostMessageA(t, WM_KEYUP, vk, 0xC0000001);
        return 0;
    }
    fprintf(stderr, "unknown command\n");
    return 2;
}
