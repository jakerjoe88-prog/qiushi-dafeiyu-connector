/* 秋实的大肥鱼连接器 启动器外壳：带看板娘图标的小 exe，静默拉起 runtime\python\pythonw.exe app\launcher.py */
#include <windows.h>
#include <shlwapi.h>
int WINAPI wWinMain(HINSTANCE h, HINSTANCE p, LPWSTR cmd, int show) {
    wchar_t dir[MAX_PATH], py[MAX_PATH], line[MAX_PATH * 3 + 64];
    GetModuleFileNameW(NULL, dir, MAX_PATH);
    PathRemoveFileSpecW(dir);
    int debug = cmd && wcsstr(cmd, L"--debug");
    wsprintfW(py, L"%s\\runtime\\python\\%s", dir, debug ? L"python.exe" : L"pythonw.exe");
    if (GetFileAttributesW(py) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(NULL, L"找不到 runtime\\python。请把整个压缩包完整解压后再运行（不要在压缩包里直接双击）。",
                    L"秋实的大肥鱼连接器", MB_ICONERROR);
        return 1;
    }
    wsprintfW(line, L"\"%s\" \"%s\\app\\launcher.py\" %s", py, dir, cmd ? cmd : L"");
    STARTUPINFOW si = {sizeof(si)}; PROCESS_INFORMATION pi;
    if (!CreateProcessW(NULL, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        MessageBoxW(NULL, L"启动失败，请试试「调试启动（出问题时用）.bat」查看原因。", L"秋实的大肥鱼连接器", MB_ICONERROR);
        return 1;
    }
    if (debug) WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return 0;
}
