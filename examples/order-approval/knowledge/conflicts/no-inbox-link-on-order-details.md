---
type: Gap
title: No inbox link on Order details
description: The policy expects a link from Order details to the approver's inbox; the app has none.
about: [ordering/screens/order-details, approvals/screens/approval-inbox, approvals/journeys/approve-order]
sources:
  - id: policy
    resource: ../docs/approval-policy.md
    title: Purchase approval policy v2, rule 5
    basis: intended
  - id: crawl
    resource: https://staging.example.com/orders/:id
    title: Crawl of /orders/:id (2026-10-20)
    basis: actual
---

# No inbox link on Order details

- **Intended:** "The order details page links back to the approver's inbox."[^policy]
- **Actual:** the crawl of Order details found the actions Submit and Cancel, and no link to `/approvals`.[^crawl]

Likely a missing feature. In the Approve an order journey the Approver must go back to the inbox without a link.

[^policy]: Purchase approval policy v2, rule 5
[^crawl]: Crawl of /orders/:id (2026-10-20)
