"""
FaceEmbedder — extracción de embeddings faciales con ONNX Runtime.

Carga un modelo ONNX (MobileFaceNet/ArcFace) y produce vectores float32
de 512 dimensiones normalizados L2 a partir de imágenes BGR de rostros.
La identidad se decide por similitud coseno contra embeddings registrados.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

log = logging.getLogger("BMO")


class FaceEmbedder:
    """Extrae embeddings de rostros usando un modelo ONNX y compara identidades."""

    def __init__(self, model_path: str | Path) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo ONNX no encontrado en: {model_path}. "
                "Ejecuta scripts/download_face_model.py para descargarlo."
            )
        self._session = ort.InferenceSession(str(model_path))
        self._input_name = self._session.get_inputs()[0].name

    def extract(self, face_bgr: np.ndarray) -> np.ndarray | None:
        """
        Recibe ROI BGR (cualquier tamaño), devuelve embedding L2-normalizado
        de shape (512,) dtype float32, o None si la entrada es inválida.
        """
        img = face_bgr.copy()

        # Validar shape: debe ser 2D o 3D con todas las dimensiones > 0
        if img.ndim < 2 or img.ndim > 3 or any(d == 0 for d in img.shape):
            log.warning("FaceEmbedder.extract: shape inválido %s, descartando.", img.shape)
            return None

        try:
            # BGR → RGB
            if img.ndim == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                # imagen en escala de grises → convertir a RGB
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

            # Resize a 112×112
            img = cv2.resize(img, (112, 112))

            # Normalizar a [-1, 1]: /255 → (x - 0.5) / 0.5
            img = img.astype(np.float32) / 255.0
            img = (img - 0.5) / 0.5

            # HWC → CHW → batch dim (1, 3, 112, 112)
            blob = img.transpose(2, 0, 1)[np.newaxis, :]

            # Inferencia ONNX
            raw = self._session.run(None, {self._input_name: blob})[0][0]  # shape (512,)

            # Normalización L2
            norm = float(np.linalg.norm(raw))
            embedding = raw / max(norm, 1e-6)

            return embedding.astype(np.float32)

        except Exception as exc:  # noqa: BLE001
            log.warning("FaceEmbedder.extract: error durante inferencia — %s", exc)
            return None

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Similitud coseno entre dos vectores unitarios. Rango [-1, 1]."""
        return float(np.dot(a, b))

    def best_match(
        self,
        query: np.ndarray,
        candidates: dict[str, list[np.ndarray]],
        threshold: float = 0.55,
    ) -> tuple[str | None, float]:
        """
        Compara query contra todos los embeddings de candidates.

        Devuelve (nombre, similitud_max) si la mejor similitud >= threshold,
        o (None, similitud_max) en caso contrario.
        Si candidates está vacío, devuelve (None, -1.0).
        """
        if not candidates:
            return (None, -1.0)

        best_name: str | None = None
        best_sim: float = -1.0

        for nombre, embeddings in candidates.items():
            for emb in embeddings:
                sim = self.cosine_similarity(query, emb)
                if sim > best_sim:
                    best_sim = sim
                    best_name = nombre

        if best_sim >= threshold:
            return (best_name, best_sim)
        return (None, best_sim)
