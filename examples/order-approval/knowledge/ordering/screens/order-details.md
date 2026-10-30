---
type: Screen
title: Order details
description: Shows one Order with its lines, status and actions.
basis: actual
sources:
  - id: crawl
    resource: https://staging.example.com/orders/:id
    title: Crawl of /orders/:id (2026-10-20)
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2
    basis: intended
verified: { by: process:demo-crawl, at: 2026-10-20T12:00:00Z }
relations:
  shows: [ordering/entities/order, ordering/entities/order-line]
  navigates_to:
    - ordering/screens/order-list
    - { to: approvals/screens/approval-inbox, basis: intended, cites: [policy] }
---

# Order details

Route `/orders/:id`. Actions: Submit, Cancel.[^crawl] The policy expects a link to the approver's inbox; the crawl did not find one.[^policy]

[^crawl]: Crawl of /orders/:id (2026-10-20)
[^policy]: Purchase approval policy v2

<!-- generated:start relations -->
## Relations

- shows → [Order](/ordering/entities/order.md) _(actual)_
- shows → [Order Line](/ordering/entities/order-line.md) _(actual)_
- navigates to → [Order list](/ordering/screens/order-list.md) _(actual)_
- navigates to → [Approval inbox](/approvals/screens/approval-inbox.md) _(intended)_
- step of → [Approve an order](/approvals/journeys/approve-order.md)
- step of → [Place an order](/ordering/journeys/place-order.md)
- [Approval inbox](/approvals/screens/approval-inbox.md) navigates to this _(actual)_
- [New order](/ordering/screens/new-order.md) navigates to this _(actual)_
- [Order list](/ordering/screens/order-list.md) navigates to this _(actual)_
- ⚠ Gap (open): [Cancel without confirmation](/conflicts/cancel-without-confirmation.md)
<!-- generated:end relations -->
