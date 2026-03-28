from agent_control_core.schemas.plans import ExecutionPlan
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


def task_is_critical_by_intent(task: TaskRequest) -> bool:
    return task_requests_review_bypass(task) and task_targets_production_config(task)