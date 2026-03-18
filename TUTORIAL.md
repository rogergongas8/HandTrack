# 🖐️ Hand Volume Control — Tutorial

> **Módulo M6 – Acceso a Datos**  
> Controla el volumen de tu PC con gestos de mano usando MediaPipe, OpenCV, pycaw y MongoDB Atlas.

---

## 📋 Requisitos previos

| Herramienta | Versión mínima |
|-------------|---------------|
| Python | 3.10+ |
| Webcam | Cualquier webcam USB/integrada |
| SO | Windows 10/11 |
| Cuenta MongoDB | Atlas (gratuita) |

---

## 🚀 Instalación

```bash
# 1. Clona el repositorio
git clone <tu-repo>
cd HandTracking

# 2. Crea un entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt
```

---

## ☁️ Configurar MongoDB Atlas

1. Ve a [https://cloud.mongodb.com](https://cloud.mongodb.com) y crea una cuenta gratuita.
2. Crea un **cluster** (elige la opción gratuita M0).
3. En **Database Access** → añade un usuario con contraseña.
4. En **Network Access** → añade tu IP (o `0.0.0.0/0` para cualquier IP).
5. En tu cluster → **Connect** → **Drivers** → copia la cadena de conexión.

---

## ⚙️ Configurar variables de entorno

Edita el archivo `.env` en la raíz del proyecto:

```env
MONGODB_URI=mongodb+srv://TU_USUARIO:TU_PASSWORD@TU_CLUSTER.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=hand_tracking_db
```

> ⚠️ **Nunca subas el `.env` a GitHub.** Ya está incluido en `.gitignore`.

---

## ▶️ Ejecutar la aplicación

```bash
python main.py
```

---

## 🖐️ Gestos disponibles

| Gesto | Efecto |
|-------|--------|
| **Meñique bajado** + separar pulgar e índice | Sube el volumen |
| **Meñique bajado** + juntar pulgar e índice | Baja el volumen |
| **Meñique arriba** | Modo pasivo — el volumen no cambia |
| `Q` o `ESC` | Cierra la aplicación |

---

## 🏗️ Arquitectura del proyecto (MVC + DAO)

```
HandTracking/
├── main.py                  # Controller  — bucle principal, coordina todo
├── HandTrackingModule.py    # Model       — detección MediaPipe
├── VolumeHandControl.py     # Model       — mapeo distancia→volumen (pycaw)
├── config/
│   └── settings.py          # Configuración global (.env)
├── models/
│   ├── session.py           # Modelo de datos: Sesión
│   └── volume_event.py      # Modelo de datos: Evento de volumen
├── dao/
│   └── mongodb_dao.py       # DAO Singleton — acceso a MongoDB Atlas
├── .env                     # Variables de entorno (NO subir a Git)
├── requirements.txt         # Dependencias Python
└── TUTORIAL.md              # Este archivo
```

### Patrón MVC
- **Model** → `HandTrackingModule`, `VolumeHandControl`, clases en `models/`
- **View** → Funciones `draw_volume_bar()` y `draw_hud()` en `main.py` (OpenCV)
- **Controller** → Función `main()` en `main.py`

### Patrón DAO
- `MongoDBDAO` centraliza toda la lógica de acceso a MongoDB.
- Implementa el patrón **Singleton** para compartir la misma conexión.

---

## 🗄️ Estructura de datos en MongoDB

### Colección `sessions`
```json
{
  "_id": ObjectId("..."),
  "start_time": ISODate("2025-01-01T10:00:00Z"),
  "end_time":   ISODate("2025-01-01T10:05:30Z"),
  "duration_seconds": 330.0
}
```

### Colección `volume_events`
```json
{
  "_id": ObjectId("..."),
  "session_id": ObjectId("..."),
  "timestamp": ISODate("2025-01-01T10:02:15Z"),
  "previous_volume": 0.45,
  "new_volume": 0.62,
  "finger_distance": 148.3
}
```

---

## 🔧 Ajustes de rendimiento

| Parámetro | Dónde | Descripción |
|-----------|-------|-------------|
| `FRAME_SKIP` | `config/settings.py` | Procesa 1 de cada N frames |
| `FRAME_WIDTH/HEIGHT` | `config/settings.py` | Resolución de captura |
| `MIN_HAND_DIST` | `config/settings.py` | Distancia mínima (volumen 0%) |
| `MAX_HAND_DIST` | `config/settings.py` | Distancia máxima (volumen 100%) |

---

## 💡 Consejos de uso

- Sitúa la mano a **40–60 cm** de la cámara para mejor detección.
- Asegúrate de tener **buena iluminación frontal**.
- Si la detección falla, ajusta `DETECTION_CONFIDENCE` en `settings.py`.

---

## 📦 Dependencias

```
opencv-python   — Captura y visualización de vídeo
mediapipe       — Detección de landmarks de mano
pycaw           — Control de volumen Windows (API de audio)
comtypes        — Requerido por pycaw
pymongo         — Driver oficial de MongoDB para Python
python-dotenv   — Carga variables de entorno desde .env
numpy           — Interpolación numérica
```
