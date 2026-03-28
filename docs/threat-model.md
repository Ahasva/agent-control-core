# Threat Model

## Scope
This document describes the primary failure and abuse modes relevant to powerful agent systems.

## Threat categories

### Unauthorized action
The agent performs an action the user did not intend or authorize.

### Scope creep
The agent expands a valid task into additional actions beyond the intended boundary.

### Credential exposure
The agent accesses, stores, or mishandles secrets, tokens, passwords, or payment instruments.

### Financial harm
The agent makes purchases, subscriptions, or transfers without proper review.

### Destructive action
The agent deletes files, changes settings, or modifies systems in irreversible ways.

### External communication risk
The agent sends emails, messages, or submissions that create commitments or reputational risk.

### Prompt injection / context poisoning
The agent is manipulated by hostile content in pages, documents, or messages.

### Overconfident execution
The agent proceeds despite weak evidence or low confidence.

### Accountability failure
There is no sufficient record of why an action was proposed, approved, denied, or executed.

## Design response
The system mitigates these threats through:
- typed plans
- risk assessment
- deterministic policy checks
- approval gating
- audit logging
- fail-closed behavior