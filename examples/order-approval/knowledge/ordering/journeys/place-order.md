---
type: Journey
title: Place an order
description: A Buyer creates an Order, adds lines and submits it.
basis: intended
sources:
  - id: ord-12
    resource: https://jira.example.com/browse/ORD-12
    title: "ORD-12: Order lifecycle"
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
steps:
  - { id: open, label: Open the order list, screen: ordering/screens/order-list, actor: ordering/actors/buyer }
  - { id: create, label: Create a new order, screen: ordering/screens/new-order, actor: ordering/actors/buyer }
  - id: submit
    label: Submit the order
    screen: ordering/screens/new-order
    actor: ordering/actors/buyer
    goto:
      - { to: blocked, when: total below 50 EUR }
      - { to: review, when: total at least 50 EUR }
  - { id: blocked, label: See 'Order total too low', screen: ordering/screens/new-order, goto: [] }
  - { id: review, label: Review the submitted order, screen: ordering/screens/order-details }
---

# Place an order

The Buyer's main journey.[^ord-12] See [Minimum order value](/ordering/rules/minimum-order-value.md).

[^ord-12]: ORD-12: Order lifecycle

<!-- generated:start flow -->
## Flow

```mermaid
flowchart TD
  n_open["Open the order list<br/><small>Order list</small>"]
  n_create["Create a new order<br/><small>New order</small>"]
  n_submit["Submit the order<br/><small>New order</small>"]
  n_blocked["See 'Order total too low'<br/><small>New order</small>"]
  n_review["Review the submitted order<br/><small>Order details</small>"]
  n_open --> n_create
  n_create --> n_submit
  n_submit -->|"total below 50 EUR"| n_blocked
  n_submit -->|"total at least 50 EUR"| n_review
```
<!-- generated:end flow -->

<!-- generated:start relations -->
## Relations

- [Buyer](/ordering/actors/buyer.md) performs this _(intended)_
- [Order list](/ordering/screens/order-list.md) step of this
- [New order](/ordering/screens/new-order.md) step of this
- [Order details](/ordering/screens/order-details.md) step of this
<!-- generated:end relations -->
