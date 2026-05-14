# demo_WARP_01 Design

## Strategic purpose

`demo_WARP_01_agent_handoff_payment_gate` is the first bounded UPL-WARP demonstration.
Its purpose is to show that a local agent handoff and a mock payment release can be gated by an explicit witness chain and an adjudicated warrant status.

## Relationship to UPL-Core and UPL-ICE

UPL-Core supplies the general bounded-warrant discipline:

`Gamma ⊢ K @ B ⇐ W : sigma`

UPL-ICE focuses on input-conditioned execution behavior.
UPL-WARP focuses on whether an agent handoff, cost claim, hold, or mock payment release may proceed under an explicit boundary.

## Why WARP is not a payment rail

UPL-WARP is not:

- a payment processor
- a wallet
- a bank integration
- a crypto system
- a financial product

The module never sends real payments.
It only records deterministic local mock ledger entries.

## Core claim

The first claim is:

> Agent A may delegate bounded task S to Agent B and release mock payment P only if mandate, budget, policy, quote, result, and trace conditions are checked under boundary B.

## Safe scope

- local execution only
- no network
- no credentials
- no external APIs
- no real money
- no external targets
- deterministic mock policy engine

## Boundary

The boundary fixes:

- mock payment only
- `EUR-MOCK` currency
- a maximum total budget
- a maximum single payment
- allowed agents
- allowed task types
- forbidden task types
- mandatory mandate, quote, result check, and trace completeness

## Policy context

The policy layer expresses seven deterministic rules:

- mandate required
- budget limit
- allowed agent
- allowed task
- result required
- trace required
- mock only

## Six witnesses

### W_mandate

Evidence of bounded user authorization for the task.

### W_route

Evidence that Agent A may delegate to Agent B for the selected task type.

### W_quote

Evidence that the quoted mock cost fits the declared budget boundary.

### W_contract

Definition of successful bounded completion and payment-release conditions.

### W_check

Deterministic per-rule pass/fail evaluation.

### W_ruleout

Evidence excluding invalid payment interpretations such as real payment, network dependency, or credential use.

## Status logic

`checked`
- all witnesses present
- budget, route, mandate, result, and ruleouts pass

`bounded`
- claim is well-formed but result not yet produced

`pending_check`
- route and quote valid but result check not yet executed

`failed`
- route or result check fails within boundary

`contradicted`
- direct conflict such as non-mock payment or over-budget quote

`inconclusive`
- data present but inconsistent without direct contradiction

`unsupported`
- no meaningful witnesses

`incomplete`
- required witness files or fields missing

`out_of_scope`
- real payment attempted
- network or credentials required
- external APIs needed
- claim broadened beyond the local mock boundary

## Mock ledger design

The ledger is a local JSON artifact.
It records:

- from account
- to account
- amount
- currency
- payment action
- linked judgment

It never triggers external transfer.

## Forbidden claims

The demo does not justify claims that:

- real payment was made
- Agent B is generally trustworthy
- the user authorized future payments
- the result is financially or legally valid
- the claim generalizes beyond boundary `B`

## First demo design

The demo loads:

- boundary
- policy
- agent registry
- user mandate

Then:

1. Agent A proposes a bounded handoff
2. Agent B returns a fixed bounded local result
3. The policy engine checks all rules
4. UPL-WARP assigns a warrant status
5. The payment-action mapping determines release, hold, or deny
6. The mock ledger records the outcome

## Future work

Future WARP demos may cover:

- multi-agent quote comparison
- bounded escrow hold/release logic
- repeated task budget exhaustion
- stronger trace completeness profiles

But the first goal remains small, safe, local, and reproducible.
