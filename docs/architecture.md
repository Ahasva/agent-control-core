# Architecture

## Overview

Agent Control Core implements a **deterministic control architecture** for AI-assisted systems.

It enforces a strict execution pipeline:

**TaskRequest → ExecutionPlan → RiskAssessment → PolicyDecision → Execution → Audit**

This pipeline ensures that **no action reaches execution without passing structured validation, risk evaluation, and policy enforcement**.

---

## High-Level Control Flow

```mermaid
flowchart LR
    U[User / Operator] --> T[TaskRequest]
    T --> P[ExecutionPlan]
    P --> R[RiskAssessment]
    R --> D[PolicyDecision]

    D -->|allow| X[ExecutionLayer]
    D -->|require approval| A[ApprovalWorkflow]
    D -->|deny| B[Blocked]

    A --> D2[Re-evaluate Policy]
    D2 --> X

    X --> M[Machine / Tool]
    X --> L[Audit Log]

    B --> L
```

---

## Core Principle

> The LLM may propose actions — but it never decides execution.

The system separates:

- intent (user / LLM)
- judgment (risk)
- authority (policy)
- execution (controlled layer)

---

## Layered Architecture

### 1. TaskRequest — Untrusted Intent

Represents raw user input:

- defined in: `schemas/tasks.py`
- created in: `demo.py`, `operator_loop.py`

```mermaid
flowchart TD
    U[User Input] --> T[TaskRequest]
    T --> N[Raw intent / not trusted]
```
This layer is always treated as untrusted input.

### 2. ExecutionPlan — Proposed Actions

Structured plan describing intended steps:

- defined in: schemas/plans.py
- created by:
- mock_generate_plan()
- live_generate_plan()
- deterministic parsing (machine demo)

```mermaid
flowchart TD
    T[TaskRequest] --> P[ExecutionPlan]
    P --> N[Proposal only / not yet allowed]
```

Includes metadata such as:

- destructive actions
- external communication
- credential access

### 3. RiskAssessment — Advisory Judgment

Evaluates the potential impact of the plan:

- defined in: `schemas/policies.py`
- created by:
- `mock_assess_risk()`
- `live_assess_risk()`
- deterministic machine risk logic

```mermaid
flowchart TD
    P[ExecutionPlan] --> R[RiskAssessment]
    R --> N[Advisory only / not authoritative]
```

Produces:

- risk level (low, medium, high, critical)
- reasons
- sensitive capabilities

### 4. PolicyDecision — Authoritative Control

The single point of authority:

- defined in: `schemas/policies.py`
- created by: `policies/engine.py`

```mermaid
flowchart TD
    T[TaskRequest] --> D[PolicyDecision]
    P[ExecutionPlan] --> D
    R[RiskAssessment] --> D
    S[System State] --> D

    D -.-> N[Deterministic<br/>Final authority]
```

Possible outcomes:

- allow
- require_approval
- deny

### 5. Execution Layer — Controlled Actuation

Only executed if policy allows it:

- implemented in: `execution/executor.py`
- uses:
- MachineExecutor
- ExecutionBundle

```mermaid
flowchart TD
    D[PolicyDecision] -->|allow| X[Execution]
    X --> M[Machine / Tool]

    D -.-> N1[Deterministic decision]
    X -.-> N2[Bounded execution<br/>No direct LLM control]
```

Important constraint:

> Execution is never performed directly from plan or LLM output.

### 6. Audit Layer — Full Traceability

Every step is logged:

- defined in: `schemas/audit.py`
- logged via: `audit/logger.py`

```mermaid
flowchart TD
    T --> L[Audit Log]
    P --> L
    R --> L
    D --> L
    X --> L
```

Provides:

- traceability
- reproducibility
- compliance support

---

## Machine Control Extension

The machine demo extends the architecture with state-aware control and hardware enforcement.

```mermaid
flowchart TD
    U[Operator Input] --> T[TaskRequest]
    T --> I[Intent Parser]

    I -->|recognized| P[Deterministic Plan]
    I -->|unrecognized| F[Fail Closed]

    P --> R[Deterministic Risk]
    R --> D[PolicyDecision]

    D -->|allow| E[Execution Bundle]
    E --> H[Hardware Layer]

    H --> S[Machine State]
    S --> D

    F --> L[Audit Log]
```

Key additions:

- deterministic intent parsing
- bounded actuator control
- hardware approval input
- state-based constraints

---

## Safety Architecture

The system enforces multiple independent safety layers:

```mermaid
flowchart LR
    I[Intent] --> C1[Parser Validation]
    C1 --> C2[Risk Assessment]
    C2 --> C3[Policy Engine]
    C3 --> C4[Execution Constraints]
    C4 --> C5[Hardware Safeguards]
```

Each layer can independently block unsafe behavior.

---

## Fail-Closed Guarantee

A core property of the architecture:

If the system is uncertain, ambiguous, or detects unsafe intent → it does nothing.

```mermaid
flowchart TD
    U[User Input] --> P{Recognized?}

    P -->|No| F[Fail Closed]
    P -->|Yes| R[Risk + Policy]

    R -->|Unsafe| B[Blocked]
    R -->|Safe| E[Execute]

    F --> L[Audit]
    B --> L
```

This ensures:

- no implicit execution
- no fallback to unsafe behavior
- no reliance on LLM interpretation alone

---

## Separation of Concerns

| **Layer** | **Responsibility** | **Trust Level** |
| TaskRequest | raw input | untrusted |
| ExecutionPlan | proposal | untrusted |
|RiskAssessment | advisory | semi-trusted |
|PolicyDecision | authority | trusted |
|Execution | actuation | fully controlled |
|Audit | traceability | immutable |

---

## Key Architectural Properties

**Deterministic Control**

> Policy decisions are rule-based and reproducible.

**State Awareness**

> Execution depends on real system or machine state.

**Bounded Execution**

> All actions are constrained before execution.

**Human Oversight**

> Approval is required for sensitive actions.

**Auditability**

> Every decision and action is logged.

---

## Summary

Agent Control Core is not an agent framework.

It is a **control system for agents**.

It ensures that:

- models propose
- systems evaluate
- policies decide
- machines execute under constraint

This separation is what makes safe agent-driven execution possible.