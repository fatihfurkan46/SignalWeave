// signal_aggregate.cpp — SignalWeave native aggregation core (C++17)
//
// A dependency-free companion to the Python signalweave package. It reads
// canonical signals as JSONL on stdin (the exact output of
// `signalweave normalize`) and emits a compact per-run reliability aggregate
// as JSON on stdout. The scoring mirrors signalweave.aggregate so native and
// Python paths agree.
//
// Build:   c++ -std=c++17 -O2 -o signal_aggregate signal_aggregate.cpp
// Usage:   signalweave normalize events.jsonl | ./signal_aggregate

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace sw {

// ---- Minimal JSON scalar extraction -------------------------------------
// The input is machine-generated single-line JSON objects with flat scalar
// fields, so a focused field extractor is sufficient and keeps the core
// dependency-free.

static bool find_key(const std::string& obj, const std::string& key,
                     std::size_t& value_start) {
    const std::string needle = "\"" + key + "\":";
    std::size_t pos = 0;
    while ((pos = obj.find(needle, pos)) != std::string::npos) {
        // Ensure the match is a key (preceded by { or , after trimming).
        std::size_t back = pos;
        while (back > 0 && (obj[back - 1] == ' ')) --back;
        if (back == 0 || obj[back - 1] == '{' || obj[back - 1] == ',') {
            value_start = pos + needle.size();
            while (value_start < obj.size() && obj[value_start] == ' ') ++value_start;
            return true;
        }
        pos += needle.size();
    }
    return false;
}

static std::string get_string(const std::string& obj, const std::string& key,
                              const std::string& fallback = "") {
    std::size_t vs;
    if (!find_key(obj, key, vs) || vs >= obj.size() || obj[vs] != '"') return fallback;
    std::string out;
    for (std::size_t i = vs + 1; i < obj.size(); ++i) {
        char c = obj[i];
        if (c == '\\' && i + 1 < obj.size()) { out.push_back(obj[++i]); continue; }
        if (c == '"') break;
        out.push_back(c);
    }
    return out;
}

static double get_number(const std::string& obj, const std::string& key,
                         double fallback = 0.0) {
    std::size_t vs;
    if (!find_key(obj, key, vs)) return fallback;
    if (vs < obj.size() && obj[vs] == '"') return fallback;  // string, not number
    std::size_t end = vs;
    while (end < obj.size() &&
           (std::isdigit(static_cast<unsigned char>(obj[end])) ||
            obj[end] == '-' || obj[end] == '+' || obj[end] == '.' ||
            obj[end] == 'e' || obj[end] == 'E')) {
        ++end;
    }
    if (end == vs) return fallback;  // e.g. null
    try {
        return std::stod(obj.substr(vs, end - vs));
    } catch (...) {
        return fallback;
    }
}

static bool has_null(const std::string& obj, const std::string& key) {
    std::size_t vs;
    if (!find_key(obj, key, vs)) return true;
    return obj.compare(vs, 4, "null") == 0;
}

// ---- Severity ladder (must match model.Severity.weight) -----------------

static int severity_weight(const std::string& sev) {
    if (sev == "ok") return 0;
    if (sev == "notice") return 1;
    if (sev == "warn") return 3;
    if (sev == "error") return 7;
    if (sev == "critical") return 12;
    return 0;
}

struct Signal {
    std::string run_id;
    std::string kind;
    std::string severity;
    double duration_ms = 0.0;
    double quality = 0.0;
    bool has_quality = false;
    long tokens_in = 0;
    long tokens_out = 0;
};

struct RunAcc {
    long count = 0;
    long error_count = 0;
    long severity_load = 0;
    long tokens_in = 0;
    long tokens_out = 0;
    double quality_sum = 0.0;
    long quality_n = 0;
    std::vector<double> durations;
    std::map<std::string, long> kind_counts;
};

static double reliability(const RunAcc& r) {
    if (r.count == 0) return 100.0;
    double severity_penalty =
        std::min(60.0, (static_cast<double>(r.severity_load) / r.count) * 8.0);

    double stability_penalty = 0.0;
    std::vector<double> nz;
    for (double d : r.durations) if (d > 0) nz.push_back(d);
    if (nz.size() >= 2) {
        double mean = 0.0;
        for (double d : nz) mean += d;
        mean /= nz.size();
        if (mean > 0) {
            double var = 0.0;
            for (double d : nz) var += (d - mean) * (d - mean);
            var /= nz.size();
            double cv = std::sqrt(var) / mean;
            stability_penalty = std::min(20.0, cv * 10.0);
        }
    }
    double score = 100.0 - severity_penalty - stability_penalty;
    if (score < 0.0) score = 0.0;
    if (score > 100.0) score = 100.0;
    return std::round(score * 100.0) / 100.0;
}

static double percentile(std::vector<double> v, double pct) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    if (v.size() == 1) return v[0];
    double rank = pct / 100.0 * (v.size() - 1);
    std::size_t low = static_cast<std::size_t>(rank);
    std::size_t high = std::min(low + 1, v.size() - 1);
    double frac = rank - low;
    return std::round(v[low] + (v[high] - v[low]) * frac);
}

}  // namespace sw

int main() {
    using namespace sw;
    std::map<std::string, RunAcc> runs;
    std::vector<std::string> order;  // preserve first-seen for stable output
    std::string line;

    while (std::getline(std::cin, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        Signal s;
        s.run_id = get_string(line, "run_id", "run-unknown");
        s.kind = get_string(line, "kind", "invocation");
        s.severity = get_string(line, "severity", "ok");
        s.duration_ms = get_number(line, "duration_ms", 0.0);
        s.tokens_in = static_cast<long>(get_number(line, "tokens_in", 0.0));
        s.tokens_out = static_cast<long>(get_number(line, "tokens_out", 0.0));
        s.has_quality = !has_null(line, "quality");
        if (s.has_quality) s.quality = get_number(line, "quality", 0.0);

        auto it = runs.find(s.run_id);
        if (it == runs.end()) {
            order.push_back(s.run_id);
            it = runs.emplace(s.run_id, RunAcc{}).first;
        }
        RunAcc& acc = it->second;
        acc.count++;
        acc.kind_counts[s.kind]++;
        acc.severity_load += severity_weight(s.severity);
        acc.tokens_in += s.tokens_in;
        acc.tokens_out += s.tokens_out;
        acc.durations.push_back(s.duration_ms);
        if (s.kind == "error" || s.severity == "error" || s.severity == "critical")
            acc.error_count++;
        if (s.has_quality) { acc.quality_sum += s.quality; acc.quality_n++; }
    }

    // Emit deterministic JSON sorted by run_id.
    std::sort(order.begin(), order.end());

    double fabric_rel_sum = 0.0;
    long total_in = 0, total_out = 0, total_sig = 0;
    double fabric_q_sum = 0.0; long fabric_q_n = 0;

    std::ostringstream body;
    body << "  \"runs\": [\n";
    for (std::size_t i = 0; i < order.size(); ++i) {
        const RunAcc& r = runs[order[i]];
        double rel = reliability(r);
        fabric_rel_sum += rel;
        total_in += r.tokens_in;
        total_out += r.tokens_out;
        total_sig += r.count;
        fabric_q_sum += r.quality_sum;
        fabric_q_n += r.quality_n;

        body << "    {\n";
        body << "      \"run_id\": \"" << order[i] << "\",\n";
        body << "      \"signal_count\": " << r.count << ",\n";
        body << "      \"error_count\": " << r.error_count << ",\n";
        body << "      \"severity_load\": " << r.severity_load << ",\n";
        body << "      \"tokens_in\": " << r.tokens_in << ",\n";
        body << "      \"tokens_out\": " << r.tokens_out << ",\n";
        body << "      \"reliability\": " << rel << ",\n";
        body << "      \"p50_duration_ms\": " << percentile(r.durations, 50) << ",\n";
        body << "      \"p95_duration_ms\": " << percentile(r.durations, 95) << ",\n";
        if (r.quality_n > 0) {
            double qm = std::round((r.quality_sum / r.quality_n) * 10000.0) / 10000.0;
            body << "      \"quality_mean\": " << qm << "\n";
        } else {
            body << "      \"quality_mean\": null\n";
        }
        body << "    }" << (i + 1 < order.size() ? "," : "") << "\n";
    }
    body << "  ]";

    double fabric_rel = order.empty()
        ? 100.0
        : std::round((fabric_rel_sum / order.size()) * 100.0) / 100.0;

    std::cout << "{\n";
    std::cout << "  \"run_count\": " << order.size() << ",\n";
    std::cout << "  \"signal_count\": " << total_sig << ",\n";
    std::cout << "  \"total_tokens_in\": " << total_in << ",\n";
    std::cout << "  \"total_tokens_out\": " << total_out << ",\n";
    std::cout << "  \"fabric_reliability\": " << fabric_rel << ",\n";
    if (fabric_q_n > 0) {
        double fq = std::round((fabric_q_sum / fabric_q_n) * 10000.0) / 10000.0;
        std::cout << "  \"fabric_quality_mean\": " << fq << ",\n";
    } else {
        std::cout << "  \"fabric_quality_mean\": null,\n";
    }
    std::cout << body.str() << "\n";
    std::cout << "}\n";
    return 0;
}
