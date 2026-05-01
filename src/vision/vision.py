"""
Módulo de visión de BMO — Detección y reconocimiento facial con ONNX.

Usa dos algoritmos en cadena:
  1. Haar Cascade: detecta la posición de rostros en el frame (rápido, CPU).
  2. FaceEmbedder (ONNX): extrae embeddings de 512 dimensiones y compara
     por similitud coseno contra los embeddings registrados en memory.json.

Flujo por frame:
  - Haar Cascade detecta rectángulos de rostros.
  - Por cada rostro, FaceEmbedder extrae un embedding del ROI BGR.
  - Se compara contra self.embeddings_dict con best_match (threshold 0.55).
  - Si similitud >= threshold → reconocido; si no → "Desconocido".

Modo degradado:
  Si data/face_model.onnx no existe, VisionBMO arranca sin FaceEmbedder.
  En ese modo detecta caras (Haar) pero no reconoce a nadie.
  Ejecuta scripts/download_face_model.py para habilitar el reconocimiento.

Registro de nuevas personas:
  - Se llama a aprender_rostro() con una lista de imágenes BGR del rostro.
  - Se extraen embeddings, se promedian y normalizan L2.
  - El embedding promedio se guarda en memory.json via register.py.
  - self.embeddings_dict se actualiza en memoria sin releer el archivo.
"""
import logging
import cv2
import numpy as np
from pathlib import Path

from src.vision.embedder import FaceEmbedder
from src.memory.register import (
    cargar_personas,
    guardar_persona,
    nombres_a_ids,
    guardar_embeddings_persona,
    cargar_embeddings_todos,
)

log = logging.getLogger("BMO")

_MODEL_PATH = Path("data/face_model.onnx")


class VisionBMO:
    def __init__(self, camera_index: int = 0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara {camera_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        Path("data").mkdir(exist_ok=True)

        # FaceEmbedder es opcional — si el modelo no existe, modo degradado
        if _MODEL_PATH.exists():
            self.embedder: FaceEmbedder | None = FaceEmbedder(_MODEL_PATH)
            self.embeddings_dict = cargar_embeddings_todos()
            print("✓ Visión BMO lista (reconocimiento facial activo)")
        else:
            self.embedder = None
            self.embeddings_dict = {}
            log.warning(
                "[VISION] Modelo ONNX no encontrado en %s. "
                "BMO detectará caras pero NO reconocerá personas. "
                "Ejecuta: python scripts/download_face_model.py",
                _MODEL_PATH,
            )
            print("⚠ Visión BMO lista (modo degradado — sin reconocimiento facial)")

    # ── Procesamiento de frame ────────────────────────────────────────────────

    def procesar_rostro(self, frame: np.ndarray) -> tuple[np.ndarray, list]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))

        resultados = []
        for (x, y, w, h) in faces:
            roi_bgr = frame[y:y+h, x:x+w]

            # Sin embedder: detectar cara pero no reconocer
            if self.embedder is None:
                resultados.append({
                    "id":        None,
                    "nombre":    "Desconocido",
                    "cara_img":  roi_bgr,
                    "similitud": -1.0,
                })
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Desconocido", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                continue

            embedding = self.embedder.extract(roi_bgr)
            if embedding is None:
                continue

            nombre, similitud = self.embedder.best_match(embedding, self.embeddings_dict)
            reconocido = nombre is not None
            id_final = nombre if reconocido else None
            color = (0, 255, 0) if reconocido else (0, 0, 255)

            resultados.append({
                "id":        id_final,
                "nombre":    nombre or "Desconocido",
                "cara_img":  roi_bgr,
                "similitud": similitud,
            })

            label = f"{nombre or 'Desconocido'} ({similitud:.2f})"
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        return frame, resultados

    # ── Aprendizaje ───────────────────────────────────────────────────────────

    def aprender_rostro(self, id_nuevo: int, nombre: str, lista_caras: list):
        """Extrae embeddings, los promedia y guarda en memory.json."""
        if self.embedder is None:
            log.warning(
                "[VISION] No se puede registrar '%s': modelo ONNX no disponible. "
                "Ejecuta scripts/download_face_model.py primero.",
                nombre,
            )
            print(f"✗ No se puede registrar '{nombre}': falta el modelo facial ONNX.")
            return

        embeddings_validos = []
        for cara in lista_caras:
            emb = self.embedder.extract(cara)
            if emb is not None:
                embeddings_validos.append(emb)

        if not embeddings_validos:
            print(f"✗ No se obtuvieron embeddings válidos para '{nombre}'")
            return

        # Promediar y renormalizar L2
        embedding_promedio = np.mean(embeddings_validos, axis=0)
        norm = float(np.linalg.norm(embedding_promedio))
        embedding_promedio = embedding_promedio / max(norm, 1e-6)
        embedding_promedio = embedding_promedio.astype(np.float32)

        # Persistir metadatos y embeddings
        guardar_persona(id_nuevo, nombre)
        guardar_embeddings_persona(nombre, [embedding_promedio])

        # Actualizar caché en memoria
        self.embeddings_dict[nombre] = [embedding_promedio]

        print(f"✓ Rostro de '{nombre}' (ID {id_nuevo}) guardado")

    # ── Utilidades ────────────────────────────────────────────────────────────

    def siguiente_id(self) -> int:
        ids_existentes = nombres_a_ids()
        ids = [int(k) for k in ids_existentes.keys() if k != "_anonimo"]
        return max(ids + [-1]) + 1

    def liberar(self):
        self.cap.release()
