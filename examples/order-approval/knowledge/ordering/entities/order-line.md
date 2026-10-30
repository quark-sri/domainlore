---
type: Entity
title: Order Line
description: One product, quantity and price within an Order.
basis: intended
sources:
  - id: ord-12
    resource: https://jira.example.com/browse/ORD-12
    title: "ORD-12: Order lifecycle"
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  belongs_to: [ordering/entities/order]
---

# Order Line

A line holds a product, a quantity and the unit price at the time the order was placed.[^ord-12]

[^ord-12]: ORD-12: Order lifecycle

<!-- generated:start relations -->
## Relations

- belongs to → [Order](/ordering/entities/order.md) _(intended)_
- [Order](/ordering/entities/order.md) has this _(intended)_
- [New order](/ordering/screens/new-order.md) shows this _(actual)_
- [Order details](/ordering/screens/order-details.md) shows this _(actual)_
<!-- generated:end relations -->
