# SignalWeave — build and run targets

PYTHON ?= python
CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall
ENGINE_SRC := engine/signal_aggregate.cpp
ENGINE_BIN := engine/signal_aggregate
FIXTURE := examples/events.jsonl

.PHONY: all engine check report normalize aggregate parity clean

all: engine
