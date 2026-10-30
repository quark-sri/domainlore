---
type: Gap
title: Cancel without confirmation
description: The policy asks the buyer to confirm a cancel; the app cancels at once.
about: [ordering/screens/order-details, ordering/entities/order]
sources:
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2, rule 4
    basis: intended
  - id: crawl
    resource: https://staging.example.com/orders/:id
    title: Crawl of /orders/:id (2026-10-20)
    basis: actual
---

# Cancel without confirmation

- **Intended:** "Cancelling a submitted order asks the buyer to confirm."[^policy]
- **Actual:** clicking **Cancel** on a submitted order sets it to `cancelled` with no dialog.[^crawl]

Likely a defect. Write a test for the confirmation dialog before fixing it.

[^policy]: Purchase approval policy v2, rule 4
[^crawl]: Crawl of /orders/:id (2026-10-20)
