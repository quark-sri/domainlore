---
type: Rule
title: Four-eyes principle
description: The Approver of an Order must not be the Buyer who placed it.
basis: intended
sources:
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  governs: [approvals/entities/approval-request]
---

# Four-eyes principle

A person cannot approve an [Order](/ordering/entities/order.md) they placed.[^policy]

[^policy]: Purchase approval policy v2

<!-- generated:start relations -->
## Relations

- governs → [Approval Request](/approvals/entities/approval-request.md) _(intended)_
- governs → [Order](/ordering/entities/order.md)
<!-- generated:end relations -->
