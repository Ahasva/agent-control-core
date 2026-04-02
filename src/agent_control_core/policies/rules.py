"""
DECISION LOGIC (FACTS), based on fact-checking helper functions, i.e. answers questions, e.g.:
    - 	“Does this plan have destructive steps?”
    -   “Does this task try to skip review?”

Therefore, it serves as fact extraction, by evaluation X as either true or false!
This is of grave importance for the POLICY LOGIC (ENGINE)

Plan: `plan_touches_external_comms(plan)` & `plan_is_destructive(plan)` inspect the ExecutionPlan
Task: `task_requests_review_bypass(task)` & `task_targets_production_config(task)` inspect the raw TaskRequest

"""

from agent_control_core.machine.state_logic import requested_angle_is_safe
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.state import MachineMode, SystemState
from agent_control_core.schemas.tasks import TaskRequest


def plan_touches_money(plan: ExecutionPlan) -> bool:
    return any(step.touches_money for step in plan.steps)


def plan_touches_credentials(plan: ExecutionPlan) -> bool:
    return any(step.touches_credentials for step in plan.steps)


def plan_touches_external_comms(plan: ExecutionPlan) -> bool:
    return any(step.touches_external_comms for step in plan.steps)


def plan_is_destructive(plan: ExecutionPlan) -> bool:
    return any(step.destructive_action for step in plan.steps)


def task_requests_review_bypass(task: TaskRequest) -> bool:
    text = f"{task.goal} {task.context or ''}".lower()
    bypass_signals = [
        "skip review",
        "without review",
        "bypass review",
        "no review",
        "skip checks",
        "without checks",
    ]
    return any(signal in text for signal in bypass_signals)


def task_targets_production_config(task: TaskRequest) -> bool:
    text = f"{task.goal} {task.context or ''}".lower()
    signals = [
        "production configuration",
        "replace it with the new experimental version",
        "replace the current production configuration",
        "deploy to production",
        "roll out the change quickly",
    ]
    return any(signal in text for signal in signals)


def task_requests_immediate_motion(task: TaskRequest) -> bool:
    text = f"{task.goal} {task.context or ''}".lower()
    signals = [
        "move immediately",
        "run immediately",
        "start immediately",
        "directly run",
        "directly move",
    ]
    return any(signal in text for signal in signals)


def task_is_critical_by_intent(task: TaskRequest) -> bool:
    return task_requests_review_bypass(task) and task_targets_production_config(task)


def state_is_faulted(state: SystemState) -> bool:
    return state.fault_active or state.machine_mode == MachineMode.FAULT


def state_is_locked(state: SystemState) -> bool:
    return state.lock_active or state.machine_mode == MachineMode.LOCKED


def state_is_ready(state: SystemState) -> bool:
    return state.machine_enabled and state.machine_mode == MachineMode.READY


def state_requires_approval(state: SystemState) -> bool:
    return state.approval_pending and not state.approval_granted


def requested_angle_from_state_is_safe(state: SystemState) -> bool:
    if state.requested_angle is None:
        return True
    return requested_angle_is_safe(state.requested_angle)