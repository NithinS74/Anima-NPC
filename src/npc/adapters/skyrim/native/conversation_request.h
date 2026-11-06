#pragma once
#include <cstdint>
namespace anima {
// "Talk with me." dialogue line (Anima.esp) asks the plugin to open the Anima text box for the speaker.
// The line is a Goodbye line, so the vanilla menu closes right after the fragment runs; a menu session would then end.
// The request therefore waits for menus to clear and continues as a menu-less (direct) session.
inline constexpr std::int64_t kOpenRequestTimeoutMs = 8000;

enum class OpenRequestAction { none, wait, expire, open_text, start_direct };

// pending: a request exists. blocked: a menu is open or the game is paused. sessionForTarget: a session for this
// speaker is already running. targetValid: the speaker may be talked to. textOpen: the Anima text box is already up.
inline OpenRequestAction DecideOpenRequest(bool pending, std::int64_t ageMs, bool blocked, bool sessionForTarget, bool targetValid, bool textOpen) {
    if (!pending) return OpenRequestAction::none;
    if (textOpen || ageMs > kOpenRequestTimeoutMs) return OpenRequestAction::expire;
    if (blocked) return OpenRequestAction::wait;
    if (sessionForTarget) return OpenRequestAction::open_text;
    return targetValid ? OpenRequestAction::start_direct : OpenRequestAction::wait;
}
}
