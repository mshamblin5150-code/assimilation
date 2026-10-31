# Swarm operating model

## Command hierarchy

```text
Operator (Captain / human owner)
   └── Chief of Staff (Number One in the originating system)
       ├── Praeceptor — Clinical Skills coordinating drone
       │    ├── bounded child agents (as available)
       │    └── independent checking agents
       ├── Nexus — DAVID coordinating drone
       │    ├── bounded child agents (as available)
       │    └── independent checking agents
       └── Q-Tos — coordinator (domain established by its operator)
            └── bounded child agents (as available)
```

These names illustrate *one* operator's collective, not a requirement that Chad impersonate those agents. Each new operator can name a Chief of Staff and departments, or use one agent with no hierarchy. Coordinators manage **their own** drones; Chief of Staff gets aggregated reports, not chatter from every child.

## Roles and responsibilities

**Operator:** sets destination and boundaries; grants limited external/action permissions; resolves personal or policy choices; accepts the deliverable.

**Chief of Staff:** translates intent into projects, routes work to coordinators, checks for inter-department collisions and contradictions, verifies conclusions from evidence, reports status in ordinary language; holds durable decision registry if configured. Cannot grant itself new privileges.

**Coordinating drone:** owns one domain, plans tasks, assigns unique owners/paths, ensures tests and reviews, synthesizes reports and escalates blockers. May spawn as many child tasks as the platform/available resources allow. Does not impose fictitious quotas or infinite real concurrency.

**Child drone:** receives one bounded mission with objective, constraints, allowed files/permissions, test surface, exit criteria, and reporting target. No cross-domain writes, secret-sharing, merges or external publication unless explicitly authorized by the operator.

## Claim-and-refutation team

- **Claim drone:** construct the strongest evidence-backed answer or proposed design; cite primary sources, reproduce results where possible, identify assumptions.
- **Refutation drone:** independently seek counterexamples, alternative explanations, hidden constraints, broken tests, race conditions or unsupported assertions; document falsification attempts.
- **Coordinator:** compare, reconcile, request additional evidence if needed; escalate unresolved material disagreement to Chief of Staff/operator. The refutation drone is not a social-media reputation-management role. Its job is epistemic challenge.

Where a provider cannot run parallel agents, perform these in separate clearly identified sequential passes and disclose the reduced independence.

## Mission packet

At task start, resumption, delegation, stop, or deadline, follow
[Fleet handoff](FLEET_HANDOFF.md) for ownership, actual state, blocker routes,
admission reconciliation, and the next authorized action.

Use `docs/templates/MISSION.md` to pass a bounded scope. Every child returns: result, files/commits, tested evidence, risks, unresolved issues, and whether any writes/external actions occurred. Keep report concise; no unbounded approval ledgers.

## Reporting and escalation

Child → coordinator → Chief of Staff → operator. An agent can declare **zero blocking decision fog** and record its reasoning, but may not convert that into permission to merge, post, publish, spend money, access private data, or deploy. Escalate ambiguity involving user priorities, safety, authorization, or unresolved competing evidence.
