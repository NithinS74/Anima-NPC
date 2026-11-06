#pragma once
#include <string>
namespace anima {
// Decides whether the plugin should open the Anima console launcher. Pure logic so it is unit-testable.
enum class LaunchDecision { disabled, no_exe_configured, missing_exe, already_launched, already_running, launch };

// Order matters: a disabled feature never inspects anything else; one launch per game session;
// a bridge that already answers is left alone (never started twice).
inline LaunchDecision DecideLaunch(bool enabled, bool exeConfigured, bool exeExists, bool alreadyLaunched, bool bridgeAnswering)
{
    if (!enabled) return LaunchDecision::disabled;
    if (alreadyLaunched) return LaunchDecision::already_launched;
    if (!exeConfigured) return LaunchDecision::no_exe_configured;
    if (!exeExists) return LaunchDecision::missing_exe;
    if (bridgeAnswering) return LaunchDecision::already_running;
    return LaunchDecision::launch;
}

inline const char* DescribeLaunch(LaunchDecision decision)
{
    switch (decision) {
    case LaunchDecision::disabled: return "LaunchConsole=0; console not started";
    case LaunchDecision::no_exe_configured: return "LaunchConsole=1 but ConsoleExe is empty";
    case LaunchDecision::missing_exe: return "ConsoleExe does not exist";
    case LaunchDecision::already_launched: return "console already launched this session";
    case LaunchDecision::already_running: return "bridge already answering; console not started";
    case LaunchDecision::launch: return "launching console";
    }
    return "unknown";
}

// "<exe>" --parent-pid <pid>; the exe path is quoted so spaces survive.
inline std::wstring ConsoleCommandLine(const std::wstring& exe, unsigned long pid)
{
    return L"\"" + exe + L"\" --parent-pid " + std::to_wstring(pid);
}
}
