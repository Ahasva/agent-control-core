# agent-control-core

A Python foundation for building controlled, auditable, policy-aware agent workflows.

## Purpose

This repository provides the control-plane building blocks for safe agentic systems:
- structured task intake
- plan generation
- risk assessment
- policy enforcement
- approval gating
- audit logging

It is designed for scenarios where an AI agent may eventually control powerful tools such as browsers, messaging, code execution, or financial actions, and where owner protection and human oversight are required.

## Current scope

This repository currently implements the control flow for:
1. receiving a task request
2. generating a structured execution plan
3. assessing task risk
4. applying deterministic policy checks
5. requiring approval or denying unsafe actions
6. recording audit events

## Design principles

- structured outputs by default
- least privilege
- fail closed on uncertainty
- human approval for high-risk actions
- auditability
- separation of planning, policy, and execution

## Roadmap

- execution adapters
- policy simulation suite
- approval broker
- secret/payment proxy interfaces
- sandbox/environment isolation concepts