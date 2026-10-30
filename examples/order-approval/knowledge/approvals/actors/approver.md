---
type: Actor
title: Approver
description: A person who accepts or rejects Approval Requests.
basis: intended
sources:
  - id: apr-3
    resource: https://jira.example.com/browse/APR-3
    title: "APR-3: Approval requests"
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
relations:
  performs: [approvals/journeys/approve-order]
---

# Approver

Usually a team lead or the finance lead.[^apr-3]

[^apr-3]: APR-3: Approval requests

<!-- generated:start relations -->
## Relations

- performs → [Approve an order](/approvals/journeys/approve-order.md) _(intended)_
<!-- generated:end relations -->
