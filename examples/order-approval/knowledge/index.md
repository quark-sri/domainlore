---
okf_version: "0.2"
---

# Start here

* [Context map](map.md) - Areas and how they depend on each other
* [Glossary](GLOSSARY.md) - Canonical terms and the words to avoid
* [Open questions](questions.md) - Ambiguities waiting for a person

# Areas

* [Approvals](approvals/) - Approvers accept or reject orders above the approval threshold
* [Ordering](ordering/) - Buyers create, submit and track purchase orders

# Key entities

* [Approval Request](approvals/entities/approval-request.md) - A request for an Approver to accept or reject one Order.
* [Customer](ordering/entities/customer.md) - The company that places Orders through its Buyers.
* [Order](ordering/entities/order.md) - A buyer's request to purchase one or more products from a supplier.
* [Order Line](ordering/entities/order-line.md) - One product, quantity and price within an Order.

# Open conflicts

* [Approval threshold amount](conflicts/approval-threshold-amount.md) - Spec Conflict: Confluence says 10 000 EUR, the BRD says 5 000 EUR.
* [Cancel without confirmation](conflicts/cancel-without-confirmation.md) - Gap: The policy asks the buyer to confirm a cancel; the app cancels at once.
