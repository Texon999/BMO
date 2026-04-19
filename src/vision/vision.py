"""
Módulo de visión de BMO.
Reconocimiento facial con LBPH + Haar Cascade.
Usa memoria unificada (memory.json) en lugar de names.json + persons.json.
"""
import cv2
import numpy as np
from pathlib import Path
from src.memory.register import cargar_personas, guardar_persona, nombres_a_ids


CONFIDENCE_THRESHOLD = 55   # menor = más estricto
FACE_SIZE = (200, 200)


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

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()

        self.model_file = Path("data/trainer.yml")
        Path("data").mkdir(exist_ok=True)

        # Diccionario {str(id): nombre} cargado desde memoria unificada
        self.nombres_dict = nombres_a_ids()

        if self.model_file.exists() and self.nombres_dict:
            self.recognizer.read(str(self.model_file))

        print("✓ Visión BMO lista")

    # ── Procesamiento de frame ────────────────────────────────────────────────

    def procesar_rostro(self, frame: np.ndarray) -> tuple[np.ndarray, list]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))

        resultados = []
        for (x, y, w, h) in faces:
            roi = cv2.resize(gray[y:y+h, x:x+w], FACE_SIZE)

            id_usuario, confianza = -1, 999.0
            if self.model_file.exists() and self.nombres_dict:
                id_usuario, confianza = self.recognizer.predict(roi)

            reconocido = confianza < CONFIDENCE_THRESHOLD and str(id_usuario) in self.nombres_dict
            nombre  = self.nombres_dict[str(id_usuario)] if reconocido else "Desconocido"
            color   = (0, 255, 0) if reconocido else (0, 0, 255)
            id_final = id_usuario if reconocido else None

            resultados.append({
                "id":        id_final,
                "nombre":    nombre,
                "cara_img":  roi,
                "confianza": confianza,
            })

            label = f"{nombre} ({int(confianza)})"
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        return frame, resultados

    # ── Aprendizaje ───────────────────────────────────────────────────────────

    def aprender_rostro(self, id_nuevo: int, nombre: str, lista_caras: list):
        """Entrena el modelo con las capturas y guarda en memoria unificada."""
        ids = np.array([id_nuevo] * len(lista_caras))

        if self.model_file.exists() and self.nombres_dict:
            self.recognizer.update(lista_caras, ids)
        else:
            self.recognizer.train(lista_caras, ids)

        self.nombres_dict[str(id_nuevo)] = nombre
        self.recognizer.write(str(self.model_file))

        # Persistir en memoria unificada
        guardar_persona(id_nuevo, nombre)
        print(f"✓ Rostro de '{nombre}' (ID {id_nuevo}) guardado")

    # ── Utilidades ────────────────────────────────────────────────────────────

    def siguiente_id(self) -> int:
        ids = [int(k) for k in self.nombres_dict.keys()]
        return max(ids + [-1]) + 1

    def liberar(self):
        self.cap.release()
