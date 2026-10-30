---
type: Entity
title: Order
description: A buyer's request to purchase one or more products from a supplier.
aliases: [Purchase Order]
basis: intended
sources:
  - id: ord-12
    resource: https://jira.example.com/browse/ORD-12
    title: "ORD-12: Order lifecycle"
    last_modified: 2026-09-02T10:00:00Z
  - id: api
    resource: ../openapi.yaml#/components/schemas/Order
    title: Order schema (OpenAPI)
    basis: actual
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2
    version: "2"
verified:
  - { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  has: [ordering/entities/order-line]
  belongs_to:
    - { to: ordering/entities/customer, basis: [intended, actual], cites: [ord-12, api] }
states: [draft, submitted, approved, rejected, cancelled, shipped]
transitions:
  - { from: draft, to: submitted, trigger: ordering/actors/buyer, governed_by: [ordering/rules/minimum-order-value], cites: [ord-12] }
  - { from: submitted, to: approved, trigger: approvals/actors/approver, governed_by: [approvals/rules/approval-threshold, approvals/rules/four-eyes], cites: [ord-12, policy] }
  - { from: submitted, to: rejected, trigger: approvals/actors/approver, cites: [ord-12] }
  - { from: submitted, to: cancelled, trigger: ordering/actors/buyer, cites: [policy] }
  - { from: approved, to: shipped, trigger: system, basis: actual, cites: [api] }
---

# Order

An Order is created as a **draft** by a [Buyer](/ordering/actors/buyer.md) and becomes **submitted** when the buyer sends it.[^ord-12]
Orders above the [approval threshold](/approvals/rules/approval-threshold.md) wait for an [Approver](/approvals/actors/approver.md).[^policy]

The API also moves approved orders to **shipped**; no ticket specifies this step.[^api]

[^ord-12]: ORD-12: Order lifecycle
[^policy]: Purchase approval policy v2
[^api]: Order schema (OpenAPI)

<!-- generated:start lifecycle -->
## Lifecycle

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> submitted : Buyer [Minimum order value] (intended)
  submitted --> approved : Approver [Approval threshold, Four-eyes principle] (intended)
  submitted --> rejected : Approver (intended)
  submitted --> cancelled : Buyer (intended)
  approved --> shipped : system (actual)
```

_Labels: (intended) = specified only · (actual) = seen in app or code only._
<!-- generated:end lifecycle -->

<!-- generated:start relations -->
## Relations

- has → [Order Line](/ordering/entities/order-line.md) _(intended)_
- belongs to → [Customer](/ordering/entities/customer.md)
- [Approval Request](/approvals/entities/approval-request.md) belongs to this _(intended)_
- [Approval threshold](/approvals/rules/approval-threshold.md) governs this _(intended)_
- [Approval inbox](/approvals/screens/approval-inbox.md) shows this _(actual)_
- [Customer](/ordering/entities/customer.md) has this _(intended)_
- [Order Line](/ordering/entities/order-line.md) belongs to this _(intended)_
- [Minimum order value](/ordering/rules/minimum-order-value.md) governs this _(intended)_
- [New order](/ordering/screens/new-order.md) shows this _(actual)_
- [Order details](/ordering/screens/order-details.md) shows this _(actual)_
- [Order list](/ordering/screens/order-list.md) shows this _(actual)_
- [PO](/ordering/terms/po.md) also known as this
- [Four-eyes principle](/approvals/rules/four-eyes.md) governs this
- ⚠ Gap (open): [Cancel without confirmation](/conflicts/cancel-without-confirmation.md)
<!-- generated:end relations -->
