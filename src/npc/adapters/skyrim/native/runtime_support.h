#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>

namespace anima {
struct RuntimeVersion {
    std::uint16_t major, minor, patch, build;
    constexpr bool operator==(const RuntimeVersion&) const = default;
};
inline constexpr std::array<RuntimeVersion, 2> SupportedRuntimes{{{1,6,318,0},{1,7,104,0}}};
constexpr bool SupportsRuntime(RuntimeVersion version)
{
    for (auto supported : SupportedRuntimes) if (version == supported) return true;
    return false;
}
constexpr std::uint32_t AddressLibraryFormat(RuntimeVersion version)
{
    return version == SupportedRuntimes[0] ? 2 : version == SupportedRuntimes[1] ? 5 : 0;
}
enum class LibraryCheck { ready, missing, wrong_format, unsupported_runtime };
inline LibraryCheck CheckAddressLibrary(const std::filesystem::path& path, RuntimeVersion version)
{
    const auto expected = AddressLibraryFormat(version);
    if (!expected) return LibraryCheck::unsupported_runtime;
    std::ifstream input(path, std::ios::binary);
    if (!input) return LibraryCheck::missing;
    std::array<unsigned char,4> bytes{};
    if (!input.read(reinterpret_cast<char*>(bytes.data()), bytes.size())) return LibraryCheck::wrong_format;
    const auto format = std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
                        (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
    return format == expected ? LibraryCheck::ready : LibraryCheck::wrong_format;
}
}
