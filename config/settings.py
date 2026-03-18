"""
config/settings.py
Carga la configuración desde el archivo .env usando python-dotenv.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta absoluta al archivo .env (subiendo de config/ a la raíz)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MONGODB_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "hand_tracking_db")

# Configuración de cámara
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FRAME_SKIP = 2          # Procesar 1 de cada N frames (rendimiento)

# Configuración de detección de manos
MAX_HANDS = 1
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.7

# Rango de distancia dedos (en píxeles) → volumen 0%-100%
MIN_HAND_DIST = 30      # distancia mínima → volumen 0%
MAX_HAND_DIST = 220     # distancia máxima → volumen 100%
