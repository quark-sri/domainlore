---
type: Screen
title: Approval inbox
description: Lists pending Approval Requests for the signed-in Approver.
basis: actual
sources:
  - id: crawl
    resource: https://staging.example.com/approvals
    title: Crawl of /approvals (2026-10-20)
verified: { by: process:demo-crawl, at: 2026-10-20T12:00:00Z }
relations:
  shows: [approvals/entities/approval-request, ordering/entities/order]
  navigates_to: [ordering/screens/order-details]
---

# Approval inbox

Route `/approvals`. Each row has Approve and Reject buttons.[^crawl]

[^crawl]: Crawl of /approvals (2026-10-20)

<!-- generated:start relations -->
## Relations

- shows → [Approval Request](/approvals/entities/approval-request.md) _(actual)_
- shows → [Order](/ordering/entities/order.md) _(actual)_
- navigates to → [Order details](/ordering/screens/order-details.md) _(actual)_
- step of → [Approve an order](/approvals/journeys/approve-order.md)
- [Order details](/ordering/screens/order-details.md) navigates to this _(intended)_
<!-- generated:end relations -->
