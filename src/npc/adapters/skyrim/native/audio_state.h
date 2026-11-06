#pragma once
#include <cstdint>
namespace anima {
// ended_early: the engine reported IsPlaying == false for at least kSilenceMs before the planned end.
// The player saw the subtitle, so the delivery still counts as completed (audio "ended_early").
// failed: audio never observed within kStartWindowMs, or it ran far past its plan.
enum class AudioDecision { waiting, started, playing, completed, ended_early, failed };
inline constexpr std::int64_t kStartWindowMs = 2000;
inline constexpr std::int64_t kSilenceMs = 300;
struct AudioState {
    std::int64_t attemptedAt = 0, observedAt = 0, duration = 0, silentSince = -1;
    bool observed = false;
    void Begin(std::int64_t now, std::int64_t durationMs) { attemptedAt = now; duration = durationMs; observed = false; silentSince = -1; observedAt = 0; }
    AudioDecision Update(std::int64_t now, bool playing) {
        if (!observed) {
            if (playing) { observed = true; observedAt = now; silentSince = -1; return AudioDecision::started; }
            return now - attemptedAt >= kStartWindowMs ? AudioDecision::failed : AudioDecision::waiting;
        }
        const auto elapsed = now - observedAt;
        if (playing) {
            silentSince = -1;
            return elapsed > duration + 1500 ? AudioDecision::failed : AudioDecision::playing;
        }
        if (elapsed + 150 >= duration) return AudioDecision::completed;
        if (silentSince < 0) silentSince = now;  // a brief false reading is not a verdict
        return now - silentSince >= kSilenceMs ? AudioDecision::ended_early : AudioDecision::playing;
    }
};
}
