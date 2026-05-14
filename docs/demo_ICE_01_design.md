# demo_ICE_01 Design

## Purpose

`demo_ICE_01_context_length_memory_pressure` is the first bounded UPL-ICE demonstration.
It is designed to show that a local, reproducible claim about input-conditioned execution
behavior can be adjudicated with an explicit witness set.

The demo claim is intentionally small:

> Increasing input context length beyond a declared threshold `L` induces
> memory-pressure regime `C` under boundary `B`.

This demo does not claim unsafe AI output, unsafe hardware, unsafe models, or any result
beyond the declared boundary.

## Strategic decision

The first UPL-ICE instance should be:

- local
- reproducible
- safe
- synthetic
- independent of external services

That leads to a resource-behavior demonstration instead of a semantic-output demonstration.
The aim is not to say what an input means, but how it conditions execution shape and memory use.

## Naming decision

This repository uses the namespace:

- `UPL-Core` for the general bounded-warrant discipline
- `UPL-ICE` for input-conditioned execution warranting
- `ICE-P0`, `ICE-P1` for profile names

The naming explicitly avoids extending the earlier `UPL-P0..P5` namespace.

## Framing: π_sem versus π_work

Every AI input has at least two useful projections:

- `π_sem(I)`: semantic projection
- `π_work(I)`: workload projection

`π_sem(I)` concerns meaning, intent, and task.
`π_work(I)` concerns shape, size, allocation demand, latency regime, and related execution structure.

UPL-ICE adjudicates claims about `π_work(I)`.
This first demo uses synthetic context length as the input behavior and memory pressure as the execution condition.

## Experimental object

The workload is a synthetic attention-like allocation pattern.
For each input length `l`, the runner simulates a score matrix allocation of approximately:

`batch_size × l × l × bytes_per_score`

The workload uses Python standard library only.
It allocates a `bytearray`, touches memory pages so allocation is material, and records:

- latency
- tracemalloc peak memory delta
- optional process RSS observation via `resource.getrusage`

## Boundary

The default boundary is stored in `configs/boundary.json`.

Key boundary commitments:

- one local machine
- Python standard library runtime
- CPU only
- synthetic workload object
- no concurrent workloads
- no network requirement
- predeclared input lengths
- predeclared abort limit

The boundary prevents overclaim:

- the result is not about arbitrary model architectures
- not about external systems
- not about semantic correctness

## Contract

The contract is stored in `configs/contract.json`.

Memory-pressure condition `C` holds only if both conditions are true:

1. the absolute threshold `M_abs_bytes` is crossed
2. the ratio threshold `R_ratio` is crossed relative to the control median

The thresholds are predeclared before measurement.
They are not fitted after the result.

## Variables

Independent variable:

- input context length

Observed variables:

- peak memory delta
- latency
- abort status

Derived variables:

- control median
- ratio against control median
- whether condition `C` holds

## Witness set

This demo writes six witnesses:

### W_input

- input lengths
- batch size
- embedding dim
- bytes per score
- synthetic policy
- repetitions
- run order

### W_exec

- runtime metadata
- latency
- memory measurements
- abort status

### W_map

- mapping from input length to execution condition
- `O(l²)` allocation logic
- memory-pressure condition framing

### W_contract

- formal contract for condition `C`
- thresholds
- validity constraints

### W_check

- control versus test comparison
- whether controls remain below `C`
- whether at least one test enters `C`
- repetition consistency

### W_ruleout

- same runtime
- same workload
- same device class
- same thresholds
- same measurement method
- no network
- no external workloads

## Adjudication rules

`checked`
- all six witnesses present
- boundary complete
- thresholds predeclared
- controls do not satisfy `C`
- at least one test does satisfy `C`
- repetitions are internally consistent

`failed`
- witnesses present
- boundary respected
- but no test satisfies `C`

`inconclusive`
- controls satisfy `C`
- or measurement consistency is too weak

`incomplete`
- missing required witness files or fields

`out_of_scope`
- boundary changed
- thresholds altered after the fact
- all test lengths blocked by abort limit
- or the claim is broadened beyond input-length to memory-pressure

## Success criterion

The success criterion for this first repository is not a particular performance number.
It is a bounded, witnessed, reproducible adjudication.

The strongest local outcome is:

- `checked`

But `failed`, `inconclusive`, or `incomplete` are also methodologically useful if they are honestly witnessed.
