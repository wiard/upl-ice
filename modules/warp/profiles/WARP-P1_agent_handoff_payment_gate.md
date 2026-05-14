# WARP-P1: Agent Handoff Payment Gate

WARP-P1 is the first concrete UPL-WARP profile.

It adjudicates whether:

- Agent A may hand off a bounded task to Agent B
- and whether a mock payment release is allowed under a bounded policy

Required witnesses:

- `W_mandate`
- `W_route`
- `W_quote`
- `W_contract`
- `W_check`
- `W_ruleout`

WARP-P1 is about bounded local agent routing and mock payment gating.
It is not a real payment authorization system.
