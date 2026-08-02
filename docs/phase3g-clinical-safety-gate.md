# Phase 3G Clinical Safety Transition Gate

## Goal

Prevent a treatment plan from moving into `approved` or `active` state when the
materialised clinical aggregate is incomplete, unmonitorable, or lacks safety
provenance.

## Transition policy

The gate runs after lifecycle legality validation and before any status,
approver, or timestamp mutation.

### Approval blockers

- no treatment items
- missing clinical rationale
- medication without dose text, route, or frequency
- medication without monitoring
- monitoring without schedule
- monitoring without an abnormal-result action
- high or critical safety rule without condition, action, or provenance source

A missing summary is recorded as a warning and does not block approval.

### Activation blockers

Activation includes every approval check and additionally requires:

- approver identity
- approval timestamp

Safety rules marked `requires_review` remain visible as activation warnings so
the clinical UI can require an explicit acknowledgement in a later workflow
extension.

## Contract

`TreatmentPlanSafetyGate.evaluate()` is deterministic and framework independent.
It returns a frozen `SafetyGateReport` with machine-readable blockers and
warnings. `assert_can_transition()` raises `ClinicalSafetyGateError`, which is a
`ValueError` so existing API exception mapping remains compatible.

`TreatmentPlanService.get_safety_gate()` exposes readiness without changing
state. `approve_plan()` and `activate_plan()` execute the same gate before
mutation and before transaction persistence.

## Non-goals

This module does not make a clinical decision, select a drug, or replace human
review. It only validates completeness and traceability of an already generated
plan.
