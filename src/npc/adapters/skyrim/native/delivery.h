#pragma once
#include <algorithm>
#include <cstdint>
#include <string_view>

namespace anima {
enum class Decision { ignore, reject, wait, play };
struct Delivery {
    std::string_view session, npc, id;
    std::uint64_t revision;
    std::int64_t expires;
    std::size_t textBytes;
};
struct Receiver {
    std::string_view session, npc;
    std::uint64_t revision;
    std::int64_t now;
    bool actorReady, vanillaTalking, duplicate;
};
inline Decision Evaluate(const Delivery& request, const Receiver& receiver)
{
    if (receiver.session.empty() || request.session != receiver.session || receiver.duplicate) return Decision::ignore;
    const bool validID = request.id.size() == 32 && std::all_of(request.id.begin(), request.id.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
    if (!validID || !receiver.actorReady || request.npc != receiver.npc || request.revision != receiver.revision
        || request.expires <= receiver.now || request.textBytes > 2000) return Decision::reject;
    return receiver.vanillaTalking ? Decision::wait : Decision::play;
}

// Keep the engine-to-policy mapping here so native delivery and the offline
// receiver tests exercise the same selected-speaker/active-line checks.
template <class TopicManager, class SpeakerHandle>
Decision EvaluateDialogue(const Delivery& request, Receiver receiver,
                          const TopicManager* manager, const SpeakerHandle& speaker)
{
    const bool currentSpeaker = manager && manager->IsCurrentSpeaker(speaker);
    receiver.actorReady = receiver.actorReady && currentSpeaker;
    receiver.vanillaTalking = currentSpeaker && manager->currentTopicInfo != nullptr;
    return Evaluate(request, receiver);
}
}
