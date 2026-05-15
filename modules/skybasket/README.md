# SkyBasket

SkyBasket is an atomic basket checkout for warrant-gated avatar work.

The basket action is released only when every WorkCard delivery claim is adjudicated as checked.

Principal is not a fifth ontology element; it is a MandateLink from one avatar to another avatar across namespace boundaries.

SkyBasket does not execute real payments and does not claim real-world settlement finality.

Pay-per-checked-basket.

## What SkyBasket is

SkyBasket is a small local marketplace application-demo for buying a bundle of bounded avatar work in one basket.
It treats each WorkCard as a bounded delivery claim and then aggregates those item judgments into one basket judgment.

## Why it is atomic

The basket is atomic at the decision layer:

- every item is checked individually
- the basket judgment aggregates item statuses
- AtomGate maps exactly one basket status to exactly one action

This application-demo does not claim real-world settlement atomicity.

## What PACT logs

PACT logs avatar transitions as append-only JSONL events:

- namespace
- world
- avatar
- transition

## What UPL adjudicates

UPL adjudicates bounded item and basket claims:

`Gamma entails K at B from W with status sigma`

## What AtomGate maps

AtomGate maps one basket status to one bounded action:

`pi: Sigma -> Actions`

## What a MandateLink is

A MandateLink is the principal edge that connects one avatar to another avatar across namespace boundaries.
In this demo, seller and buyer avatars operate under a bounded principal path to `vasen_vof@kvk`.

## Non-claims

- no real payment is executed
- no legal finality is claimed
- no settlement finality is claimed
- no claim travels farther than its witnesses

## CLI

Run from this module directory:

```bash
python3 -m skybasket seed
python3 -m skybasket list-workcards
python3 -m skybasket create-basket
python3 -m skybasket deliver-all basket_001
python3 -m skybasket checkout basket_001
python3 -m skybasket replay
```

## Expected happy-path output

On the happy path:

- `basket_status = checked`
- `basket_action = mock_basket_payment_release_allowed`

The resulting BasketReceipt is written into `receipts/`, and the PACT log is written to `log/pact_events.jsonl`.
