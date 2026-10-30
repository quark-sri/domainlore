---
type: Screen
title: New order
description: Form to create an Order and add Order Lines.
basis: actual
sources:
  - id: crawl
    resource: https://staging.example.com/orders/new
    title: Crawl of /orders/new (2026-10-20)
verified: { by: process:demo-crawl, at: 2026-10-20T12:00:00Z }
relations:
  shows: [ordering/entities/order, ordering/entities/order-line]
  navigates_to: [ordering/screens/order-details]
---

# New order

Route `/orders/new`. Fields: supplier, product, quantity. Buttons: Save draft, Submit.[^crawl]

[^crawl]: Crawl of /orders/new (2026-10-20)

<!-- generated:start relations -->
## Relations

- shows → [Order](/ordering/entities/order.md) _(actual)_
- shows → [Order Line](/ordering/entities/order-line.md) _(actual)_
- navigates to → [Order details](/ordering/screens/order-details.md) _(actual)_
- step of → [Place an order](/ordering/journeys/place-order.md)
- [Order list](/ordering/screens/order-list.md) navigates to this _(actual)_
<!-- generated:end relations -->
