# Architecture

## Overview

Agent Control Core is built as a layered control pipeline:

TaskRequest → ExecutionPlan → RiskAssessment → PolicyDecision → AuditEvent

Each stage has a distinct responsibility.

Layers

1. TaskRequest

Represents the raw user request.
	•	defined in: src/agent_control_core/schemas/tasks.py
	•	created in: src/agent_control_core/demo.py

This layer is treated as untrusted intent.

⸻

2. ExecutionPlan

Represents the structured plan proposed by the agent.
	•	defined in: src/agent_control_core/schemas/plans.py
	•	created by:
	•	mock_generate_plan() in demo.py
	•	live_generate_plan() in demo.py
	•	call_structured_model() in llm/structured.py

This layer is treated as a proposal, not an authorization.

⸻

3. RiskAssessment

Represents the structured risk estimate for the plan.
	•	defined in: src/agent_control_core/schemas/policies.py
	•	created by:
	•	mock_assess_risk() in demo.py
	•	live_assess_risk() in demo.py
	•	call_structured_model() in llm/structured.py

This layer is treated as advisory model judgment.

⸻

4. PolicyDecision

Represents the final deterministic decision.
	•	defined in: src/agent_control_core/schemas/policies.py
	•	created by: evaluate_plan() in src/agent_control_core/policies/engine.py

Possible outcomes:
	•	allow
	•	require_approval
	•	deny

This is the authoritative control decision.

⸻

5. AuditEvent

Represents traceable workflow events.
	•	defined in: src/agent_control_core/schemas/audit.py
	•	emitted in: demo.py
	•	logged by: audit/logger.py

This layer provides auditability and traceability.

Safety model

The architecture intentionally separates:
	•	LLM reasoning
	•	deterministic rule evaluation
	•	final enforcement

This prevents the model from being the sole authority.