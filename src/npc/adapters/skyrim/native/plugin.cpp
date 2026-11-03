// Independently authored. No Mantella source or binary dependency.
#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <Windows.h>
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
    explicit HttpError(DWORD value) : std::runtime_error(std::format("bridge HTTP {}", value)), status(value) {}
};
class DialogueLock {
    CRITICAL_SECTION* section;
public:
    explicit DialogueLock(RE::MenuTopicManager* manager) : section(reinterpret_cast<CRITICAL_SECTION*>(&manager->criticalSection)) { EnterCriticalSection(section); }
    ~DialogueLock() { LeaveCriticalSection(section); }
};

void BuildVoice(RE::BSSoundHandle& sound, const char* path)
{
    // Engine entry points documented by CommonLibSSE-NG (MIT), upstream b93280e.
    // 3.7.0 has the ABI types but predates these two convenience wrappers.
    RE::BSResource::ID resource{};
    using Resolve = void (*)(RE::BSResource::ID*, const char*);
    REL::Relocation<Resolve> resolve{REL::RelocationID{68635, 69979}};
    resolve(&resource, path);
    using Build = void (*)(RE::BSAudioManager*, RE::BSSoundHandle&, const RE::BSResource::ID&, std::uint32_t, std::uint32_t);
    REL::Relocation<Build> build{REL::RelocationID{66402, 67664}};
    build(RE::BSAudioManager::GetSingleton(), sound, resource, 0x1A, 0);
}

class Connector final : public RE::BSTEventSink<RE::MenuOpenCloseEvent>, public RE::BSTEventSink<RE::InputEvent*> {
public:
    static Connector& Get() { static auto* instance = new Connector; return *instance; }
    void Initialize()
    {
        auto path = std::filesystem::absolute("Data/SKSE/Plugins/AnimaConnector.ini").wstring();
        port = static_cast<INTERNET_PORT>(GetPrivateProfileIntW(L"Connection", L"Port", 8768, path.c_str()));
        pttKey = GetPrivateProfileIntW(L"Connection", L"PushToTalkKey", 66, path.c_str());
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
            if (!button || event->GetDevice() != RE::INPUT_DEVICE::kKeyboard || button->idCode != pttKey) continue;
            if (button->IsDown()) {
                Stop("interrupted"); listening = true; Queue(Event("listen_start"));
            } else if (button->IsUp() && listening) {
                listening = false; Queue(Event("listen_stop"));
            }
        }
        return RE::BSEventNotifyControl::kContinue;
    }
private:
    std::atomic_bool taskPending{false}, resync{false};
    std::mutex mutex;
    std::deque<json> outgoing, commands;
    std::string workerSession, session, epoch, lastSnapshot, delivery, subtitleText;
    RE::ActorHandle speaker;
    RE::BSSoundHandle sound;
    std::unordered_set<std::string> seen;
    std::uint64_t serial = 0, sequence = 0, snapshotSequence = 0;
    INTERNET_PORT port = 8768;
    std::uint32_t pttKey = 66;
    bool open = false, listening = false, animateMouth = true, audioStarted = false, endAfter = false, mouthOwned = false;
    float originalMouth = 0;
    std::vector<float> mouth;
    Clock::time_point openedAt, lastCapture, playbackStart, playbackEnd;

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
        else if (now >= playbackEnd) {
            auto closeMenu = endAfter; Stop("completed");
            if (closeMenu) RE::UIMessageQueue::GetSingleton()->AddMessage(RE::DialogueMenu::MENU_NAME, RE::UI_MESSAGE_TYPE::kHide, nullptr);
        } else if (audioStarted && now - playbackStart > std::chrono::milliseconds(500) && !sound.IsPlaying()) Stop("interrupted");
        else if (mouthOwned && !mouth.empty()) {
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
        const auto decision = anima::Evaluate(
            {requestSession, target, id, command.value("snapshot_sequence", 0ULL), command.value("expires_at_ms", 0LL), command.value("text", "").size()},
            {session, expected, snapshotSequence, UtcMs(), ready, RE::MenuTopicManager::GetSingleton()->currentTopicInfo != nullptr, seen.contains(id)});
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
        endAfter = command.value("mode", "speech") == "end"; Ack(id, "started");
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
        if (status < 200 || status >= 300) throw HttpError(status);
        std::string received; char buffer[4096]; DWORD read = 0;
        while (WinHttpReadData(request.handle, buffer, sizeof(buffer), &read) && read) {
            received.append(buffer, read);
            if (received.size() > 65536) throw std::runtime_error("oversized command");
        }
        return received.empty() ? json::object() : json::parse(received);
    }
    void Worker()
    {
        auto lastWarning = Clock::now() - std::chrono::seconds(30);
        while (true) {
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
                    if (e.status == 409) resync = true;
                }
            } catch (const std::exception& e) {
                if (Clock::now() - lastWarning > std::chrono::seconds(10)) { SKSE::log::warn("Bridge: {}", e.what()); lastWarning = Clock::now(); }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
};
}
extern "C" __declspec(dllexport) constinit SKSE::PluginVersionData SKSEPlugin_Version = [] {
    SKSE::PluginVersionData data;
    data.PluginVersion({0, 1, 0, 0}); data.PluginName("AnimaConnector"); data.AuthorName("Anima project");
    data.UsesAddressLibrary(); data.CompatibleVersions({REL::Version{1, 6, 318, 0}}); return data;
}();
extern "C" __declspec(dllexport) bool SKSEPlugin_Load(const SKSE::LoadInterface* skse)
{
    SKSE::Init(skse);
    if (REL::Module::get().version() != REL::Version{1, 6, 318, 0}) return false;
    if (auto directory = SKSE::log::log_directory()) {
        auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((*directory / "AnimaConnector.log").string(), true);
        spdlog::set_default_logger(std::make_shared<spdlog::logger>("AnimaConnector", sink)); spdlog::flush_on(spdlog::level::info);
    }
    return SKSE::GetMessagingInterface()->RegisterListener([](SKSE::MessagingInterface::Message* message) {
        if (message->type == SKSE::MessagingInterface::kDataLoaded) Connector::Get().Initialize();
        else if (message->type == SKSE::MessagingInterface::kPreLoadGame || message->type == SKSE::MessagingInterface::kNewGame) Connector::Get().ResetEpoch();
    });
}
