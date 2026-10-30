---
type: Area Map
title: Ordering map
description: Entities and screen navigation in the Ordering Area.
generated: { by: process:lore-build }
---

# Ordering map

Buyers create, submit and track purchase orders

## Entities

```mermaid
erDiagram
  Customer
  Order
  Order_Line
  Customer ||--o{ Order : "has (intended)"
  Order ||--o{ Order_Line : "has (intended)"
```

_Labels: (intended) = specified only · (actual) = seen in app or code only._

Open Gaps:
- ⚠ Order: [Cancel without confirmation](/conflicts/cancel-without-confirmation.md)

## Navigation

```mermaid
flowchart LR
  n_ordering_screens_new_order["New order"]
  n_ordering_screens_order_details["⚠ Order details"]
  n_ordering_screens_order_list["Order list"]
  n_approvals_screens_approval_inbox["Approval inbox"]
  n_ordering_screens_new_order -->|"navigates to"| n_ordering_screens_order_details
  n_ordering_screens_order_details -->|"navigates to"| n_ordering_screens_order_list
  n_ordering_screens_order_details -.->|"navigates to"| n_approvals_screens_approval_inbox
  n_ordering_screens_order_list -->|"navigates to"| n_ordering_screens_order_details
  n_ordering_screens_order_list -->|"navigates to"| n_ordering_screens_new_order
  linkStyle 0 stroke:#e67e00,stroke-width:2px
  linkStyle 1 stroke:#e67e00,stroke-width:2px
  linkStyle 3 stroke:#e67e00,stroke-width:2px
  linkStyle 4 stroke:#e67e00,stroke-width:2px
  classDef gap fill:#fde2e2,stroke:#c00,color:#900
  classDef unverified color:#777,stroke:#aaa
  class n_ordering_screens_order_details gap
```

_Legend: dashed arrow = intended only (not seen in app or code) · orange arrow = actual only (not specified) · red ⚠ = open Gap · grey = unverified._
