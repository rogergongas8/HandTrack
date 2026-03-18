"""
HandTrackingModule.py
Módulo reutilizable de detección de manos con MediaPipe.
Devuelve landmarks normalizados, bounding box y distancia entre dos dedos.
"""
import math
import cv2
import mediapipe as mp


class HandDetector:
    """
    Envuelve MediaPipe Hands para detección y tracking de manos.

    Parámetros
    ----------
    max_hands : int
        Número máximo de manos a detectar.
    detection_confidence : float
        Confianza mínima para la detección inicial.
    tracking_confidence : float
        Confianza mínima para el tracking de landmarks.
    """

    # IDs de landmarks relevantes (mano derecha/izquierda)
    TIP_IDS = [4, 8, 12, 16, 20]   # pulgar, índice, medio, anular, meñique
    THUMB_TIP  = 4
    INDEX_TIP  = 8
    PINKY_TIP  = 20
    PINKY_MCP  = 17   # base del meñique

    def __init__(
        self,
        max_hands: int = 1,
        detection_confidence: float = 0.7,
        tracking_confidence: float = 0.7,
    ):
        self._mp_hands = mp.solutions.hands
        self._mp_draw  = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        self.hands = self._mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._results = None

    # ------------------------------------------------------------------ #
    #  Detección principal                                                 #
    # ------------------------------------------------------------------ #

    def find_hands(self, frame, draw: bool = True):
        """
        Procesa un frame BGR y detecta manos.

        Parámetros
        ----------
        frame : np.ndarray
            Frame capturado por OpenCV (BGR).
        draw : bool
            Si True, dibuja los landmarks sobre el frame.

        Devuelve
        -------
        frame : np.ndarray
            Frame (con o sin anotaciones).
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._results = self.hands.process(rgb)

        if draw and self._results.multi_hand_landmarks:
            for hand_lm in self._results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    frame,
                    hand_lm,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )
        return frame

    # ------------------------------------------------------------------ #
    #  Landmarks y bounding box                                            #
    # ------------------------------------------------------------------ #

    def get_landmarks(self, frame, hand_no: int = 0) -> list[tuple[int, int, int]]:
        """
        Devuelve los 21 landmarks de la mano indicada en coordenadas de píxel.

        Devuelve
        -------
        list of (id, x, y) – vacío si no hay mano detectada.
        """
        landmarks = []
        if not self._results or not self._results.multi_hand_landmarks:
            return landmarks

        if hand_no >= len(self._results.multi_hand_landmarks):
            return landmarks

        h, w, _ = frame.shape
        hand_lm = self._results.multi_hand_landmarks[hand_no]
        for idx, lm in enumerate(hand_lm.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            landmarks.append((idx, cx, cy))

        return landmarks

    def get_bounding_box(self, frame, hand_no: int = 0) -> tuple | None:
        """
        Devuelve el bounding box de la mano como (x_min, y_min, x_max, y_max)
        con un padding de 20 px, o None si no hay mano.
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms:
            return None

        xs = [lm[1] for lm in lms]
        ys = [lm[2] for lm in lms]
        pad = 20
        h, w, _ = frame.shape
        return (
            max(0, min(xs) - pad),
            max(0, min(ys) - pad),
            min(w, max(xs) + pad),
            min(h, max(ys) + pad),
        )

    # ------------------------------------------------------------------ #
    #  Distancia entre dedos                                               #
    # ------------------------------------------------------------------ #

    def get_distance(
        self,
        frame,
        lm_id1: int,
        lm_id2: int,
        hand_no: int = 0,
        draw: bool = True,
    ) -> tuple[float, list, tuple | None]:
        """
        Calcula la distancia en píxeles entre dos landmarks.

        Devuelve
        -------
        (distance, landmarks, midpoint) donde midpoint es (mx, my) o None.
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms or lm_id1 >= len(lms) or lm_id2 >= len(lms):
            return 0.0, lms, None

        _, x1, y1 = lms[lm_id1]
        _, x2, y2 = lms[lm_id2]
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        distance = math.hypot(x2 - x1, y2 - y1)

        if draw:
            cv2.circle(frame, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(frame, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.circle(frame, (mx, my), 8, (255, 0, 255), cv2.FILLED)

        return distance, lms, (mx, my)

    # ------------------------------------------------------------------ #
    #  Estado de los dedos                                                 #
    # ------------------------------------------------------------------ #

    def fingers_up(self, frame, hand_no: int = 0) -> list[int]:
        """
        Devuelve una lista de 5 valores (0/1) indicando si cada dedo está
        levantado: [pulgar, índice, medio, anular, meñique].
        """
        lms = self.get_landmarks(frame, hand_no)
        if not lms or len(lms) < 21:
            return [0, 0, 0, 0, 0]

        fingers = []

        # Pulgar – comparar x con el nodo anterior
        if lms[self.TIP_IDS[0]][1] < lms[self.TIP_IDS[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # El resto de dedos – comparar y con el nodo 2 posiciones atrás
        for tip_id in self.TIP_IDS[1:]:
            if lms[tip_id][2] < lms[tip_id - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    def hands_detected(self) -> bool:
        """Devuelve True si se detectó al menos una mano."""
        return bool(self._results and self._results.multi_hand_landmarks)
