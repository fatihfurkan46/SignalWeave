# SignalWeave — build and run targets

PYTHON ?= python
CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall
ENGINE_SRC := engine/signal_aggregate.cpp
ENGINE_BIN := engine/signal_aggregate
FIXTURE := examples/events.jsonl

.PHONY: all engine check report normalize aggregate parity clean

all: engine

engine: $(ENGINE_BIN)

$(ENGINE_BIN): $(ENGINE_SRC)
	$(CXX) $(CXXFLAGS) -o $(ENGINE_BIN) $(ENGINE_SRC)

check:
	$(PYTHON) -m compileall signalweave

report:
	$(PYTHON) -m signalweave report $(FIXTURE)

normalize:
	$(PYTHON) -m signalweave normalize $(FIXTURE)

aggregate:
	$(PYTHON) -m signalweave aggregate $(FIXTURE)

# Confirm the Python and native cores produce matching aggregates.
parity: engine
	$(PYTHON) -m signalweave normalize $(FIXTURE) | ./$(ENGINE_BIN)

clean:
	rm -f $(ENGINE_BIN) $(ENGINE_BIN).exe
	rm -rf signalweave/__pycache__
