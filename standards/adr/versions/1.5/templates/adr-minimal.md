---
schema_version: '1.1'
id: 'adr-0000-repo-name-short-title' # globally unique; filename omits repo-name
title: 'ADR 0000: Short Title'
description: 'Decision record for a significant architectural or project decision.'
doc_type: 'adr'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: ''
consumer: 'unknown'
tags: []
aliases: []
related: []
supersedes: []
superseded_by: null
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
  amends: [] # IDs of ADRs this record partially amends; reciprocal with their amended_by
  amended_by: [] # filled in later, by whoever amends this record
---

# {short title, representative of the bounded decision}

<!-- Amendment notes go here once this record is amended, not while it is drafted. -->

## Context and Problem Statement

{State the governed concern, population, applicability condition, realistic exclusions, and related decisions that remain open. End with one question no broader than that boundary.}

## Considered Options

{List alternatives that answer the same bounded question for the same population.}

- {title of option 1}
- {title of option 2}

## Decision Outcome

Chosen option: "{title of option 1}", because {justification}.

This decision governs {concern} for {population} when {applicability condition}. It does not govern {explicit exclusions}; those concerns remain undecided or are governed separately.

<!-- Optional. Describe effects only; do not expand the decision. -->

### Consequences

- Good, because {positive consequence}
- Bad, because {negative consequence}
