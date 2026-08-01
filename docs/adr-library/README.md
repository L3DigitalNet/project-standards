---
schema_version: '1.1'
id: 'index-0aah3n-adr-library'
title: 'ADR Library'
description: 'Index of draft ADR templates being evaluated as inputs to a future versioned ADR package library.'
doc_type: 'index'
status: 'draft'
created: '2026-08-01'
updated: '2026-08-01'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'index'
aliases: []
related:
  - 'docs/TODO.md'
  - 'docs/adr-library/git/branch-integration-and-protection.md'
  - 'standards/adr/README.md'
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---

# ADR Library

## Purpose

This directory collects draft Architectural Decision Record (ADR) templates for common repository management, software development, and operations practices. The drafts are reference inputs for a future versioned ADR package library; they are not released package payloads or accepted project decisions.

Before adoption, review and adapt each draft for the target repository, add the metadata required by that repository, resolve its placeholders, and record explicit acceptance.

## Git and branch management

### [Branch Integration and Protection Strategy](git/branch-integration-and-protection.md)

Provides a draft for a simple `dev`/`main` branch relationship and local Git-hook safeguards intended to prevent ordinary development from being committed directly to `main`.
