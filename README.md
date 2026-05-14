# UPL-ICE: Input-Conditioned Execution Warranting

UPL-ICE assigns warrant status to claims about how AI input behavior induces execution conditions.

UPL-ICE is not:
- an offensive cyber toolkit
- a chip-safety certification system
- an AI-output safety benchmark

UPL-ICE is:
- a bounded-warrant framework
- for local reproducible claims
- about input-conditioned execution behavior

The central distinction is between:
- `π_sem(I)`: the semantic projection of input `I`
- `π_work(I)`: the workload projection of input `I`

UPL-ICE adjudicates claims about `π_work(I)`, not `π_sem(I)`.

## First demo

This repository boots with:

- `demo_ICE_01_context_length_memory_pressure`

Claim:

> Increasing input context length beyond threshold `L` induces memory-pressure regime `C` under boundary `B`.

## Safety scope

- Local execution only
- No external targets
- No network dependency in the demo
- No scanning
- No exploitation
- No malware
- Synthetic benign inputs only

## Quickstart

```bash
cd ~/upl-ice/demos/demo_ICE_01_context_length_memory_pressure
python3 run.py
```

## Status discipline

For `demo_ICE_01`, the active adjudication subset is:

- `checked`
- `failed`
- `inconclusive`
- `incomplete`
- `out_of_scope`

## Foundational reference

Foundational work:

- `github.com/wiard/upl-foundation`
- paper v0.4
- exploratory witnessed instance `demo_06`

## Repository layout

```text
upl-ice/
├── README.md
├── LICENSE
├── .gitignore
├── docs/
├── schemas/
├── profiles/
└── demos/
```

## Working style

This repository follows a small, clean, safe, understandable style.
The first goal is a bounded, witnessed, reproducible judgment, not a perfect benchmark.
