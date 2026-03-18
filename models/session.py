"""
models/session.py
Modelo de datos para una sesión de uso de la aplicación.
"""
from datetime import datetime


class Session:
    """Representa una sesión de uso de la aplicación."""

    def __init__(self, start_time: datetime = None):
        self.start_time: datetime = start_time or datetime.utcnow()
        self.end_time: datetime | None = None
        self.duration_seconds: float = 0.0

    def close(self):
        """Cierra la sesión y calcula la duración."""
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convierte el modelo a un diccionario para guardar en MongoDB."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
        }

    def __repr__(self):
        return (
            f"Session(start={self.start_time}, end={self.end_time}, "
            f"duration={self.duration_seconds:.1f}s)"
        )
