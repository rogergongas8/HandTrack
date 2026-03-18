"""
models/volume_event.py
Modelo de datos para un evento de cambio de volumen.
"""
from datetime import datetime


class VolumeEvent:
    """Representa un cambio de volumen realizado por gesto de mano."""

    def __init__(
        self,
        session_id,
        previous_volume: float,
        new_volume: float,
        finger_distance: float,
        timestamp: datetime = None,
    ):
        self.session_id = session_id          # ID de la sesión en MongoDB
        self.timestamp: datetime = timestamp or datetime.utcnow()
        self.previous_volume: float = round(previous_volume, 2)
        self.new_volume: float = round(new_volume, 2)
        self.finger_distance: float = round(finger_distance, 2)

    def to_dict(self) -> dict:
        """Convierte el modelo a un diccionario para guardar en MongoDB."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "previous_volume": self.previous_volume,
            "new_volume": self.new_volume,
            "finger_distance": self.finger_distance,
        }

    def __repr__(self):
        return (
            f"VolumeEvent(prev={self.previous_volume:.0%}, "
            f"new={self.new_volume:.0%}, dist={self.finger_distance:.1f}px)"
        )
