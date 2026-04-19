import cv2
import numpy as np
import json
import datetime
from pathlib import Path

class VisionBMO:
    def __init__(self, camera_index=0):
        # Configuración de hardware
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Rutas de datos
        self.db_path = Path("data")
        self.db_path.mkdir(exist_ok=True)
        self.model_file = self.db_path / "trainer.yml"
        self.names_file = self.db_path / "names.json"
        self.persons_file = self.db_path / "persons.json"
        
        # Cargamos nombres como DICCIONARIO { "id": "nombre" }
        self.nombres_dict = self._cargar_nombres()
        
        if self.model_file.exists():
            self.recognizer.read(str(self.model_file))
            
        print("✓ Visión BMO: Sistema de Feria con ID Único Listo")

    def _cargar_nombres(self):
        if self.names_file.exists():
            with open(self.names_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def procesar_rostro(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray) # Normaliza luz
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 8)
        
        resultados = []
        for (x, y, w, h) in faces:
            roi_gray = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
            
            id_usuario, confianza = -1, 999
            if self.model_file.exists() and self.nombres_dict:
                id_usuario, confianza = self.recognizer.predict(roi_gray)
            
            # Umbral estricto para la feria
            if confianza < 55 and str(id_usuario) in self.nombres_dict:
                nombre = self.nombres_dict[str(id_usuario)]
                color = (0, 255, 0)
                # Guardamos el ID real para el historial
                id_final = id_usuario
            else:
                nombre = "Desconocido"
                color = (0, 0, 255)
                id_final = None
            
            resultados.append({
                "id": id_final,
                "nombre": nombre, 
                "cara_img": roi_gray,
                "confianza": confianza
            })
            
            # Dibujamos ID y Nombre en pantalla
            label = f"ID:{id_usuario} {nombre} ({int(confianza)})"
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        return frame, resultados

    def aprender_rostro(self, id_nuevo, nombre, lista_caras):
        """Entrena usando el ID como etiqueta numérica"""
        ids_entrenamiento = np.array([id_nuevo] * len(lista_caras))
        
        if self.model_file.exists():
            self.recognizer.update(lista_caras, ids_entrenamiento)
        else:
            self.recognizer.train(lista_caras, ids_entrenamiento)
            
        # Guardamos en el diccionario usando el ID como llave
        self.nombres_dict[str(id_nuevo)] = nombre
        
        self.recognizer.write(str(self.model_file))
        with open(self.names_file, 'w', encoding='utf-8') as f:
            json.dump(self.nombres_dict, f, indent=4)
            
        self.registrar_actividad(id_nuevo, nombre)

    def registrar_actividad(self, id_persona, nombre):
        memoria = {}
        if self.persons_file.exists():
            with open(self.persons_file, 'r', encoding='utf-8') as f:
                memoria = json.load(f)
        
        # La llave ahora es el ID para evitar choques de nombres
        memoria[str(id_persona)] = {
            "nombre": nombre,
            "ultima_vez": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.persons_file, 'w', encoding='utf-8') as f:
            json.dump(memoria, f, indent=4)