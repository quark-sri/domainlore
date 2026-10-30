---
type: Entity
title: Approval Request
description: A request for an Approver to accept or reject one Order.
basis: intended
sources:
  - id: apr-3
    resource: https://jira.example.com/browse/APR-3
    title: "APR-3: Approval requests"
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  belongs_to: [ordering/entities/order]
states: [pending, approved, rejected, escalated]
transitions:
  - { from: pending, to: approved, trigger: approvals/actors/approver, governed_by: [approvals/rules/four-eyes], cites: [apr-3] }
  - { from: pending, to: rejected, trigger: approvals/actors/approver, cites: [apr-3] }
  - { from: pending, to: escalated, trigger: system, cites: [policy] }
---

# Approval Request

Created when an [Order](/ordering/entities/order.md) above the threshold is submitted.[^apr-3]
Undecided requests are escalated after 3 working days.[^policy]

[^apr-3]: APR-3: Approval requests
[^policy]: Purchase approval policy v2

<!-- generated:start lifecycle -->
## Lifecycle

```mermaid
stateDiagram-v2
  [*] --> pending
  pending --> approved : Approver [Four-eyes principle] (intended)
  pending --> rejected : Approver (intended)
  pending --> escalated : system (intended)
```

_Labels: (intended) = specified only · (actual) = seen in app or code only._
<!-- generated:end lifecycle -->

<!-- generated:start relations -->
## Relations

- belongs to → [Order](/ordering/entities/order.md) _(intended)_
- [Approval threshold](/approvals/rules/approval-threshold.md) governs this _(intended)_
- [Four-eyes principle](/approvals/rules/four-eyes.md) governs this _(intended)_
- [Approval inbox](/approvals/screens/approval-inbox.md) shows this _(actual)_
<!-- generated:end relations -->
