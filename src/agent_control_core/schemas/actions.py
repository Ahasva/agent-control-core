from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MachineActionType(str, Enum):
    ENABLE_MACHINE = "enable_machine"
    DISABLE_MACHINE = "disable_machine"
    SET_IDLE = "set_idle"
    SET_READY = "set_ready"
    START_CALIBRATION = "start_calibration"
    START_ACTIVE = "start_active"
    MOVE_SERVO = "move_servo"
    REQUEST_APPROVAL = "request_approval"
    GRANT_APPROVAL = "grant_approval"
    RAISE_FAULT = "raise_fault"
    CLEAR_FAULT = "clear_fault"
    LOCK_MACHINE = "lock_machine"
    UNLOCK_MACHINE = "unlock_machine"
    SOUND_ALARM = "sound_alarm"
    ACKNOWLEDGE = "acknowledge"


class MachineAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: MachineActionType = Field(..., description="Type of executable machine action")
    target_value: int | None = Field(..., description="Optional numeric target, e.g. servo angle")
    reason: str | None = Field(..., description="Human-readable reason for the action")


class ExecutionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: list[MachineAction] = Field(..., description="Ordered executable actions")