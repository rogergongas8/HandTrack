"""
main.py  –  Controlador principal (MVC Controller)
============================================================
Coordina:
  · Cámara (OpenCV)           → captura de vídeo
  · HandDetector              → detección MediaPipe
  · VolumeController          → control de volumen Windows
  · MongoDBDAO                → persistencia (sesiones + eventos)

Gestos reconocidos
------------------
  Meñique BAJADO  → modo ACTIVO  (el gesto controla el volumen)
  Meñique ARRIBA  → modo PASIVO (sólo visualización, no cambia)

Controles de teclado
--------------------
  Q / ESC  → salir
"""

import sys
import time
import cv2
import numpy as np

from config.settings import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    FRAME_SKIP,
    MIN_HAND_DIST,
    MAX_HAND_DIST,
    MAX_HANDS,
    DETECTION_CONFIDENCE,
    TRACKING_CONFIDENCE,
)
from HandTrackingModule import HandDetector
from VolumeHandControl import VolumeController
from dao.mongodb_dao import MongoDBDAO
from models.session import Session
from models.volume_event import VolumeEvent


# ────────────────────────────────────────────────
#   Colores (BGR)
# ────────────────────────────────────────────────
COLOR_BAR_BG    = (50,  50,  50)
COLOR_BAR_FG    = (0,  215, 255)
COLOR_BAR_FRAME = (200, 200, 200)
COLOR_ACTIVE    = (0,  255,  80)
COLOR_PASSIVE   = (80,  80, 200)
COLOR_TEXT      = (255, 255, 255)
COLOR_DB_OK     = (0,  200,  80)
COLOR_DB_FAIL   = (80,  80,  80)


# ────────────────────────────────────────────────
#   Helpers de visualización (Vista en MVC)
# ────────────────────────────────────────────────

def draw_volume_bar(frame, vol_pct: int, active: bool):
    """Dibuja la barra lateral de volumen."""
    h, w = frame.shape[:2]
    bar_x, bar_y_top, bar_y_bot = w - 80, 150, h - 150
    bar_h = bar_y_bot - bar_y_top
    bar_w = 35

    # Fondo
    cv2.rectangle(frame, (bar_x, bar_y_top), (bar_x + bar_w, bar_y_bot),
                  COLOR_BAR_BG, cv2.FILLED)

    # Relleno proporcional al volumen
    fill_h = int(bar_h * vol_pct / 100)
    fill_y = bar_y_bot - fill_h
    bar_color = COLOR_ACTIVE if active else COLOR_PASSIVE
    cv2.rectangle(frame, (bar_x, fill_y), (bar_x + bar_w, bar_y_bot),
                  bar_color, cv2.FILLED)

    # Marco
    cv2.rectangle(frame, (bar_x, bar_y_top), (bar_x + bar_w, bar_y_bot),
                  COLOR_BAR_FRAME, 2)

    # Porcentaje
    cv2.putText(frame, f"{vol_pct}%",
                (bar_x - 5, bar_y_bot + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

    # Etiqueta VOL
    cv2.putText(frame, "VOL",
                (bar_x + 2, bar_y_top - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)


def draw_hud(frame, active: bool, fps: float, db_ok: bool, session_start: float):
    """Dibuja el HUD superior con estado, FPS y conexión DB."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 45), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Estado del gesto
    estado = "ACTIVO  [menique bajo]" if active else "PASIVO  [levanta menique]"
    color_estado = COLOR_ACTIVE if active else COLOR_PASSIVE
    cv2.putText(frame, estado, (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_estado, 2)

    # FPS
    cv2.putText(frame, f"FPS: {fps:.0f}", (w - 200, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)

    # DB status
    db_text  = "DB: OK" if db_ok else "DB: --"
    db_color = COLOR_DB_OK if db_ok else COLOR_DB_FAIL
    cv2.putText(frame, db_text, (w - 350, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, db_color, 2)

    # Duración de sesión
    elapsed = int(time.time() - session_start)
    mins, secs = divmod(elapsed, 60)
    cv2.putText(frame, f"Sesion: {mins:02d}:{secs:02d}", (w // 2 - 70, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)


# ────────────────────────────────────────────────
#   Controlador principal
# ────────────────────────────────────────────────

def main():
    # ── Inicializar componentes ─────────────────
    print("[MAIN] Iniciando Hand Volume Control...")

    detector = HandDetector(
        max_hands=MAX_HANDS,
        detection_confidence=DETECTION_CONFIDENCE,
        tracking_confidence=TRACKING_CONFIDENCE,
    )
    vol_ctrl = VolumeController(min_dist=MIN_HAND_DIST, max_dist=MAX_HAND_DIST)
    dao = MongoDBDAO()

    # ── Sesión en MongoDB ───────────────────────
    session = Session()
    session_id = dao.save_session(session)
    print(f"[MAIN] Sesión iniciada | ID: {session_id}")

    # ── Cámara ──────────────────────────────────
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] No se pudo abrir la cámara.")
        sys.exit(1)

    # ── Estado de la aplicación (Modelo en MVC) ─
    prev_vol    = vol_ctrl.current_volume
    frame_count = 0
    fps         = 0.0
    prev_time   = time.time()
    session_start = time.time()

    # Umbral de cambio mínimo para registrar evento (evita spam a BD)
    VOL_CHANGE_THRESHOLD = 0.02   # 2%

    print("[MAIN] Presiona Q o ESC para salir.")

    # ── Bucle principal ─────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] No se pudo leer frame de la cámara.")
            break

        frame_count += 1

        # FPS
        curr_time = time.time()
        if curr_time - prev_time >= 1.0:
            fps = frame_count / (curr_time - prev_time)
            frame_count = 0
            prev_time = curr_time

        # ── Detección de manos (cada FRAME_SKIP frames) ──
        if frame_count % FRAME_SKIP == 0:
            frame = detector.find_hands(frame, draw=True)

        # Bounding box (visual opcional)
        bbox = detector.get_bounding_box(frame)
        if bbox:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 200, 0), 1)

        # ── Distancia pulgar–índice ──────────────
        distance, lms, midpoint = detector.get_distance(
            frame,
            HandDetector.THUMB_TIP,
            HandDetector.INDEX_TIP,
            draw=True,
        )

        # ── Estado de dedos → gesto meñique ─────
        fingers = detector.fingers_up(frame)
        # fingers[4] == 0 → meñique bajado → MODO ACTIVO
        pinky_down = (len(fingers) == 5 and fingers[4] == 0)

        # Volumen actual
        current_vol = vol_ctrl.current_volume

        if detector.hands_detected() and distance > 0:
            if pinky_down:
                # Aplicar cambio de volumen
                new_vol = vol_ctrl.apply_from_distance(distance)
                current_vol = new_vol

                # Registrar evento si el cambio es significativo
                if abs(new_vol - prev_vol) >= VOL_CHANGE_THRESHOLD:
                    event = VolumeEvent(
                        session_id=session_id,
                        previous_volume=prev_vol,
                        new_volume=new_vol,
                        finger_distance=distance,
                    )
                    dao.save_volume_event(event)
                    prev_vol = new_vol

            # Mostrar distancia en pantalla
            if midpoint:
                cv2.putText(frame, f"{int(distance)}px",
                            (midpoint[0] - 20, midpoint[1] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # ── Vista (HUD + barra de volumen) ───────
        vol_pct = int(current_vol * 100)
        draw_volume_bar(frame, vol_pct, active=pinky_down)
        draw_hud(frame, active=pinky_down, fps=fps,
                 db_ok=dao.is_connected, session_start=session_start)

        # Instrucción en pantalla
        cv2.putText(frame, "Baja el menique para controlar el volumen",
                    (15, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

        cv2.imshow("Hand Volume Control - M6", frame)

        # ── Salida ───────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):   # Q o ESC
            break

    # ── Limpieza ────────────────────────────────
    print("[MAIN] Cerrando aplicación...")
    cap.release()
    cv2.destroyAllWindows()

    # Cerrar sesión en MongoDB
    session.close()
    dao.update_session(session_id, session)
    print(f"[MAIN] Sesión cerrada | Duración: {session.duration_seconds:.1f}s")

    dao.close()
    print("[MAIN] ¡Hasta luego!")


if __name__ == "__main__":
    main()
