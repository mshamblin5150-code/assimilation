# ADR 0001: portable doctrine, human command, bounded autonomy

- **Status:** Accepted for Assimilation v0.1
- **Date:** 2026-10-27
- **Decision owner:** Originating operator; new adopters remain owners of their projects.

## Context

Rigid agent micromanagement created bottlenecks; unbounded concurrency created collisions. A good package must transfer engineering discipline without duplicating private history or ceremonial machinery. External skills evolve, and readers have different platform capabilities.

## Decision

Use public Markdown for operating instructions, upstream *complete* sources installed separately, skill routing by task stage, and optional Chief of Staff → coordinator → child architecture. Resolve meaningful design questions through `grill-with-docs`; use `wayfinder` only for multi-session fog. Record durable choices in ADRs. Agents may declare evidence-supported ZERO_BLOCKING_FOG, but humans retain consequential authority. Review upstream versions monthly; never silently execute or merge new upstream code.

## Alternatives

- One huge prompt: rejected because not source-grounded or maintainable.
- Mandatory multi-agent hierarchy on every task: rejected as wasteful for simple tasks.
- Automatic upstream updates: rejected as a trust and reproducibility risk.
- Live Open Brain access: rejected as unnecessary exposure of private knowledge.

## Consequences

The repository works as a readable playbook even without agent tools. Full skill execution requires a compatible environment. Generated wrappers point to original source files; they are not independent rewrites. Humans remain accountable for releases and real-world acceptance.
