#pragma once
#include <string>
#include <string_view>
#include <array>
#include <cstdint>
namespace anima {
inline bool RequiresResync(std::uint32_t status, std::string_view error) {
    return status == 409 && (error == "unknown or ended session" || error == "session already ended; open a new conversation" ||
        error == "game epoch mismatch" || error == "snapshot actor mismatch" || error == "out of order state revision" || error == "out of order game event");
}
enum class Panel { none, options, text };
inline constexpr std::array<const char*, 3> MenuEntries{
    "ANIMA: Start conversation / type message;;-1;;0;;0;;0",
    "ANIMA: Voice input (hold F8);;-1;;1;;1;;0",
    "ANIMA: End conversation;;-1;;2;;2;;0"};
struct UiState {
    Panel panel = Panel::none;
    std::string session;
    std::uint64_t generation = 0;
    bool Open(std::string_view current, Panel desired) {
        if (current.empty() || panel != Panel::none || desired == Panel::none) return false;
        session = current; panel = desired; ++generation; return true;
    }
    bool Owns(std::string_view current, Panel expected) const {
        return panel == expected && !session.empty() && session == current;
    }
    bool CanSubmit(std::string_view current, std::string_view text) const {
        return Owns(current, Panel::text) && !text.empty() && text.size() <= 4000 &&
            text.find_first_not_of(" \r\n\t") != std::string_view::npos;
    }
    void Cancel() { panel = Panel::none; session.clear(); ++generation; }
};
}
