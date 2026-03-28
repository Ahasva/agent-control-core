# Design Principles

## Structured outputs by default
All major workflow steps should emit machine-validated data structures.

## Least privilege
Agents should receive the minimum access, tools, and context necessary.

## Separation of powers
Planning, risk estimation, policy enforcement, approval, and execution should remain separate concerns.

## Human approval for high-risk actions
Actions involving money, external communication, credentials, destructive changes, or legal/financial commitments require explicit approval.

## Fail closed
If the system is uncertain about risk, policy applicability, or authorization, it should deny or pause rather than continue.

## Auditability
Important decisions and actions must generate auditable records.

## Deterministic enforcement
LLMs may assist with reasoning and classification, but policy enforcement must be deterministic and inspectable.

## Explainability
Denials, approvals, and pauses should be explainable to the user in clear language.