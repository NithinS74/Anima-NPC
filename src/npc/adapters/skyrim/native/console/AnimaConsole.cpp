// Anima console launcher: shows the Python bridge output in a visible console window, like a mod-manager console.
// Independently authored. Reads AnimaConsole.ini next to this exe: Python=, WorkingDir=, Arguments=.
#include <Windows.h>
#include <string>
#include <vector>

namespace {
std::wstring Ini(const std::wstring& path, const wchar_t* key)
{
    std::vector<wchar_t> buffer(32768);
    GetPrivateProfileStringW(L"Console", key, L"", buffer.data(), static_cast<DWORD>(buffer.size()), path.c_str());
    return buffer.data();
}
void Say(const std::wstring& text)
{
    DWORD written = 0;
    const auto line = text + L"\r\n";
    WriteConsoleW(GetStdHandle(STD_OUTPUT_HANDLE), line.c_str(), static_cast<DWORD>(line.size()), &written, nullptr);
}
void WaitForKey()
{
    Say(L"Press any key to close this window.");
    HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
    FlushConsoleInputBuffer(input);
    INPUT_RECORD record; DWORD count = 0;
    while (ReadConsoleInputW(input, &record, 1, &count) && count)
        if (record.EventType == KEY_EVENT && record.Event.KeyEvent.bKeyDown) break;
}
// A job object kills the bridge when this launcher dies, including when the user closes the window.
HANDLE KillOnCloseJob()
{
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    if (!job) return nullptr;
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits));
    return job;
}
}

int wmain(int argc, wchar_t** argv)
{
    SetConsoleTitleW(L"Anima Skyrim Bridge");
    SetConsoleOutputCP(CP_UTF8);
    DWORD mode = 0;
    HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE);
    if (GetConsoleMode(out, &mode)) SetConsoleMode(out, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);

    DWORD parentPid = 0;
    for (int i = 1; i + 1 < argc; ++i)
        if (std::wstring(argv[i]) == L"--parent-pid") parentPid = static_cast<DWORD>(_wtoi(argv[i + 1]));

    std::vector<wchar_t> self(32768);
    GetModuleFileNameW(nullptr, self.data(), static_cast<DWORD>(self.size()));
    std::wstring ini = self.data();
    ini = ini.substr(0, ini.find_last_of(L"\\/") + 1) + L"AnimaConsole.ini";
    const auto python = Ini(ini, L"Python"), directory = Ini(ini, L"WorkingDir"), arguments = Ini(ini, L"Arguments");
    if (python.empty() || directory.empty()) {
        Say(L"[ANIMA CONSOLE] Missing Python= or WorkingDir= in " + ini);
        Say(L"Run scripts/install_skyrim_console.py to create AnimaConsole.ini.");
        WaitForKey();
        return 2;
    }

    HANDLE parent = nullptr;
    if (parentPid) parent = OpenProcess(SYNCHRONIZE, FALSE, parentPid);
    HANDLE job = KillOnCloseJob();
    std::wstring commandLine = L"\"" + python + L"\" " + arguments;
    STARTUPINFOW startup{}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION child{};
    Say(L"[ANIMA CONSOLE] Starting bridge: " + commandLine);
    if (!CreateProcessW(python.c_str(), commandLine.data(), nullptr, nullptr, TRUE, CREATE_SUSPENDED, nullptr,
                        directory.c_str(), &startup, &child)) {
        Say(L"[ANIMA CONSOLE] Could not start Python (error " + std::to_wstring(GetLastError()) + L"). Check Python= in " + ini);
        WaitForKey();
        return 3;
    }
    if (job) AssignProcessToJobObject(job, child.hProcess);
    ResumeThread(child.hThread);
    CloseHandle(child.hThread);

    DWORD code = 0;
    bool parentExited = false;
    HANDLE waits[2] = {child.hProcess, parent};
    const DWORD n = parent ? 2 : 1;
    const DWORD result = WaitForMultipleObjects(n, waits, FALSE, INFINITE);
    if (result == WAIT_OBJECT_0 + 1) {
        parentExited = true;
        TerminateProcess(child.hProcess, 0);
        WaitForSingleObject(child.hProcess, 3000);
    }
    GetExitCodeProcess(child.hProcess, &code);
    CloseHandle(child.hProcess);
    if (parentExited) return 0;  // The game closed; nothing left to show.
    if (code != 0) {
        Say(L"[ANIMA CONSOLE] The bridge stopped with exit code " + std::to_wstring(code) + L".");
        Say(L"Hint: read the last lines above; check the provider key, port 8768 conflicts and the --log-file output.");
        WaitForKey();
        return static_cast<int>(code);
    }
    Say(L"[ANIMA CONSOLE] The bridge exited normally.");
    return 0;
}
