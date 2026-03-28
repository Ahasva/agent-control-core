# Policy Model

## Overview
The policy model determines whether a proposed plan may proceed, must be denied, or requires explicit approval.

## Inputs
- task request
- execution plan
- risk assessment
- application policy configuration

## Outputs
- allow
- deny
- require approval

## High-risk triggers
The following plan characteristics are treated as high risk by default:
- money movement or purchases
- external communication
- credential handling
- destructive system changes
- actions with legal or contractual effect

## Principle
LLMs may help identify risk signals, but the final policy decision is made by deterministic code.

## Fail-closed behavior
If risk is unclear and the action is sensitive, the system should require approval or deny execution.

## Future extensions
- role-based approval rules
- environment-aware policy
- action-specific constraints
- delegated scopes and session-specific permissions