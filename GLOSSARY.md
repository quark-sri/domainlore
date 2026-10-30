# Domain Knowledge Base

Collects sourced facts about a product's business domain from tickets, docs, the live app and the code, and serves them to any AI coding agent as layered markdown.

## Knowledge

**Knowledge Base**:
The set of node pages, indexes and sources that describe one product's domain, kept in that product's repo.
_Avoid_: Wiki, brain, memory

**Node**:
One described thing in the Knowledge Base, of exactly one Node Type, with its own page.
_Avoid_: Item, record, document

**Fact**:
One statement about a Node or a Relation, backed by at least one Source.
_Avoid_: Claim, assertion, note

**Relation**:
A typed, directed link between two Nodes.
_Avoid_: Edge (in user-facing text), link, association

**Conflict**:
Two Facts from different Sources that cannot both be true, recorded until a person resolves it. Every Conflict is either a Gap or a Spec Conflict.
_Avoid_: Discrepancy, mismatch

**Gap**:
A Conflict between an Intended Fact and an Actual Fact: a likely defect or missing feature.
_Avoid_: Bug (until confirmed), deviation

**Spec Conflict**:
A Conflict between two Intended Facts: a question for the product owner.
_Avoid_: Ambiguity, contradiction

**Open Question**:
An ambiguity that neither the Sources nor the code settle, waiting for a person's answer.
_Avoid_: Clarification, TODO

## Basis

**Intended**:
The basis of a Fact that states what the product should do, from tickets or docs.
_Avoid_: Expected, specified

**Actual**:
The basis of a Fact that states what the product does, from the running app or the code.
_Avoid_: Real, implemented

## Node Types

**Entity**:
A thing in the business domain that the product stores or acts on.
_Avoid_: Object, model, table

**Lifecycle**:
The set of states an Entity can be in and the Transitions between them.
_Avoid_: Workflow, state machine, status flow

**Transition**:
A move of an Entity from one state to another, triggered by an Actor and possibly guarded by a Rule.
_Avoid_: Status change, step

**Rule**:
A business rule or constraint that governs one or more Entities.
_Avoid_: Requirement, policy, validation

**Actor**:
A role that a person or external system plays when it uses the product.
_Avoid_: User, persona

**Journey**:
A goal-driven sequence of steps that an Actor completes.
_Avoid_: Flow, use case, scenario

**Screen**:
A UI page or UI state that shows Entities and leads to other Screens.
_Avoid_: Page, view

**Term**:
A word, synonym or abbreviation that people use for a Node.
_Avoid_: Alias, keyword

**Source**:
The origin of a Fact: a ticket, doc page, crawl run or code location, recorded as a `sources` entry on the page that uses it.
_Avoid_: Reference, evidence, citation

## Trust

**Unverified**:
The trust level of a Fact that an AI extracted and nothing has checked yet.
_Avoid_: Inferred, draft, guessed

**Machine-confirmed**:
The trust level of a Fact seen directly in the running app or the code, or matched by an automatic cross-check between Sources.
_Avoid_: Observed, verified

**Human-reviewed**:
The trust level of a Fact that a person approved in review.
_Avoid_: Confirmed, approved, validated

**Proposal**:
A set of new or changed Facts from one extraction run, waiting for review.
_Avoid_: Draft, suggestion

## Disclosure

**Layer**:
One level of disclosure: L0 is the root index, L1 is an area index, L2 is a Node page.
_Avoid_: Tier, level

**Area**:
A bounded part of the domain with its own folder and index, such as billing; a bounded context in DDD terms.
_Avoid_: Module, context, section
