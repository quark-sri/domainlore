---
type: Rule
title: Minimum order value
description: An Order can only be submitted when its total is at least 50 EUR.
basis: intended
sources:
  - id: ord-31
    resource: https://jira.example.com/browse/ORD-31
    title: "ORD-31: Block tiny orders"
relations:
  governs: [ordering/entities/order]
---

# Minimum order value

Submitting an [Order](/ordering/entities/order.md) with a total below **50 EUR** is blocked with the message "Order total too low".[^ord-31]

[^ord-31]: ORD-31: Block tiny orders

<!-- generated:start relations -->
## Relations

- governs → [Order](/ordering/entities/order.md) _(intended)_
<!-- generated:end relations -->
