#include "runtime_support.h"
#include "ui_state.h"
#include "audio_state.h"
#include "version_metadata.h"
#include <chrono>
#include <iostream>
int main()
{
    int failures = 0;
    auto check = [&](bool ok,const char* label) { if (!ok) { std::cerr << label << '\n'; ++failures; } };


    check(anima::RequiresResync(409, "unknown or ended session"), "lost bridge session requests resync");
    check(!anima::RequiresResync(409, "turn or playback busy; interrupt playback before speaking again"), "busy is not session loss");
    check(!anima::RequiresResync(409, "unknown delivery"), "late delivery receipt does not reset conversation");
    check(!anima::RequiresResync(500, "unknown or ended session"), "server failure retries without reset");
    anima::AudioState audio;
    audio.Begin(100, 3000);
    check(audio.Update(600, false) == anima::AudioDecision::waiting, "queued Play is not observed start");
    check(audio.Update(2099, false) == anima::AudioDecision::waiting, "bounded decoder startup grace");
    check(audio.Update(2100, false) == anima::AudioDecision::failed, "never-started sound fails truthfully");
    audio.Begin(100, 3000);
    check(audio.Update(200, true) == anima::AudioDecision::started, "observed IsPlaying starts receipt");
    check(audio.Update(300, true) == anima::AudioDecision::playing, "playing sound stays active");
    check(audio.Update(800, false) == anima::AudioDecision::interrupted, "early stop is interruption");
    check(audio.Update(3200, false) == anima::AudioDecision::completed, "observed full playback completes");
    check(audio.Update(4800, true) == anima::AudioDecision::failed, "unexpected overlong audio is bounded");
    anima::UiState ui;
    check(!ui.Open("", anima::Panel::options), "UI rejects empty session");
    check(ui.Open("session-a", anima::Panel::text), "UI text ownership");
    check(!ui.Open("session-b", anima::Panel::options), "UI rejects competing owner");
    check(!ui.CanSubmit("session-b", "HELLO"), "UI rejects stale-session text");
    check(!ui.CanSubmit("session-a", " "), "UI rejects blank text");
    check(!ui.CanSubmit("session-a", std::string(4001, 'x')), "UI bounds text");
    check(ui.CanSubmit("session-a", "HELLO"), "UI accepts owned text");
    auto generation = ui.generation;
    ui.Cancel(); check(ui.generation != generation, "cancel invalidates queued UI generation"); check(!ui.CanSubmit("session-a", "HELLO"), "UI closes ownership");
    check(anima::SupportsRuntime({1,6,318,0}),"retain original AE runtime");
    check(anima::SupportsRuntime({1,7,104,0}),"accept installed AE runtime");
    for (auto v : {anima::RuntimeVersion{1,6,318,1},{1,7,104,1},{1,7,99,0},{1,6,1170,0},{1,4,15,0},{0,0,0,0}})
        check(!anima::SupportsRuntime(v),"reject unverified runtime/build");
    constexpr auto metadata=anima::VersionMetadata();
    check(metadata.versionIndependence==0,"legacy loader must not see unknown post-629 flags");
    check(metadata.versionIndependenceEx==SKSE::PluginVersionData::kVersionIndependentEx_AddressLibraryV5,"V5 flag without false NoStructUse claim");
    check(metadata.compatibleVersions[0]==REL::Version{1,6,318,0}.pack(),"legacy export target");
    check(metadata.compatibleVersions[1]==REL::Version{1,7,104,0}.pack() && metadata.compatibleVersions[2]==0,"new export target and terminator");
    namespace fs=std::filesystem;
    const auto root=fs::current_path() / ("anima-runtime-test-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(root);
    const auto library=root/"version.bin";
    check(anima::CheckAddressLibrary(library,{1,7,104,0})==anima::LibraryCheck::missing,"missing library fails before engine calls");
    { std::ofstream f(library,std::ios::binary); f.put(2);f.put(0);f.put(0);f.put(0); }
    check(anima::CheckAddressLibrary(library,{1,6,318,0})==anima::LibraryCheck::ready,"legacy format 2 retained");
    check(anima::CheckAddressLibrary(library,{1,7,104,0})==anima::LibraryCheck::wrong_format,"legacy library cannot service new runtime");
    { std::ofstream f(library,std::ios::binary); f.put(5);f.put(0);f.put(0);f.put(0); }
    check(anima::CheckAddressLibrary(library,{1,7,104,0})==anima::LibraryCheck::ready,"format 5 accepted");
    check(anima::CheckAddressLibrary(library,{1,6,318,0})==anima::LibraryCheck::wrong_format,"new library cannot service old runtime");
    { std::ofstream f(library,std::ios::binary); f.put(5); }
    check(anima::CheckAddressLibrary(library,{1,7,104,0})==anima::LibraryCheck::wrong_format,"truncated header rejected");
    check(anima::CheckAddressLibrary(library,{9,9,9,9})==anima::LibraryCheck::unsupported_runtime,"unknown version has no library assumption");
    fs::remove(library); fs::remove(root);
    return failures ? 1 : 0;
}
