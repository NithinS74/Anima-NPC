#include "delivery.h"
#include <iostream>

int main()
{
    using anima::Decision;
    anima::Delivery request{"session", "npc", "0123456789abcdef0123456789abcdef", 4, 2000, 20};
    anima::Receiver receiver{"session", "npc", 4, 1000, true, false, false};
    int failures = 0;
    auto check = [&](Decision expected, const char* label) {
        if (anima::Evaluate(request, receiver) != expected) { std::cerr << label << '\n'; ++failures; }
    };
    check(Decision::play, "valid delivery");
    receiver.duplicate = true; check(Decision::ignore, "duplicate must never replay"); receiver.duplicate = false;
    receiver.vanillaTalking = true; check(Decision::wait, "wait for authored speech"); receiver.vanillaTalking = false;
    receiver.revision = 5; check(Decision::reject, "changed state"); receiver.revision = 4;
    receiver.now = 2000; check(Decision::reject, "start expiry boundary"); receiver.now = 1000;
    receiver.npc = "other"; check(Decision::reject, "wrong NPC"); receiver.npc = "npc";
    receiver.session = "other"; check(Decision::ignore, "old session"); receiver.session = "session";
    receiver.actorReady = false; check(Decision::reject, "combat or missing actor"); receiver.actorReady = true;
    request.id = "../../outside"; check(Decision::reject, "invalid delivery path ID");
    return failures ? 1 : 0;
}
