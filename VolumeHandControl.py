"""
VolumeHandControl.py
Lógica de mapeo distancia-volumen y control del volumen del sistema (Windows).
Usa pycaw para acceder a la API de audio de Windows.
"""
import math
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class VolumeController:
    """
    Controla el volumen del sistema Windows mediante pycaw.
    
    Mapea la distancia entre dedos (píxeles) al rango de volumen del
    dispositivo de audio (dB) y expone métodos simples para obtener/
    fijar el volumen como porcentaje (0.0 – 1.0).
    """

    def __init__(self, min_dist: float = 30, max_dist: float = 220):
        """
        Parámetros
        ----------
        min_dist : float
            Distancia mínima en píxeles → volumen 0%.
        max_dist : float
            Distancia máxima en píxeles → volumen 100%.
        """
        self.min_dist = min_dist
        self.max_dist = max_dist

        # Inicializar interfaz pycaw
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self._volume = cast(interface, POINTER(IAudioEndpointVolume))

        # Rango de dB del dispositivo
        vol_range = self._volume.GetVolumeRange()
        self._min_vol_db: float = vol_range[0]
        self._max_vol_db: float = vol_range[1]

    # ------------------------------------------------------------------ #
    #  Propiedades públicas                                                #
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
    #  Control del volumen                                                 #
    # ------------------------------------------------------------------ #

    def set_volume(self, level: float):
        """
        Fija el volumen del sistema.
        
        Parámetros
        ----------
        level : float
            Valor entre 0.0 (silencio) y 1.0 (máximo).
        """
        level = max(0.0, min(1.0, level))
        self._volume.SetMasterVolumeLevelScalar(level, None)

    def distance_to_volume(self, distance: float) -> float:
        """
        Convierte la distancia entre dedos en un nivel de volumen (0.0–1.0).

        Parámetros
        ----------
        distance : float
            Distancia en píxeles entre pulgar e índice.

        Devuelve
        -------
        float : nivel de volumen 0.0–1.0
        """
        vol = np.interp(distance, [self.min_dist, self.max_dist], [0.0, 1.0])
        return float(vol)

    def apply_from_distance(self, distance: float) -> float:
        """
        Calcula el volumen a partir de la distancia y lo aplica al sistema.

        Devuelve
        -------
        float : nuevo nivel de volumen aplicado (0.0–1.0).
        """
        new_vol = self.distance_to_volume(distance)
        self.set_volume(new_vol)
        return new_vol
