// Independently authored. No Mantella source or binary dependency.
#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <Windows.h>
#ifdef GetObject
#undef GetObject
#endif
#include <winhttp.h>
#include <nlohmann/json.hpp>
#include <spdlog/sinks/basic_file_sink.h>
#include <atomic>
#include <chrono>
#include <deque>
#include <filesystem>
#include <format>
#include <cmath>
#include <mutex>
#include <thread>
#include <unordered_set>
#include "delivery.h"
#include "runtime_support.h"
#include "version_metadata.h"
#include "ui_state.h"
#include "audio_state.h"

using json = nlohmann::json;
using Clock = std::chrono::steady_clock;
namespace {
std::int64_t UtcMs()
{
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}
std::string Text(const char* value, std::size_t limit = 500)
{
    std::string text = value ? value : "";
    if (text.size() > limit) {
        auto end = limit;
        while (end && (static_cast<unsigned char>(text[end]) & 0xC0) == 0x80) --end;
        text.resize(end);
    }
    return text;
}
json Form(RE::TESForm* form)
{
    if (!form) return nullptr;
    auto file = form->GetFile(0);
    return {{"form_id", std::format("{:08X}", form->GetFormID())},
            {"local_id", std::format("{:08X}", file ? form->GetLocalFormID() : form->GetFormID())},
            {"plugin", file ? Text(file->fileName, 128) : ""}, {"name", Text(form->GetName())}};
}
json Actor(RE::Actor* actor, RE::Actor* player)
{
    auto base = actor->GetActorBase();
    json factions = json::array(), equipment = json::array();
    if (base) for (const auto& faction : base->factions)
        if (faction.faction && factions.size() < 64) factions.push_back(Form(faction.faction));
    for (bool left : {false, true})
        if (auto item = actor->GetEquippedObject(left)) equipment.push_back(Form(item));
    bool ignored = false;
    return {{"reference", Form(actor)}, {"base", Form(base)}, {"race", Form(actor->GetRace())},
            {"voice", Form(base ? base->voiceType : nullptr)},
            {"sex", base ? json(static_cast<int>(base->GetSex())) : json(nullptr)},
            {"in_combat", actor->IsInCombat()}, {"dead", actor->IsDead()}, {"weapon_drawn", actor->AsActorState()->IsWeaponDrawn()},
            {"sees_player", actor == player || actor->HasLineOfSight(player, ignored)},
            {"hostile_to_player", actor != player && actor->IsHostileToActor(player)},
            {"factions", factions}, {"equipment", equipment}};
}
class HttpHandle {
public:
    HINTERNET handle;
    explicit HttpHandle(HINTERNET value) : handle(value) {}
    ~HttpHandle() { if (handle) WinHttpCloseHandle(handle); }
    HttpHandle(const HttpHandle&) = delete;
};
struct HttpError : std::runtime_error {
    DWORD status;
    bool resync;
    HttpError(DWORD value, bool reset) : std::runtime_error(std::format("bridge HTTP {}", value)), status(value), resync(reset) {}
};
class DialogueLock {
    CRITICAL_SECTION* section;
public:
    explicit DialogueLock(RE::MenuTopicManager* manager) : section(reinterpret_cast<CRITICAL_SECTION*>(&manager->criticalSection)) { EnterCriticalSection(section); }
    ~DialogueLock() { LeaveCriticalSection(section); }
};

void BuildVoice(RE::BSSoundHandle& sound, const char* path)
{
    RE::BSResource::ID resource{};
    resource.GenerateFromPath(path);
    RE::BSAudioManager::GetSingleton()->GetSoundHandleByFile(sound, resource, 0x1A, 128);
    if (!sound.IsValid()) return;
    sound.SetVolume(1.0F);
    if (auto defaults = RE::BGSDefaultObjectManager::GetSingleton())
        if (auto output = defaults->GetObject<RE::BGSSoundOutput>(RE::DEFAULT_OBJECT::kDialogueOutputModel3D))
            sound.SetOutputModel(output);
}

class Connector final : public RE::BSTEventSink<RE::MenuOpenCloseEvent>, public RE::BSTEventSink<RE::InputEvent*>, public RE::BSTEventSink<SKSE::ModCallbackEvent> {
public:
    static Connector& Get() { static auto* instance = new Connector; return *instance; }
    void Initialize()
    {
        auto path = std::filesystem::absolute("Data/SKSE/Plugins/AnimaConnector.ini").wstring();
        port = static_cast<INTERNET_PORT>(GetPrivateProfileIntW(L"Connection", L"Port", 8768, path.c_str()));
        pttKey = GetPrivateProfileIntW(L"Connection", L"PushToTalkKey", 66, path.c_str());
        menuKey = GetPrivateProfileIntW(L"Connection", L"ConversationMenuKey", 65, path.c_str());
        SKSE::GetModCallbackEventSource()->AddEventSink(this);
        animateMouth = GetPrivateProfileIntW(L"Connection", L"AnimateMouth", 1, path.c_str()) != 0;
        ResetEpoch();
        RE::UI::GetSingleton()->AddEventSink<RE::MenuOpenCloseEvent>(this);
        if (auto input = RE::BSInputDeviceManager::GetSingleton()) input->AddEventSink(this);
        std::thread([this] { Worker(); }).detach();
        SKSE::log::info("AnimaConnector initialized on port {}", port);
    }
    void ResetEpoch()
    {
        End();
        epoch = std::format("{}-{}-{}", GetCurrentProcessId(), UtcMs(), ++serial);
        open = false;
    }
    RE::BSEventNotifyControl ProcessEvent(const RE::MenuOpenCloseEvent* event, RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override
    {
        if (event && event->menuName == RE::DialogueMenu::MENU_NAME) {
            open = event->opening;
            openedAt = Clock::now();
            if (!open) End();
        }
        return RE::BSEventNotifyControl::kContinue;
    }
    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent* const* events, RE::BSTEventSource<RE::InputEvent*>*) override
    {
        if (!events || session.empty()) return RE::BSEventNotifyControl::kContinue;
        for (auto event = *events; event; event = event->next) {
            auto button = event->AsButtonEvent();
            if (!button || event->GetDevice() != RE::INPUT_DEVICE::kKeyboard) continue;
            if (button->idCode == menuKey && button->IsDown()) { OpenUi(anima::Panel::options); continue; }
            if (button->idCode != pttKey || RE::UI::GetSingleton()->IsMenuOpen("CustomMenu")) continue;
            if (button->IsDown()) {
                if (!BargeIn()) continue; listening = true; Notify("ANIMA: listening while F8 is held..."); Queue(Event("listen_start"));
            } else if (button->IsUp() && listening) {
                listening = false; Notify("ANIMA: transcribing..."); Queue(Event("listen_stop"));
            }
        }
        return RE::BSEventNotifyControl::kContinue;
    }
    RE::BSEventNotifyControl ProcessEvent(const SKSE::ModCallbackEvent* event, RE::BSTEventSource<SKSE::ModCallbackEvent>*) override
    {
        if (!event) return RE::BSEventNotifyControl::kContinue;
        const std::string name = event->eventName.c_str(), text = event->strArg.c_str();
        if ((name.starts_with("UIListMenu_") || name.starts_with("UITextEntryMenu_")) && text.size() <= 4000) {
            std::scoped_lock lock(mutex);
            if (uiEvents.size() < 8) uiEvents.push_back({{"name", name}, {"text", text}});
        }
        return RE::BSEventNotifyControl::kContinue;
    }
private:
    std::atomic_bool taskPending{false}, resync{false};
    std::mutex mutex;
    std::deque<json> outgoing, commands, uiEvents;
    anima::UiState uiState;
    std::atomic<anima::Panel> uiRenderPanel{anima::Panel::none};
    std::atomic_uint64_t uiRenderGeneration{0}, uiProbeGeneration{0};
    std::atomic_bool uiTaskPending{false}, uiFilled{false};
    int nextUi = -1;
    Clock::time_point uiOpenedAt;
    std::string workerSession, session, epoch, lastSnapshot, delivery, subtitleText;
    RE::ActorHandle speaker;
    RE::BSSoundHandle sound;
    anima::AudioState audioState;
    std::int64_t audioStartExpiry = 0;
    std::unordered_set<std::string> seen;
    std::uint64_t serial = 0, sequence = 0, snapshotSequence = 0;
    INTERNET_PORT port = 8768;
    std::uint32_t pttKey = 66, menuKey = 65;
    bool open = false, listening = false, animateMouth = true, audioStarted = false, endAfter = false, mouthOwned = false;
    float originalMouth = 0;
    std::vector<float> mouth;
    Clock::time_point openedAt, lastCapture, playbackStart, playbackEnd;

    void Notify(const char* text)
    {
        auto vm = RE::BSScript::Internal::VirtualMachine::GetSingleton();
        RE::BSTSmartPointer<RE::BSScript::IStackCallbackFunctor> callback;
        if (vm) vm->DispatchStaticCall("Debug", "Notification", RE::MakeFunctionArguments(RE::BSFixedString(text)), callback);
    }
    bool CallUi(const char* function, const char* movie = nullptr)
    {
        auto vm = RE::BSScript::Internal::VirtualMachine::GetSingleton();
        RE::BSTSmartPointer<RE::BSScript::IStackCallbackFunctor> callback;
        return vm && vm->DispatchStaticCall("UI", function,
            movie ? RE::MakeFunctionArguments(RE::BSFixedString(movie), std::int32_t(0)) : RE::MakeFunctionArguments(), callback);
    }
    void OpenUi(anima::Panel panel)
    {
        if (!open || session.empty() || RE::UI::GetSingleton()->IsMenuOpen("CustomMenu")) return;
        if (!uiState.Open(session, panel)) return;
        uiOpenedAt = Clock::now();
        uiRenderPanel = panel; uiRenderGeneration = uiState.generation; uiFilled = false;
        if (!CallUi("OpenCustomMenu", panel == anima::Panel::text ? "textentrymenu" : "listmenu")) {
            CancelUi(); Notify("ANIMA: UIExtensions menu unavailable.");
        } else {
            Notify(panel == anima::Panel::text ? "ANIMA: type a message, Enter sends, Escape cancels." : "ANIMA conversation controls");
            SKSE::log::info("ANIMA menu opened; session={}", session);
        }
    }
    void CancelUi()
    {
        uiState.Cancel(); uiRenderPanel = anima::Panel::none; uiRenderGeneration = uiState.generation; uiFilled = false;
    }
    void RenderUi(std::uint64_t generation)
    {
        if (generation != uiRenderGeneration || uiFilled) return;
        auto panel = uiRenderPanel.load();
        auto menu = RE::UI::GetSingleton()->GetMenu("CustomMenu");
        if (panel == anima::Panel::none || !menu || !menu->uiMovie) return;
        RE::GFxValue root;
        const auto path = panel == anima::Panel::options ? "_root.listMenu" : "_root.textEntry";
        const bool found = menu->uiMovie->GetVariable(&root, path) && root.IsObject();
        if (uiProbeGeneration.exchange(generation) != generation)
            SKSE::log::info("ANIMA UI task executing; panel={} root={} available={}", static_cast<int>(panel), path, found);
        if (!found) return;
        if (generation != uiRenderGeneration) return;
        bool populated = false;
        if (panel == anima::Panel::options) {
            // Match SKSE UI.InvokeStringA: one scalar argument per entry, not one GFx array.
            std::array<RE::GFxValue, anima::MenuEntries.size()> entries;
            for (std::size_t i = 0; i < entries.size(); ++i) entries[i].SetString(anima::MenuEntries[i]);
            populated = menu->uiMovie->Invoke("_root.listMenu.LM_AddTreeEntries", nullptr, entries.data(), entries.size());
            RE::GFxValue sort(false); menu->uiMovie->Invoke("_root.listMenu.LM_SetSortingEnabled", nullptr, &sort, 1);
        } else {
            RE::GFxValue empty; empty.SetString("");
            populated = menu->uiMovie->Invoke("_root.textEntry.setTextEntryMenuText", nullptr, &empty, 1);
        }
        if (generation != uiRenderGeneration) return;
        uiFilled = populated;
        if (populated) SKSE::log::info("ANIMA UI-thread population succeeded; panel={} generation={}", static_cast<int>(panel), generation);
    }
    void ProcessUi()
    {
        std::deque<json> events;
        { std::scoped_lock lock(mutex); events.swap(uiEvents); }
        for (const auto& item : events) {
            const auto name = item.value("name", ""), text = item.value("text", "");
            if (uiState.Owns(session, anima::Panel::options)) {
                if (name == "UIListMenu_LoadMenu") {
                    SKSE::log::info("ANIMA UIExtensions list load callback received");
                } else if (name == "UIListMenu_SelectItem" && (text == "0" || text == "1" || text == "2")) {
                    nextUi = text[0] - '0'; CancelUi();
                } else if (name == "UIListMenu_CloseMenu") { CancelUi(); }
            } else if (uiState.Owns(session, anima::Panel::text)) {
                if (name == "UITextEntryMenu_LoadMenu") {
                    SKSE::log::info("ANIMA UIExtensions text load callback received");
                } else if (name == "UITextEntryMenu_TextChanged") {
                    if (uiState.CanSubmit(session, text) && BargeIn()) { Notify("ANIMA: sending your message..."); auto event = Event("player_text"); event["text"] = text; Queue(std::move(event)); }
                    CancelUi();
                } else if (name == "UITextEntryMenu_CloseMenu") { CancelUi(); }
            }
        }
        if (!RE::UI::GetSingleton()->IsMenuOpen("CustomMenu")) {
            const auto choice = nextUi; nextUi = -1;
            if (choice == 0) OpenUi(anima::Panel::text);
            else if (choice == 1) Notify("ANIMA: hold F8 to speak; release to send.");
            else if (choice == 2) RE::UIMessageQueue::GetSingleton()->AddMessage(RE::DialogueMenu::MENU_NAME, RE::UI_MESSAGE_TYPE::kHide, nullptr);
            else if (uiState.panel != anima::Panel::none && Clock::now() - uiOpenedAt > std::chrono::seconds(5)) CancelUi();
        }
    }

    bool BargeIn()
    {
        auto actor = speaker.get();
        if (session.empty() || !open || !actor || actor->IsInCombat() || actor->IsDead()) return false;
        Stop("interrupted"); actor->StopCurrentDialogue();
        if (session.empty() || !open) return false;
        // Invalidate both downloaded and in-flight commands before admitting new input.
        ++snapshotSequence;
        auto data = Snapshot(actor.get()); lastSnapshot = Fingerprint(data);
        auto event = Event("snapshot"); event["snapshot"] = data; Queue(std::move(event));
        lastCapture = Clock::now();
        return true;
    }

    json Event(const char* kind)
    {
        ++sequence;
        return {{"schema_version", "0.1"}, {"event_id", std::format("{}:{}", session, sequence)},
                {"session_id", session}, {"game_epoch", epoch}, {"sequence", sequence},
                {"state_revision", snapshotSequence}, {"captured_at_ms", UtcMs()},
                {"game_pid", GetCurrentProcessId()}, {"kind", kind}};
    }
    void Queue(json event)
    {
        std::scoped_lock lock(mutex);
        if (event["kind"] == "snapshot")
            std::erase_if(outgoing, [](const json& item) { return item["kind"] == "snapshot"; });
        if (outgoing.size() >= 32) { SKSE::log::error("Connector queue full"); return; }
        outgoing.push_back(std::move(event));
    }
    json Snapshot(RE::Actor* actor)
    {
        auto player = RE::PlayerCharacter::GetSingleton();
        auto manager = RE::MenuTopicManager::GetSingleton();
        json dialogue = json::array();
        bool complete = true;
        {
        DialogueLock lock(manager);
        if (manager->dialogueList) {
            for (auto choice : *manager->dialogueList) {
                if (!choice || !choice->parentTopic) continue;
                if (dialogue.size() >= 16) { complete = false; break; }
                json responses = json::array();
                for (auto response : choice->responses) {
                    if (response && responses.size() < 8) responses.push_back(Text(response->text.c_str()));
                    else if (response) complete = false;
                }
                auto quest = choice->parentQuest;
                dialogue.push_back({{"topic", Form(choice->parentTopic)}, {"info", Form(choice->parentTopicInfo)},
                    {"player_text", Text(choice->topicText.c_str())}, {"responses", responses}, {"quest", Form(quest)},
                    {"quest_stage", quest ? json(quest->GetCurrentStageID()) : json(nullptr)}, {"provenance", "engine_dialogue_menu"}});
            }
        } else complete = false;
        }
        auto cell = actor->GetParentCell();
        bool interior = cell && cell->IsInteriorCell();
        auto sky = RE::Sky::GetSingleton();
        auto calendar = RE::Calendar::GetSingleton();
        return {{"npc", Actor(actor, player)}, {"player", Actor(player, player)},
                {"location", Form(actor->GetCurrentLocation())}, {"cell", Form(cell)}, {"interior", interior},
                {"hour", std::floor(calendar->GetHour() * 100) / 100}, {"game_days", calendar->GetDaysPassed()},
                {"weather", !interior && sky ? Form(sky->currentWeather) : json(nullptr)},
                {"weather_label", interior || !sky ? json(nullptr) : json(sky->IsSnowing() ? "snowing" : sky->IsRaining() ? "raining" : "not_raining_or_snowing")},
                {"dialogue", dialogue}, {"dialogue_complete", complete}};
    }
    static std::string Fingerprint(json value)
    {
        value.erase("game_days"); value.erase("hour");
        return value.dump();
    }
    void Tick()
    {
        if (resync.exchange(false)) {
            End(false);
            std::scoped_lock lock(mutex); outgoing.clear();
        }
        auto now = Clock::now();
        ProcessUi();
        if (open && now - openedAt > std::chrono::milliseconds(350)) {
            auto manager = RE::MenuTopicManager::GetSingleton();
            auto reference = manager ? manager->speaker.get() : RE::NiPointer<RE::TESObjectREFR>();
            auto actor = reference ? reference->As<RE::Actor>() : nullptr;
            if (actor && actor != RE::PlayerCharacter::GetSingleton() && actor->GetActorBase()) {
                if (actor->IsInCombat() || actor->IsDead()) { End(); return; }
                if (session.empty() || speaker.get().get() != actor) {
                    End(); session = std::format("{}-{}", epoch, ++serial); sequence = 0;
                    speaker = actor->GetHandle();
                    snapshotSequence = 1;
                    auto data = Snapshot(actor); auto event = Event("start");
                    event["snapshot"] = data; lastSnapshot = Fingerprint(data); Queue(std::move(event));
                    lastCapture = now;
                    std::scoped_lock lock(mutex); workerSession = session;
                } else if (now - lastCapture >= std::chrono::seconds(1)) {
                    lastCapture = now;
                    auto data = Snapshot(actor); auto fingerprint = Fingerprint(data);
                    if (fingerprint != lastSnapshot) { Stop("interrupted"); ++snapshotSequence; }
                    auto event = Event("snapshot"); event["snapshot"] = data;
                    lastSnapshot = std::move(fingerprint); Queue(std::move(event));
                }
            } else if (!session.empty()) End();
        }
        std::deque<json> ready;
        { std::scoped_lock lock(mutex); ready.swap(commands); }
        for (const auto& command : ready) {
            try { Apply(command); }
            catch (const std::exception& e) { SKSE::log::error("Rejected command: {}", e.what()); }
        }
        if (delivery.empty()) return;
        auto actor = speaker.get();
        if (!actor || !open || actor->IsInCombat() || actor->IsDead()) Stop("interrupted");
        else if (audioStarted) {
            const auto current = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
            if (!audioState.observed && UtcMs() >= audioStartExpiry) { Stop("failed"); return; }
            const auto decision = audioState.Update(current, sound.IsPlaying());
            if (decision == anima::AudioDecision::started) {
                playbackStart = now;
                SKSE::log::info("ANIMA observed native audio playing; delivery={} soundID={}", delivery, sound.soundID);
                Ack(delivery, "started");
            } else if (decision == anima::AudioDecision::failed) {
                SKSE::log::error("ANIMA audio failed: observedPlaying={} soundID={}", audioState.observed, sound.soundID);
                Stop("failed");
            } else if (decision == anima::AudioDecision::interrupted) Stop("interrupted");
            else if (decision == anima::AudioDecision::completed) {
                const auto closeMenu = endAfter; Stop("completed");
                if (closeMenu) RE::UIMessageQueue::GetSingleton()->AddMessage(RE::DialogueMenu::MENU_NAME, RE::UI_MESSAGE_TYPE::kHide, nullptr);
            }
        }
        else if (now >= playbackEnd) {
            auto closeMenu = endAfter; Stop("completed");
            if (closeMenu) RE::UIMessageQueue::GetSingleton()->AddMessage(RE::DialogueMenu::MENU_NAME, RE::UI_MESSAGE_TYPE::kHide, nullptr);
        }
        if (!delivery.empty() && mouthOwned && (!audioStarted || audioState.observed) && !mouth.empty()) {
            auto face = actor->GetFaceGenAnimationData();
            auto index = static_cast<std::size_t>(std::chrono::duration<float>(now - playbackStart).count() * 20);
            if (face && face->phenomeKeyFrame.count && face->phenomeKeyFrame.values) {
                RE::BSSpinLockGuard lock(face->lock);
                face->phenomeKeyFrame.SetValue(0, index < mouth.size() ? mouth[index] : 0.0F);
            }
        }
    }
    void AddSubtitle(RE::Actor* actor, const std::string& text)
    {
        if (text.empty()) return;
        if (auto manager = RE::SubtitleManager::GetSingleton()) {
            RE::BSSpinLockGuard lock(manager->lock);
            RE::SubtitleInfo info{};
            info.speaker = actor->GetHandle(); info.subtitle = text.c_str(); info.targetDistance = 10000; info.forceDisplay = true;
            manager->subtitles.push_back(info); subtitleText = text;
        }
    }
    void Apply(const json& command)
    {
        auto kind = command.value("kind", "idle");
        if (kind == "idle" || command.value("session_id", "") != session || session.empty()) return;
        auto id = command.value("delivery_id", "");
        if (kind == "stop") {
            if (delivery == id) Stop("interrupted");
            else if (!seen.contains(id)) Ack(id, "interrupted");
            seen.insert(id); return;
        }
        if (kind != "speak" || seen.contains(id)) return;
        auto actor = speaker.get();
        const auto target = command.value("npc_id", "");
        const auto expected = actor ? std::format("ref:{:08x}", actor->GetFormID()) : "";
        const auto requestSession = command.value("session_id", "");
        const bool ready = actor && open && !actor->IsInCombat() && !actor->IsDead() && seen.size() < 128;
        auto manager = RE::MenuTopicManager::GetSingleton();
        const auto targetHandle = actor ? static_cast<RE::TESObjectREFR*>(actor.get())->GetHandle() : RE::ObjectRefHandle{};
        const auto decision = anima::EvaluateDialogue(
            {requestSession, target, id, command.value("snapshot_sequence", 0ULL), command.value("expires_at_ms", 0LL), command.value("text", "").size()},
            {session, expected, snapshotSequence, UtcMs(), ready, false, seen.contains(id)}, manager, targetHandle);
        if (decision == anima::Decision::ignore || decision == anima::Decision::wait) return;
        if (decision == anima::Decision::reject) {
            Ack(id, "failed"); seen.insert(id); return;
        }
        if (command.value("mode", "speech") == "silence") { seen.insert(id); Ack(id, "completed"); return; }
        Stop("interrupted"); delivery = id; seen.insert(id); audioStarted = false;
        if (command.contains("audio_file") && !command["audio_file"].is_null()) {
            auto path = command["audio_file"].get<std::string>();
            if (path != std::format("Sound/Voice/AnimaConnector/{}.wav", id) || !std::filesystem::exists(std::filesystem::path("Data") / path)) {
                Stop("failed"); return;
            }
            std::replace(path.begin(), path.end(), '/', '\\');
            RE::BSResourceNiBinaryStream resource(path);
            SKSE::log::info("ANIMA audio resource: delivery={} good={} error={} priority=128", id, resource.good(), static_cast<int>(resource.lastError));
            if (!resource.good()) { Stop("failed"); return; }
            sound = RE::BSSoundHandle{};
            BuildVoice(sound, path.c_str());
            sound.SetPosition(actor->GetPosition());
            if (auto node = actor->Get3D()) sound.SetObjectToFollow(node);
            if (!sound.IsValid() || !sound.Play()) { Stop("failed"); return; }
            audioStarted = true;
        }
        AddSubtitle(actor.get(), command.value("text", "")); mouth.clear();
        if (animateMouth && audioStarted && command.contains("mouth") && command["mouth"].is_array() && command["mouth"].size() <= 600) {
            for (const auto& value : command["mouth"]) mouth.push_back(std::clamp(value.get<float>(), 0.0F, 1.0F));
            if (auto face = actor->GetFaceGenAnimationData(); face && face->phenomeKeyFrame.count && face->phenomeKeyFrame.values) {
                RE::BSSpinLockGuard lock(face->lock); originalMouth = face->phenomeKeyFrame.values[0]; mouthOwned = true;
            }
        }
        auto duration = std::clamp(command.value("duration_s", 3.0), 0.05, 30.0);
        playbackStart = Clock::now(); playbackEnd = playbackStart + std::chrono::milliseconds(static_cast<int>(duration * 1000));
        endAfter = command.value("mode", "speech") == "end";
        if (audioStarted) {
            audioStartExpiry = command.value("expires_at_ms", 0LL);
            audioState.Begin(std::chrono::duration_cast<std::chrono::milliseconds>(playbackStart.time_since_epoch()).count(),
                             static_cast<std::int64_t>(duration * 1000));
        } else Ack(id, "started");
    }
    void Ack(const std::string& id, const char* status)
    {
        if (session.empty() || id.empty()) return;
        auto event = Event("delivery"); event["delivery_id"] = id; event["status"] = status; Queue(std::move(event));
    }
    void Stop(const char* status)
    {
        if (delivery.empty()) return;
        if (audioStarted) sound.Stop();
        auto actor = speaker.get();
        if (mouthOwned && actor) {
            if (auto face = actor->GetFaceGenAnimationData(); face && face->phenomeKeyFrame.count && face->phenomeKeyFrame.values) {
                RE::BSSpinLockGuard lock(face->lock); face->phenomeKeyFrame.SetValue(0, originalMouth);
            }
        }
        if (!subtitleText.empty()) {
            if (auto manager = RE::SubtitleManager::GetSingleton()) {
                RE::BSSpinLockGuard lock(manager->lock);
                for (auto it = manager->subtitles.begin(); it != manager->subtitles.end();) {
                    if (it->speaker == speaker && subtitleText == it->subtitle.c_str()) it = manager->subtitles.erase(it);
                    else ++it;
                }
            }
        }
        subtitleText.clear(); mouthOwned = false; audioStarted = false; Ack(delivery, status); delivery.clear();
    }
    void End(bool notify = true)
    {
        if (uiState.panel != anima::Panel::none) CallUi("CloseCustomMenu");
        CancelUi(); nextUi = -1;
        Stop("interrupted");
        if (notify && !session.empty()) Queue(Event("end"));
        session.clear(); seen.clear(); listening = false;
        std::scoped_lock lock(mutex); workerSession.clear(); commands.clear();
    }
    json Request(const wchar_t* method, const std::wstring& path, const std::string& body = "")
    {
        HttpHandle http(WinHttpOpen(L"AnimaConnector/0.1", WINHTTP_ACCESS_TYPE_NO_PROXY, nullptr, nullptr, 0));
        if (!http.handle) throw std::runtime_error("WinHTTP failed");
        WinHttpSetTimeouts(http.handle, 300, 300, 500, 500);
        HttpHandle connection(WinHttpConnect(http.handle, L"127.0.0.1", port, 0));
        HttpHandle request(WinHttpOpenRequest(connection.handle, method, path.c_str(), nullptr, nullptr, nullptr, 0));
        if (!request.handle || !WinHttpSendRequest(request.handle, L"Content-Type: application/json\r\n", static_cast<DWORD>(-1L),
            body.empty() ? WINHTTP_NO_REQUEST_DATA : const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
            static_cast<DWORD>(body.size()), 0) || !WinHttpReceiveResponse(request.handle, nullptr)) throw std::runtime_error("bridge unavailable");
        DWORD status = 0, size = sizeof(status);
        WinHttpQueryHeaders(request.handle, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, nullptr, &status, &size, nullptr);
        std::string received; char buffer[4096]; DWORD read = 0;
        while (WinHttpReadData(request.handle, buffer, sizeof(buffer), &read) && read) {
            received.append(buffer, read);
            if (received.size() > 65536) throw std::runtime_error("oversized command");
        }
        if (status < 200 || status >= 300) {
            const auto error = json::parse(received, nullptr, false);
            const auto reason = error.is_object() && error.contains("error") && error["error"].is_string() ? error["error"].get<std::string>() : "";
            throw HttpError(status, anima::RequiresResync(status, reason));
        }
        return received.empty() ? json::object() : json::parse(received);
    }
    void Worker()
    {
        auto lastWarning = Clock::now() - std::chrono::seconds(30);
        while (true) {
            if (uiRenderPanel != anima::Panel::none && !uiFilled && !uiTaskPending.exchange(true)) {
                auto generation = uiRenderGeneration.load();
                SKSE::GetTaskInterface()->AddUITask([this, generation] {
                    try { RenderUi(generation); } catch (const std::exception& e) { SKSE::log::error("ANIMA UI render failed: {}", e.what()); }
                    uiTaskPending = false;
                });
            }
            if (!taskPending.exchange(true)) SKSE::GetTaskInterface()->AddTask([this] {
                try { Tick(); } catch (const std::exception& e) { SKSE::log::error("Observation failed: {}", e.what()); }
                taskPending = false;
            });
            json next; std::string current;
            { std::scoped_lock lock(mutex); if (!outgoing.empty()) next = outgoing.front(); current = workerSession; }
            try {
                if (!next.is_null()) {
                    Request(L"POST", L"/v1/game/event", next.dump(-1, ' ', false, json::error_handler_t::replace));
                    std::scoped_lock lock(mutex);
                    if (!outgoing.empty() && outgoing.front()["event_id"] == next["event_id"]) outgoing.pop_front();
                }
                if (!current.empty()) {
                    auto result = Request(L"GET", L"/v1/game/command?session_id=" + std::wstring(current.begin(), current.end()));
                    if (result.value("kind", "idle") != "idle") { std::scoped_lock lock(mutex); if (commands.size() < 4) commands.push_back(std::move(result)); }
                }
            } catch (const HttpError& e) {
                SKSE::log::warn("Bridge rejected request: {}", e.what());
                if (e.status >= 400 && e.status < 500) {
                    std::scoped_lock lock(mutex);
                    if (!outgoing.empty() && !next.is_null() && outgoing.front()["event_id"] == next["event_id"]) outgoing.pop_front();
                    if (e.resync) resync = true;
                }
            } catch (const std::exception& e) {
                if (Clock::now() - lastWarning > std::chrono::seconds(10)) { SKSE::log::warn("Bridge: {}", e.what()); lastWarning = Clock::now(); }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
};
}
extern "C" __declspec(dllexport) constinit SKSE::PluginVersionData SKSEPlugin_Version = anima::VersionMetadata();
extern "C" __declspec(dllexport) bool SKSEPlugin_Load(const SKSE::LoadInterface* skse)
{
    // Admission uses SKSE's supplied runtime before touching engine relocations.
    const auto version = skse->RuntimeVersion();
    if (!anima::SupportsRuntime({version.major(), version.minor(), version.patch(), version.build()})) {
        OutputDebugStringA("AnimaConnector: unsupported Skyrim runtime; supported: 1.6.318.0 and 1.7.104.0\n");
        return false;
    }
    if (auto directory = SKSE::log::log_directory()) {
        auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((*directory / "AnimaConnector.log").string(), true);
        spdlog::set_default_logger(std::make_shared<spdlog::logger>("AnimaConnector", sink)); spdlog::flush_on(spdlog::level::info);
    }
    std::array<wchar_t,32768> executable{};
    const auto length = GetModuleFileNameW(nullptr, executable.data(), static_cast<DWORD>(executable.size()));
    if (!length || length >= executable.size()) {
        SKSE::log::error("Cannot locate the game executable for Address Library preflight");
        return false;
    }
    const auto library = std::filesystem::path(executable.data()).parent_path() / "Data/SKSE/Plugins" /
        std::format("versionlib-{}-{}-{}-{}.bin",version.major(),version.minor(),version.patch(),version.build());
    const auto check = anima::CheckAddressLibrary(library,{version.major(),version.minor(),version.patch(),version.build()});
    if (check != anima::LibraryCheck::ready) {
        SKSE::log::error("Address Library preflight failed ({}) for {}",static_cast<int>(check),library.string());
        return false;
    }
    SKSE::Init(skse);
    SKSE::log::info("AnimaConnector 0.3.0 loading on Skyrim {}; Address Library format {}", version.string(),
                   anima::AddressLibraryFormat({version.major(),version.minor(),version.patch(),version.build()}));
    return SKSE::GetMessagingInterface()->RegisterListener([](SKSE::MessagingInterface::Message* message) {
        if (message->type == SKSE::MessagingInterface::kDataLoaded) Connector::Get().Initialize();
        else if (message->type == SKSE::MessagingInterface::kPreLoadGame || message->type == SKSE::MessagingInterface::kNewGame) Connector::Get().ResetEpoch();
    });
}
