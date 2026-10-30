---
type: Area Map
title: Approvals map
description: Entities and screen navigation in the Approvals Area.
generated: { by: process:lore-build }
---

# Approvals map

Approvers accept or reject orders above the approval threshold

## Entities

```mermaid
erDiagram
  Approval_Request
  Approval_Request }o--|| Order : "belongs to (intended)"
```

_Labels: (intended) = specified only · (actual) = seen in app or code only._

## Navigation

```mermaid
flowchart LR
  n_approvals_screens_approval_inbox["⚠ Approval inbox"]
  n_ordering_screens_order_details["⚠ Order details"]
  n_approvals_screens_approval_inbox -->|"navigates to"| n_ordering_screens_order_details
  linkStyle 0 stroke:#e67e00,stroke-width:2px
  classDef gap fill:#fde2e2,stroke:#c00,color:#900
  classDef unverified color:#777,stroke:#aaa
  class n_approvals_screens_approval_inbox,n_ordering_screens_order_details gap
```

_Legend: dashed arrow = intended only (not seen in app or code) · orange arrow = actual only (not specified) · red ⚠ = open Gap · grey = unverified._
