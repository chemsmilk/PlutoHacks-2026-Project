// File: core/engine.cpp
// Compile command:
//   g++ -O3 -std=c++17 -Wall -Wextra core/engine.cpp -o engine

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace {

struct Config {
    std::size_t data_size = 100000;
    std::uint32_t seed = 42;
    std::string mode = "sort_stats";
};

std::string escape_json(const std::string& input) {
    std::ostringstream ss;
    for (char c : input) {
        switch (c) {
            case '"':  ss << "\\\""; break;
            case '\\': ss << "\\\\"; break;
            case '\b': ss << "\\b";  break;
            case '\f': ss << "\\f";  break;
            case '\n': ss << "\\n";  break;
            case '\r': ss << "\\r";  break;
            case '\t': ss << "\\t";  break;
            default:   ss << c;      break;
        }
    }
    return ss.str();
}

bool parse_args(int argc, char* argv[], Config& cfg, std::string& error_msg) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if ((arg == "--size" || arg == "-n") && i + 1 < argc) {
            char* end = nullptr;
            unsigned long long val = std::strtoull(argv[++i], &end, 10);
            if (*end != '\0' || val == 0 || val > 50000000ULL) {
                error_msg = "Invalid --size value (must be an integer between 1 and 50,000,000).";
                return false;
            }
            cfg.data_size = static_cast<std::size_t>(val);
        } else if ((arg == "--seed" || arg == "-s") && i + 1 < argc) {
            char* end = nullptr;
            unsigned long val = std::strtoul(argv[++i], &end, 10);
            if (*end != '\0') {
                error_msg = "Invalid --seed value (must be an unsigned integer).";
                return false;
            }
            cfg.seed = static_cast<std::uint32_t>(val);
        } else if ((arg == "--mode" || arg == "-m") && i + 1 < argc) {
            cfg.mode = argv[++i];
        } else if (arg.rfind("-", 0) != 0 && i == 1) {
            // Support positional first argument as data_size
            char* end = nullptr;
            unsigned long long val = std::strtoull(arg.c_str(), &end, 10);
            if (*end != '\0' || val == 0 || val > 50000000ULL) {
                error_msg = "Invalid positional size argument.";
                return false;
            }
            cfg.data_size = static_cast<std::size_t>(val);
        } else if (arg.rfind("-", 0) != 0 && i == 2) {
            // Support positional second argument as seed
            char* end = nullptr;
            unsigned long val = std::strtoul(arg.c_str(), &end, 10);
            if (*end != '\0') {
                error_msg = "Invalid positional seed argument.";
                return false;
            }
            cfg.seed = static_cast<std::uint32_t>(val);
        } else {
            error_msg = "Unrecognized or incomplete argument: " + arg;
            return false;
        }
    }
    return true;
}

}  // namespace

int main(int argc, char* argv[]) {
    Config cfg;
    std::string error_msg;

    if (!parse_args(argc, argv, cfg, error_msg)) {
        std::cout << "{\"status\":\"error\",\"message\":\""
                  << escape_json(error_msg) << "\"}" << std::endl;
        return 1;
    }

    auto start_time = std::chrono::high_resolution_clock::now();

    // Generate synthetic dataset and apply non-linear signal transform
    std::mt19937 rng(cfg.seed);
    std::uniform_real_distribution<double> dist(0.0, 1000.0);

    std::vector<double> data(cfg.data_size);
    for (std::size_t i = 0; i < cfg.data_size; ++i) {
        double raw = dist(rng);
        data[i] = raw * std::sin(raw * 0.01) + std::sqrt(raw);
    }

    // High-performance in-place sort
    std::sort(data.begin(), data.end());

    // Compute statistical summary
    double sum = std::accumulate(data.begin(), data.end(), 0.0);
    double mean = sum / static_cast<double>(cfg.data_size);

    double sq_diff_sum = 0.0;
    for (double val : data) {
        double diff = val - mean;
        sq_diff_sum += diff * diff;
    }
    double std_dev = std::sqrt(sq_diff_sum / static_cast<double>(cfg.data_size));

    double median = (cfg.data_size % 2 == 0)
                        ? (data[cfg.data_size / 2 - 1] + data[cfg.data_size / 2]) * 0.5
                        : data[cfg.data_size / 2];
    double min_val = data.front();
    double max_val = data.back();

    auto end_time = std::chrono::high_resolution_clock::now();
    double elapsed_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

    // Emit structured JSON output to stdout
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{"
        << "\"status\":\"ok\","
        << "\"mode\":\"" << escape_json(cfg.mode) << "\","
        << "\"parameters\":{"
        << "\"size\":" << cfg.data_size << ","
        << "\"seed\":" << cfg.seed
        << "},"
        << "\"metrics\":{"
        << "\"mean\":" << mean << ","
        << "\"median\":" << median << ","
        << "\"std_dev\":" << std_dev << ","
        << "\"min\":" << min_val << ","
        << "\"max\":" << max_val << ","
        << "\"execution_time_ms\":" << elapsed_ms
        << "},"
        << "\"sample_top_5\":[";

    std::size_t preview_count = std::min<std::size_t>(5, cfg.data_size);
    for (std::size_t i = 0; i < preview_count; ++i) {
        if (i > 0) out << ",";
        out << data[cfg.data_size - 1 - i];
    }
    out << "]}";

    std::cout << out.str() << std::endl;
    return 0;
}