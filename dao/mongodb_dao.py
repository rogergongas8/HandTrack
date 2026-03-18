"""
dao/mongodb_dao.py
Data Access Object (DAO) con patrón Singleton para MongoDB Atlas.
Centraliza todas las operaciones de base de datos.
"""
import threading
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError

from config.settings import MONGODB_URI, DATABASE_NAME
from models.session import Session
from models.volume_event import VolumeEvent


class MongoDBDAO:
    """
    DAO Singleton para MongoDB Atlas.
    Garantiza una única instancia de conexión por proceso.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client: MongoClient | None = None
        self._db = None
        self._connected = False
        self._connect()

    # ------------------------------------------------------------------ #
    #  Conexión                                                            #
    # ------------------------------------------------------------------ #

    def _connect(self):
        """Establece la conexión con MongoDB Atlas."""
        if not MONGODB_URI:
            print("[DAO] MONGODB_URI no configurada. La BD estará desactivada.")
            return
        try:
            self._client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Verificar conectividad
            self._client.admin.command("ping")
            self._db = self._client[DATABASE_NAME]
            self._connected = True
            print(f"[DAO] Conectado a MongoDB: {DATABASE_NAME}")
        except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError, Exception) as e:
            print(f"[DAO] Error de conexión (BD desactivada): {type(e).__name__}: {e}")
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    #  Sesiones                                                            #
    # ------------------------------------------------------------------ #

    def save_session(self, session: Session):
        """
        Inserta una sesión en la colección 'sessions'.
        Devuelve el inserted_id o None si falla.
        """
        if not self._connected:
            return None
        try:
            result = self._db["sessions"].insert_one(session.to_dict())
            return result.inserted_id
        except Exception as e:
            print(f"[DAO] Error guardando sesión: {e}")
            return None

    def update_session(self, session_id, session: Session):
        """
        Actualiza end_time y duration_seconds de una sesión existente.
        """
        if not self._connected or session_id is None:
            return
        try:
            self._db["sessions"].update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "end_time": session.end_time,
                        "duration_seconds": session.duration_seconds,
                    }
                },
            )
        except Exception as e:
            print(f"[DAO] Error actualizando sesión: {e}")

    # ------------------------------------------------------------------ #
    #  Eventos de volumen                                                  #
    # ------------------------------------------------------------------ #

    def save_volume_event(self, event: VolumeEvent):
        """
        Inserta un evento de volumen en la colección 'volume_events'.
        """
        if not self._connected:
            return None
        try:
            result = self._db["volume_events"].insert_one(event.to_dict())
            return result.inserted_id
        except Exception as e:
            print(f"[DAO] Error guardando evento de volumen: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Cierre                                                              #
    # ------------------------------------------------------------------ #

    def close(self):
        """Cierra la conexión con MongoDB."""
        if self._client:
            self._client.close()
            self._connected = False
            print("[DAO] Conexión MongoDB cerrada.")
