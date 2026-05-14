# ICE-P1: Input-Length Resource Condition

ICE-P1 is the first concrete UPL-ICE profile for claims where input length or shape induces a resource condition.

Canonical shape:

> Increasing input length or shape beyond a declared threshold induces execution condition `C` within boundary `B`.

## Required witnesses

- `W_input`
- `W_exec`
- `W_map`
- `W_contract`
- `W_check`
- `W_ruleout`

## Intended claim type

ICE-P1 is about `π_work(I)`, not `π_sem(I)`.

It adjudicates whether a declared input behavior induces a declared execution condition, such as:

- memory pressure
- latency regime shift
- resource footprint transition

## Anti-overclaim rules

ICE-P1 does not by itself justify claims that:

- a model is unsafe
- a chip is unsafe
- an AI output is unsafe
- a result generalizes outside the declared boundary

## Demo_ICE_01 use

`demo_ICE_01_context_length_memory_pressure` is the first ICE-P1 instance in this repository.
