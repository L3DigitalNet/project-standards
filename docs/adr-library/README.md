# ADR Library

## Purpose

A collection of Architectural Decision Records (ADRs) for common repository mangagement, software development, and operations practices. Each ADR is ready for adoption with or without modification.

## Table of Contents

- [ADR Library](#adr-library)
  - [Purpose](#purpose)
  - [Table of Contents](#table-of-contents)
  - [**Category:** Git \& Branch Management](#category-git--branch-management)
    - [Branch Integration and Protection Strategy](#branch-integration-and-protection-strategy)

## **Category:** Git & Branch Management

### [Branch Integration and Protection Strategy](git/branch-integration-and-protection.md)

Defines a simple `dev`/`main` branch relationship and local git-hook-based safeguards to prevent ordinary development from being committed directly to `main`.
