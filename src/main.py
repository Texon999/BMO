import cv2
import time
from pathlib import Path
from src.vision.vision import VisionBMO

def main():
    Path("data/history").mkdir(parents=True, exist_ok=True)
    
    try:
        bmo = VisionBMO(camera_index=0)
        estado = "ESCUCHANDO (r/q)"
        
        while True:
            ret, frame = bmo.cap.read()
            if not ret: break

            frame_final, detecciones = bmo.procesar_rostro(frame)
            
            # Barra de estado visual
            cv2.rectangle(frame_final, (0,0), (300, 35), (0,0,0), -1)
            cv2.putText(frame_final, f"MODO: {estado}", (10, 23), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow('BMO - Vision System', frame_final)

            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('r'):
                estado = "ESCRIBE NOMBRE EN CONSOLA"
                cv2.imshow('BMO - Vision System', frame_final)
                cv2.waitKey(10)
                
                # Calculamos el siguiente ID disponible
                ids_existentes = [int(i) for i in bmo.nombres_dict.keys()]
                siguiente_id = max(ids_existentes + [-1]) + 1
                
                print(f"\n[!] REGISTRO DE VISITANTE #{siguiente_id}")
                nombre = input("¿Cuál es el nombre del visitante?: ").strip().lower()
                
                if nombre:
                    estado = f"CAPTURANDO ID {siguiente_id}..."
                    capturas = []
                    count = 0
                    
                    print("BMO: ¡Vuelve a mirar la cámara!")
                    while count < 30:
                        ret, f = bmo.cap.read()
                        if not ret: break
                        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                        faces = bmo.face_cascade.detectMultiScale(gray, 1.1, 8)
                        
                        for (x, y, w, h) in faces:
                            roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                            capturas.append(roi)
                            count += 1
                            cv2.rectangle(f, (x,y), (x+w, y+h), (0, 255, 0), 2)
                        
                        cv2.putText(f, f"Capturando ID {siguiente_id}: {count}/30", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.imshow('BMO - Grabando...', f)
                        cv2.waitKey(50)

                    if capturas:
                        bmo.aprender_rostro(siguiente_id, nombre, capturas)
                        
                        # Historial único por ID y Nombre
                        path_hist = Path(f"data/history/{siguiente_id}_{nombre}.txt")
                        if not path_hist.exists():
                            path_hist.write_text(f"ID: {siguiente_id} | Nombre: {nombre}\n---\n")
                        
                        cv2.destroyWindow('BMO - Grabando...')
                        print(f"✓ Guardado como ID {siguiente_id}. ¡HAZ CLIC EN LA CAMARA!")
                        estado = "¡CLIC EN LA VENTANA!"
                    else:
                        estado = "ESCUCHANDO (r/q)"
                else:
                    estado = "ESCUCHANDO (r/q)"

            if key == ord('q'): break
            
            # Reset de mensaje de clic
            if estado == "¡CLIC EN LA VENTANA!" and key != 255:
                estado = "ESCUCHANDO (r/q)"

    except Exception as e:
        print(f"✗ Error crítico: {e}")
    finally:
        if 'bmo' in locals(): bmo.cap.release()
        cv2.destroyAllWindows()
        print("✓ BMO desconectado")

if __name__ == "__main__":
    main()