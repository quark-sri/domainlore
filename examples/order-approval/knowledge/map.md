---
type: Context Map
title: Context map
description: The Areas of the domain and how they depend on each other.
generated: { by: process:lore-build }
---

# Context map

```mermaid
flowchart LR
  n_approvals["Approvals"]
  n_ordering["Ordering"]
  n_approvals --> n_ordering
  n_ordering --> n_approvals
```

_Arrows point from an Area to an Area it depends on._
