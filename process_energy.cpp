// macOS per-process accounting. OS energy estimate, not a physical wattmeter.
#include <libproc.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cerrno>
#include <cstdio>
#include <cstdint>
#include <chrono>

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "Usage: process_energy program [args]\n"); return 2; }
    const auto start = std::chrono::steady_clock::now();
    const pid_t pid = fork();
    if (pid < 0) { std::perror("fork"); return 1; }
    if (pid == 0) {
        execvp(argv[1], argv+1);
        std::perror("execvp");
        _exit(127);
    }
    siginfo_t exit_info{};
    while (waitid(P_PID, pid, &exit_info, WEXITED | WNOWAIT) < 0) {
        if (errno == EINTR) continue;
        std::perror("waitid"); return 1;
    }
    const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    rusage_info_v6 info{};
    const int rc = proc_pid_rusage(pid, RUSAGE_INFO_V6, reinterpret_cast<rusage_info_t*>(&info));
    if (rc != 0) std::perror("proc_pid_rusage");
    int status = 0;
    while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
    if (rc != 0) return 1;
    std::fprintf(stderr,
        "seconds=%.9f energy_nj=%llu performance_core_energy_nj=%llu instructions=%llu cycles=%llu\n",
        seconds, (unsigned long long)info.ri_energy_nj, (unsigned long long)info.ri_penergy_nj,
        (unsigned long long)info.ri_instructions, (unsigned long long)info.ri_cycles);
    if (info.ri_energy_nj == 0) {
        std::fprintf(stderr, "Energy counter unavailable or zero; do not report zero joules as measured energy.\n");
        return 3;
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
