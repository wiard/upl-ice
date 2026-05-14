# WARP-P0: Trace Completeness

WARP-P0 verifies trace completeness for agent handoff and mock payment claims.

It checks that the bounded run produced:

- boundary material
- policy material
- witness files
- judgment file
- mock ledger file
- trace log

WARP-P0 does not require that mock payment release occurred.
It only checks that the bounded trace is present and legible.
