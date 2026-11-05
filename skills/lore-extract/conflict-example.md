# Spec Conflict page in a Proposal

Two `intended` documents give different values. `about` names the pages the conflict touches; the body records both sides with a cite each and names who can decide. A `Gap` page has the same shape, with an `actual` Source on one side.

```yaml
- id: conflicts/approval-threshold-amount
  type: Spec Conflict
  title: Approval threshold amount
  description: The Confluence approval rules say 10 000 EUR, the BRD says 5 000 EUR.
  about: [approvals/rules/approval-threshold]
  body: |
    # Approval threshold amount

    | Source | Value | Date |
    |---|---|---|
    | Approval rules (Confluence) v12[^rules] | 10 000 EUR | 2026-06-01 |
    | Purchase approval BRD v2[^brd] | 5 000 EUR | 2025-03-14 |

    The newer page is not automatically right. **Who can answer:** the product owner for Approvals.
  cites:
    rules:
      doc: docs/approval-rules.pdf
      quote: Every order with a total above 10 000 EUR needs approval.
    brd:
      doc: docs/purchase-approval-brd.docx
      quote: Every order with a total above 5 000 EUR needs approval before it is processed.
```
