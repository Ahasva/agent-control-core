from __future__ import annotations

from dataclasses import dataclass

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


@dataclass
class SerialMachineLink:
    port: str
    baudrate: int = 115200
    timeout: float = 1.0

    def __post_init__(self) -> None:
        self._connection = None

    def connect(self) -> None:
        if serial is None:
            raise ImportError("pyserial is not installed. Install it with: pip install pyserial")
        self._connection = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self._connection.reset_input_buffer()
        self._connection.reset_output_buffer()

    def is_connected(self) -> bool:
        return self._connection is not None

    def send_command(self, command: str) -> None:
        if self._connection is None:
            raise RuntimeError("Serial connection is not open.")
        payload = f"{command}\n".encode("utf-8")
        self._connection.write(payload)

    def read_line(self) -> str:
        if self._connection is None:
            raise RuntimeError("Serial connection is not open.")
        raw = self._connection.readline()
        line = raw.decode("utf-8", errors="ignore").strip()
        return line


    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None