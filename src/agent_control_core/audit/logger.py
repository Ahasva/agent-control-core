from agent_control_core.schemas.audit import AuditEvent


def log_event(event: AuditEvent) -> None:
    print(event.model_dump_json(indent=2))