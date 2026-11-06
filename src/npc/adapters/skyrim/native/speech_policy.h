#pragma once
#include <algorithm>
#include <cstdint>
namespace anima {
// Vanilla speech from the delivering NPC is suppressed only while an Anima delivery is active.
// It never concerns the player's own speech or Anima's own sound handle (callers pass vanilla-only signals).
enum class SuppressAction { none, stop, stop_and_log };
struct SpeechSuppressor {
    bool logged = false;
    void Begin() { logged = false; }
    SuppressAction Decide(bool enabled, bool deliveryActive, bool vanillaSpeaking) {
        if (!enabled || !deliveryActive || !vanillaSpeaking) return SuppressAction::none;
        if (logged) return SuppressAction::stop;
        logged = true; return SuppressAction::stop_and_log;
    }
};
// A Say line gives no receipt of its own: it counts as started only once the actor is seen speaking.
// If that has not happened within kSayProofMs the delivery fails (audio_failed) so the bridge can fall back.
inline constexpr std::int64_t kSayProofMs = 2000;
enum class SayProof { waiting, started, failed };
inline SayProof DecideSayProof(bool actorSpeaking, std::int64_t elapsedMs) {
    if (actorSpeaking) return SayProof::started;
    return elapsedMs >= kSayProofMs ? SayProof::failed : SayProof::waiting;
}
// An opening greeting must never cut off the NPC's own greeting or quest lines.
inline bool MayStopCurrentDialogue(bool openingDelivery) { return !openingDelivery; }
// Worker poll interval: 25 ms while a turn or delivery is pending, 100 ms otherwise.
// Consecutive failures back off exponentially (250 ms base) up to 2 s so a dead bridge never busy-loops.
inline std::int64_t PollDelayMs(bool pending, unsigned failures) {
    if (failures == 0) return pending ? 25 : 100;
    return std::min<std::int64_t>(2000, 250LL << std::min(failures - 1, 6u));
}
}
