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
