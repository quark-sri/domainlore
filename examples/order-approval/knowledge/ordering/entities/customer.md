---
type: Entity
title: Customer
description: The company that places Orders through its Buyers.
basis: intended
sources:
  - id: wiki-model
    resource: https://wiki.example.com/display/ORD/Domain+model
    title: Ordering domain model (Confluence)
    version: "7"
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  has: [ordering/entities/order]
---

# Customer

A Customer is a company account. People who place orders for it are [Buyers](/ordering/actors/buyer.md).[^wiki-model]

[^wiki-model]: Ordering domain model (Confluence)

<!-- generated:start relations -->
## Relations

- has → [Order](/ordering/entities/order.md) _(intended)_
- [Order](/ordering/entities/order.md) belongs to this
<!-- generated:end relations -->
