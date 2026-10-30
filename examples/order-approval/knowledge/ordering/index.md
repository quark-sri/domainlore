# Map

* [Ordering map](map.md) - Entities and navigation diagrams

# Entities

* [Customer](entities/customer.md) - The company that places Orders through its Buyers.
* [Order](entities/order.md) - A buyer's request to purchase one or more products from a supplier.
* [Order Line](entities/order-line.md) - One product, quantity and price within an Order.

# Rules

* [Minimum order value](rules/minimum-order-value.md) - An Order can only be submitted when its total is at least 50 EUR. _(unverified)_

# Actors

* [Buyer](actors/buyer.md) - A person who creates and submits Orders for a Customer.

# Journeys

* [Place an order](journeys/place-order.md) - A Buyer creates an Order, adds lines and submits it.

# Screens

* [New order](screens/new-order.md) - Form to create an Order and add Order Lines. _(machine-confirmed)_
* [Order details](screens/order-details.md) - Shows one Order with its lines, status and actions. _(machine-confirmed)_
* [Order list](screens/order-list.md) - Lists the Customer's Orders with status and total. _(machine-confirmed)_

# Terms

* [PO](terms/po.md) - Abbreviation used by finance for an Order. _(unverified)_
