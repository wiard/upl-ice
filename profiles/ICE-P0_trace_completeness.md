# ICE-P0: Trace Completeness

ICE-P0 is the minimum trace-completeness profile for UPL-ICE.

It checks whether a run has the minimum required:

- boundary material
- witness material
- judgment material

ICE-P0 does not require a successful resource-condition claim.
It only checks whether the trace, witnesses, and adjudication artifacts exist in a bounded and legible form.

## Minimum artifacts

- boundary configuration
- contract configuration
- witness files
- summary result
- trace log
- judgment file

## Typical use

ICE-P0 is useful when:

- a new demo is being bootstrapped
- the witness chain exists but the claim has not yet reached `checked`
- reproducibility and completeness matter before claim strength
