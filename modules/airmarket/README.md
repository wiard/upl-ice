# AirMarket

AirMarket is a small local warrant-gated marketplace for avatar work.

PACT Log records avatar transitions in an append-only event log.
UPL adjudicates bounded claims about delivered work.
AtomGate maps one adjudicated status to one marketplace action.

AirMarket is not a real payment system.
AirMarket does not claim legal finality or settlement finality.

This is pay-per-checked-claim.

## Core objects

- `AirMarket`: the marketplace
- `PACT Log`: append-only event log
- `WorkCard`: marketplace offer
- `MandateLink`: principal edge between avatars
- `ProofPack`: witnesses for delivered work
- `UPL Checkout`: bounded claim adjudication
- `AtomGate`: `pi: Sigma -> Actions`
- `ClaimReceipt`: output receipt

## CLI

Run from this module directory:

```bash
python3 -m airmarket seed
python3 -m airmarket list-workcards
python3 -m airmarket place-order workcard_summary_001
python3 -m airmarket deliver order_001
python3 -m airmarket checkout order_001
python3 -m airmarket replay
```

## What checkout does

1. load order, workcard, buyer avatar, seller avatar, and principal edge
2. construct bounded claim `K`
3. construct boundary `B`
4. collect witnesses `W`
5. adjudicate exactly one UPL status `sigma`
6. apply `AtomGate`
7. append a PACT event
8. write a `ClaimReceipt`

## Non-claims

- no real payment is executed
- no external service is called
- no legal or settlement finality is claimed
- no trust claim travels farther than its evidence
