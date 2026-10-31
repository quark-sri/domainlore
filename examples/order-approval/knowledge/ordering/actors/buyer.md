---
type: Actor
title: Buyer
description: A person who places Orders for a Customer; the Buyer creates and submits them.
aliases: [Requester]
basis: intended
sources:
  - id: wiki-model
    resource: https://wiki.example.com/display/ORD/Domain+model
    title: Ordering domain model (Confluence)
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  performs: [ordering/journeys/place-order]
---

# Buyer

A Buyer works for a [Customer](/ordering/entities/customer.md) and places [Orders](/ordering/entities/order.md).[^wiki-model]

[^wiki-model]: Ordering domain model (Confluence)

<!-- generated:start relations -->
## Relations

- performs → [Place an order](/ordering/journeys/place-order.md) _(intended)_
<!-- generated:end relations -->
