"""
VolumeHandControl.py
Lógica de mapeo distancia-volumen y control del volumen del sistema (Windows).

Usa la API moderna de pycaw (>= 0.5): AudioDevice.EndpointVolume
en lugar del método Activate (eliminado en versiones recientes).
"""
import numpy as np
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class VolumeController:
    """
    Controla el volumen del sistema Windows mediante pycaw.

    Mapea la distancia entre dedos (píxeles) al rango de volumen del
    dispositivo de audio y expone métodos simples para obtener/fijar
    el volumen como fracción 0.0–1.0.
    """

    def __init__(self, min_dist: float = 30, max_dist: float = 220):
        self.min_dist = min_dist
        self.max_dist = max_dist

        # API moderna: AudioDevice expone .EndpointVolume directamente
        speakers = AudioUtilities.GetSpeakers()
        self._volume = speakers.EndpointVolume   # POINTER(IAudioEndpointVolume)

        vol_range = self._volume.GetVolumeRange()
        self._min_vol_db: float = vol_range[0]
        self._max_vol_db: float = vol_range[1]

    # ------------------------------------------------------------------ #
    #  Propiedades                                                         #
    # ------------------------------------------------------------------ #

    @property
    def current_volume(self) -> float:
        """Devuelve el volumen actual como fracción 0.0–1.0."""
        return self._volume.GetMasterVolumeLevelScalar()

    @property
    def current_volume_pct(self) -> int:
        """Devuelve el volumen actual como porcentaje 0–100."""
        return int(self.current_volume * 100)

    # ------------------------------------------------------------------ #
    #  Control                                                             #
    # ------------------------------------------------------------------ #

    def set_volume(self, level: float):
        """
        Fija el volumen del sistema.

        Parámetros
        ----------
        level : float  Valor entre 0.0 (silencio) y 1.0 (máximo).
        """
        level = max(0.0, min(1.0, level))
        self._volume.SetMasterVolumeLevelScalar(level, None)

    def distance_to_volume(self, distance: float) -> float:
        """Convierte distancia en píxeles a nivel de volumen 0.0–1.0."""
        return float(np.interp(distance, [self.min_dist, self.max_dist], [0.0, 1.0]))

    def apply_from_distance(self, distance: float) -> float:
        """Aplica al sistema el volumen calculado desde la distancia. Devuelve el nivel."""
        new_vol = self.distance_to_volume(distance)
        self.set_volume(new_vol)
        return new_vol
