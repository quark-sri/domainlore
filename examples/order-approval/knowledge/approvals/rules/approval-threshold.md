---
type: Rule
title: Approval threshold
description: Orders above a total amount need approval before processing.
basis: intended
sources:
  - id: wiki-approvals
    resource: https://wiki.example.com/display/APR/Approval+rules
    title: Approval rules (Confluence)
    version: "12"
    last_modified: 2026-06-01T00:00:00Z
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2
    version: "2"
    last_modified: 2025-03-14T00:00:00Z
relations:
  governs: [ordering/entities/order, approvals/entities/approval-request]
---

# Approval threshold

Confluence sets the threshold at **10 000 EUR**.[^wiki-approvals] The BRD sets it at **5 000 EUR**.[^policy]
See the open [Spec Conflict](/conflicts/approval-threshold-amount.md).

[^wiki-approvals]: Approval rules (Confluence)
[^policy]: Purchase approval policy v2

<!-- generated:start relations -->
## Relations

- governs → [Order](/ordering/entities/order.md) _(intended)_
- governs → [Approval Request](/approvals/entities/approval-request.md) _(intended)_
- ⚠ Spec Conflict (open): [Approval threshold amount](/conflicts/approval-threshold-amount.md)
<!-- generated:end relations -->
