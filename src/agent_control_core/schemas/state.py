from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class MachineMode(str, Enum):
    OFF = "off"
    IDLE = "idle"
    READY = "ready"
    CALIBRATION = "calibration"
    ACTIVE = "active"
    FAULT = "fault"
    LOCKED = "locked"


class SystemState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_mode: MachineMode = Field(..., description="Current high-level machine mode")
    machine_enabled: bool = Field(..., description="Whether the machine is enabled")
    approval_pending: bool = Field(..., description="Whether an approval is currently pending")
    approval_granted: bool = Field(..., description="Whether approval has been granted")
    fault_active: bool = Field(..., description="Whether the machine is currently faulted")
    lock_active: bool = Field(..., description="Whether the machine is currently locked")
    servo_angle: int = Field(..., ge=0, le=180, description="Current actuator angle in degrees")
    requested_angle: int | None = Field(..., description="Requested target angle if any")
    potentiometer_raw: int = Field(..., ge=0, le=1023, description="Raw potentiometer reading")
    potentiometer_angle: int = Field(..., ge=0, le=180, description="Mapped potentiometer angle")
    last_error: str | None = Field(..., description="Last error message if any")
    last_event: str | None = Field(..., description="Last state/event message if any")

    @classmethod
    def initial(cls) -> "SystemState":
        return cls(
            machine_mode=MachineMode.OFF,
            machine_enabled=False,
            approval_pending=False,
            approval_granted=False,
            fault_active=False,
            lock_active=False,
            servo_angle=90,
            requested_angle=None,
            potentiometer_raw=0,
            potentiometer_angle=0,
            last_error=None,
            last_event="initial_state_created",
        )