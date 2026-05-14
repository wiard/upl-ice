# demo_ICE_01_context_length_memory_pressure

This demo measures whether increased synthetic context length induces a predeclared memory-pressure condition under a bounded local runtime.

Claim:

> Increasing input context length beyond threshold `L` induces memory-pressure regime `C` under boundary `B`.

Run locally:

```bash
python3 run.py
```

Outputs:

- `witnesses/*.json`
- `results/summary.json`
- `results/environment.json`
- `results/trace.log`
- `results/judgment.json`
