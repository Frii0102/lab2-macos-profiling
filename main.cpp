#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

void transform(const std::uint32_t*, std::uint32_t*, std::size_t);

// Одна задача: для кожного числа обчислити число * 2 + 1.
// Аргументи: кількість чисел, повторення; або кількість чисел --seconds секунди.
int main(int argc, char** argv) {
    try {
        auto positive = [](const char* text) -> std::uint64_t {
            std::string s(text);
            if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
                throw std::runtime_error("Arguments must be positive integers");
            auto n = std::stoull(s);
            if (!n) throw std::runtime_error("Zero is not allowed");
            return n;
        };
        if (argc != 1 && argc != 3 && argc != 4)
            throw std::runtime_error("Usage: program [elements repetitions | elements --seconds seconds]");
        const auto n = argc == 1 ? 1000000ULL : positive(argv[1]);
        const bool timed = argc == 4 && std::string(argv[2]) == "--seconds";
        if (argc == 4 && !timed) throw std::runtime_error("Expected --seconds");
        const auto amount = argc == 1 ? 2000ULL : positive(argv[timed ? 3 : 2]);
        if (n > 20000000 || amount > (timed ? 120ULL : 1000000ULL))
            throw std::runtime_error("Workload exceeds safety limit");

        std::vector<std::uint32_t> input(n), output(n);
        for (std::size_t i = 0; i < n; ++i) input[i] = i % 1000;
        using Clock = std::chrono::steady_clock;
        const auto start = Clock::now();
        std::uint64_t completed = 0;
        double seconds = 0;
        do {
            transform(input.data(), output.data(), n);
            ++completed;
            seconds = std::chrono::duration<double>(Clock::now() - start).count();
        } while (timed ? seconds < amount : completed < amount);

        std::uint64_t checksum = 0;
        for (std::size_t i = 0; i < n; ++i) {
            if (output[i] != input[i] * 2u + 1u)
                throw std::runtime_error("Incorrect result");
            checksum += output[i];
        }
        std::cout << "mode=" << (timed ? "fixed-duration-profile" : "fixed-work")
                  << " elements=" << n << " repetitions=" << completed
                  << " kernel_seconds=" << seconds << " checksum=" << checksum
                  << " check=OK\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
