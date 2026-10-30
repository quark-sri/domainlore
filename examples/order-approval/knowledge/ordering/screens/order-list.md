---
type: Screen
title: Order list
description: Lists the Customer's Orders with status and total.
basis: actual
sources:
  - id: crawl
    resource: https://staging.example.com/orders
    title: Crawl of /orders (2026-10-20)
verified: { by: process:demo-crawl, at: 2026-10-20T12:00:00Z }
relations:
  shows: [ordering/entities/order]
  navigates_to:
    - ordering/screens/order-details
    - ordering/screens/new-order
---

# Order list

Route `/orders`. Columns: number, status, total, created.[^crawl]

[^crawl]: Crawl of /orders (2026-10-20)

<!-- generated:start relations -->
## Relations

- shows → [Order](/ordering/entities/order.md) _(actual)_
- navigates to → [Order details](/ordering/screens/order-details.md) _(actual)_
- navigates to → [New order](/ordering/screens/new-order.md) _(actual)_
- step of → [Place an order](/ordering/journeys/place-order.md)
- [Order details](/ordering/screens/order-details.md) navigates to this _(actual)_
<!-- generated:end relations -->
