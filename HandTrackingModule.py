"""
HandTrackingModule.py
Módulo reutilizable de detección de manos con MediaPipe (API moderna mp.tasks).
Devuelve landmarks normalizados, bounding box y distancia entre dos dedos.

Compatibilidad: mediapipe >= 0.10.x  /  Python 3.10+
"""
import math
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import HandLandmarkerOptions, RunningMode


# ────────────────────────────────────────────────────────────────────────────
#  Descarga automática del modelo si falta
# ────────────────────────────────────────────────────────────────────────────
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = Path(__file__).parent / "hand_landmarker.task"

def _ensure_model():
    if not MODEL_PATH.exists():
        print(f"[HandDetector] Descargando modelo MediaPipe → {MODEL_PATH.name} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[HandDetector] Modelo descargado.")

_ensure_model()


# ────────────────────────────────────────────────────────────────────────────
#  IDs de landmarks (igual que antes)
# ────────────────────────────────────────────────────────────────────────────
TIP_IDS   = [4, 8, 12, 16, 20]   # pulgar, índice, medio, anular, meñique
THUMB_TIP  = 4
INDEX_TIP  = 8
PINKY_TIP  = 20
PINKY_MCP  = 17

# Conexiones para dibujar el esqueleto (pares de IDs)
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),          # pulgar
    (0,5),(5,6),(6,7),(7,8),          # índice
    (0,9),(9,10),(10,11),(11,12),     # medio
    (0,13),(13,14),(14,15),(15,16),   # anular
    (0,17),(17,18),(18,19),(19,20),   # meñique
    (5,9),(9,13),(13,17),(0,17),      # palma
]


class HandDetector:
    """
    Envuelve MediaPipe Hand Landmarker (API tasks) para uso sencillo con OpenCV.

    Parámetros
    ----------
    max_hands : int        Número máximo de manos a detectar.
    detection_confidence   Confianza mínima en la detección.
    tracking_confidence    Confianza mínima en el tracking.
    """

    # Exponer constantes de landmarks a nivel de clase
    TIP_IDS   = TIP_IDS
    THUMB_TIP  = THUMB_TIP
    INDEX_TIP  = INDEX_TIP
    PINKY_TIP  = PINKY_TIP
    PINKY_MCP  = PINKY_MCP

    def __init__(
        self,
        max_hands: int = 1,
        detection_confidence: float = 0.7,
        tracking_confidence:  float = 0.7,
    ):
        base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = HandLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._detection  = None   # resultado del último frame

    # ------------------------------------------------------------------ #
    #  Detección principal                                                 #
    # ------------------------------------------------------------------ #

    def find_hands(self, frame, draw: bool = True):
        """
        Procesa un frame BGR, detecta manos y opcionalmente las dibuja.

        Devuelve el frame (con o sin anotaciones).
        """
        rgb        = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._detection = self._landmarker.detect(mp_image)

        if draw and self._detection.hand_landmarks:
            h, w = frame.shape[:2]
            for hand_lms in self._detection.hand_landmarks:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms]
                # Dibujar conexiones
                for a, b in HAND_CONNECTIONS:
                    cv2.line(frame, pts[a], pts[b], (80, 180, 80), 2)
                # Dibujar puntos
                for i, (px, py) in enumerate(pts):
                    r = 6 if i in TIP_IDS else 4
                    cv2.circle(frame, (px, py), r, (255, 255, 255), cv2.FILLED)
                    cv2.circle(frame, (px, py), r, (0, 150, 255),   1)

        return frame

    # ------------------------------------------------------------------ #
    #  Landmarks y bounding box                                            #
    # ------------------------------------------------------------------ #

    def get_landmarks(self, frame, hand_no: int = 0) -> list[tuple[int, int, int]]:
        """
        Devuelve los 21 landmarks de la mano en coordenadas de píxel:
        [(id, x, y), ...] – vacío si no hay mano.
        """
        if not self._detection or not self._detection.hand_landmarks:
            return []
        if hand_no >= len(self._detection.hand_landmarks):
            return []

        h, w = frame.shape[:2]
        return [
            (idx, int(lm.x * w), int(lm.y * h))
            for idx, lm in enumerate(self._detection.hand_landmarks[hand_no])
        ]

    def get_bounding_box(self, frame, hand_no: int = 0) -> tuple | None:
        """
        Devuelve (x_min, y_min, x_max, y_max) del bounding box de la mano,
        con padding, o None si no hay mano detectada.
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms:
            return None
        xs = [lm[1] for lm in lms]
        ys = [lm[2] for lm in lms]
        pad = 20
        h, w = frame.shape[:2]
        return (
            max(0, min(xs) - pad),
            max(0, min(ys) - pad),
            min(w, max(xs) + pad),
            min(h, max(ys) + pad),
        )

    # ------------------------------------------------------------------ #
    #  Distancia entre dos landmarks                                       #
    # ------------------------------------------------------------------ #

    def get_distance(
        self,
        frame,
        lm_id1: int,
        lm_id2: int,
        hand_no:  int  = 0,
        draw:     bool = True,
    ) -> tuple[float, list, tuple | None]:
        """
        Calcula la distancia en píxeles entre dos landmarks y la dibuja.

        Devuelve (distancia, landmarks, punto_medio).
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms or lm_id1 >= len(lms) or lm_id2 >= len(lms):
            return 0.0, lms, None

        _, x1, y1 = lms[lm_id1]
        _, x2, y2 = lms[lm_id2]
        mx, my    = (x1 + x2) // 2, (y1 + y2) // 2
        distance  = math.hypot(x2 - x1, y2 - y1)

        if draw:
            cv2.circle(frame, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(frame, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.line(frame,   (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.circle(frame, (mx, my),  8, (255, 0, 255), cv2.FILLED)

        return distance, lms, (mx, my)

    # ------------------------------------------------------------------ #
    #  Estado de los dedos                                                 #
    # ------------------------------------------------------------------ #

    def fingers_up(self, frame, hand_no: int = 0) -> list[int]:
        """
        Devuelve [pulgar, índice, medio, anular, meñique] como 1 (arriba) / 0 (bajo).
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms or len(lms) < 21:
            return [0, 0, 0, 0, 0]

        fingers = []

        # Pulgar: comparar X con nodo anterior
        if lms[TIP_IDS[0]][1] < lms[TIP_IDS[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # El resto: comparar Y con el nodo 2 posiciones hacia la palma
        for tip_id in TIP_IDS[1:]:
            fingers.append(1 if lms[tip_id][2] < lms[tip_id - 2][2] else 0)

        return fingers

    def hands_detected(self) -> bool:
        """True si se detectó al menos una mano en el último frame."""
        return bool(self._detection and self._detection.hand_landmarks)
