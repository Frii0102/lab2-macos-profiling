#include <cstddef>
#include <cstdint>

// Окремий файл без LTO: компілятор не видаляє повторні виклики з main.
void transform(const std::uint32_t* input, std::uint32_t* output, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) {
        output[i] = input[i] * 2u + 1u;
    }
}
