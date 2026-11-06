#pragma once
#include <cstdint>
namespace anima {
// Menu-less NPCs answer E with a static bark and open no DialogueMenu. When the player activates an actor and no
// menu opens within kActivationMenuWaitMs, the activation is treated as "no menu" and a direct session starts.
inline constexpr std::int64_t kActivationMenuWaitMs = 700;
inline constexpr std::int64_t kActivationTimeoutMs = 3000;  // give up when a pause or custom menu keeps blocking the start

// Should this TESActivateEvent be remembered at all? Evaluated when the event arrives.
inline bool TrackActivation(bool enabled, bool byPlayer, bool targetIsActor, bool targetIsPlayer, bool alreadyInSession, bool validTarget) {
    return enabled && byPlayer && targetIsActor && !targetIsPlayer && !alreadyInSession && validTarget;
}

enum class ActivationAction { wait, cancel, start };
// Evaluated every tick for a remembered activation.
// menuOpened: a DialogueMenu opened (or is open) since the activation. sessionActive: any session now exists.
// blocked: paused or custom menu open. validTarget: the actor still passes the F6 rules (alive, not hostile/combat, in range).
inline ActivationAction DecideActivation(std::int64_t ageMs, bool menuOpened, bool sessionActive, bool blocked, bool validTarget) {
    if (menuOpened || sessionActive || !validTarget) return ActivationAction::cancel;
    if (ageMs < kActivationMenuWaitMs) return ActivationAction::wait;
    if (blocked) return ageMs > kActivationTimeoutMs ? ActivationAction::cancel : ActivationAction::wait;
    return ActivationAction::start;
}
inline const char* ActivationReason(bool menuOpened, bool sessionActive, bool validTarget) {
    if (menuOpened) return "dialogue_menu_opened";
    if (sessionActive) return "session_active";
    if (!validTarget) return "invalid_target";
    return "timeout";
}
}
