---
type: Journey
title: Approve an order
description: An Approver reviews a pending request and approves or rejects it.
basis: intended
diagram: sequence
sources:
  - id: apr-3
    resource: https://jira.example.com/browse/APR-3
    title: "APR-3: Approval requests"
verified: { by: human:demo-reviewer, at: 2026-10-01T09:00:00Z }
steps:
  - { id: inbox, label: Open the approval inbox, screen: approvals/screens/approval-inbox, actor: approvals/actors/approver }
  - { id: details, label: Open the order, screen: ordering/screens/order-details, actor: approvals/actors/approver }
  - { id: decide, label: Approve or reject, screen: approvals/screens/approval-inbox, actor: approvals/actors/approver }
---

# Approve an order

[^apr-3]: APR-3: Approval requests

<!-- generated:start flow -->
## Flow

```mermaid
sequenceDiagram
  participant Approver as Approver
  participant Approval_inbox as Approval inbox
  participant Order_details as Order details
  Approver->>Approval_inbox: Open the approval inbox
  Approver->>Order_details: Open the order
  Approver->>Approval_inbox: Approve or reject
```
<!-- generated:end flow -->

<!-- generated:start relations -->
## Relations

- [Approver](/approvals/actors/approver.md) performs this _(intended)_
- [Approval inbox](/approvals/screens/approval-inbox.md) step of this
- [Order details](/ordering/screens/order-details.md) step of this
- ⚠ Gap (open): [No inbox link on Order details](/conflicts/no-inbox-link-on-order-details.md)
<!-- generated:end relations -->
