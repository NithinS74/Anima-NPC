#pragma once
#include <cstdint>
namespace anima {
enum class AudioDecision { waiting, started, playing, completed, failed, interrupted };
struct AudioState {
    std::int64_t attemptedAt = 0, observedAt = 0, duration = 0;
    bool observed = false;
    void Begin(std::int64_t now, std::int64_t durationMs) { attemptedAt = now; duration = durationMs; observed = false; }
    AudioDecision Update(std::int64_t now, bool playing) {
        if (!observed) {
            if (playing) { observed = true; observedAt = now; return AudioDecision::started; }
            return now - attemptedAt >= 2000 ? AudioDecision::failed : AudioDecision::waiting;
        }
        const auto elapsed = now - observedAt;
        if (playing) return elapsed > duration + 1500 ? AudioDecision::failed : AudioDecision::playing;
        return elapsed + 150 >= duration ? AudioDecision::completed : AudioDecision::interrupted;
    }
};
}
