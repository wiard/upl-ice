# UPL-WARP: Warranted Agent Routing and Payment

UPL-WARP makes agent routing and agent payments warrantable.

Dutch core sentence:

> UPL-WARP maakt agentkeuze en agentbetalingen bewijsbaar verantwoord.

UPL-WARP is a bounded-warrant framework for deciding whether an agent handoff, cost, hold, or mock payment release is allowed under an explicit boundary.

UPL-WARP does not:
- process real payments
- replace payment networks
- authorize real-world financial activity
- connect to Stripe, PayPal, banks, crypto wallets, or external APIs

UPL-WARP provides:
- an audit layer above agent routing
- a deterministic policy engine for mock payment action
- a warrant layer below payment execution

## Architecture

```text
agent proposes
UPL-WARP adjudicates
deterministic policy engine authorizes
mock ledger records
audit trail persists
```

## Safety scope

- local execution only
- no network access
- no real money
- no external APIs
- no credentials
- no blockchain transactions
- no financial advice

## Demo

The first demo is:

- `demo_WARP_01_agent_handoff_payment_gate`

Claim:

> Agent A may delegate bounded task S to Agent B and release mock payment P only if mandate, budget, policy, quote, result, and trace conditions are checked under boundary B.

## Quickstart

```bash
cd ~/upl-ice/modules/warp/demos/demo_WARP_01_agent_handoff_payment_gate
python3 run.py
```
