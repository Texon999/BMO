"""
BMO - Main loop
Integra: Visión (OpenCV) + Voz (Whisper + Piper) + Cerebro (Ollama llama3.2:1b)

Controles:
  R  → Registrar nuevo visitante
  V  → Activar escucha de voz (BMO te responde)
  Q  → Salir
"""
import cv2
import threading
from pathlib import Path

from src.vision.vision import VisionBMO
from src.voice.voice import VozBMO
from src.brain.brain import generar_respuesta


# ── Estado global ─────────────────────────────────────────────────────────────

estado       = "LISTO (r=registrar, v=hablar, q=salir)"
persona_actual: str | None = None   # nombre de quien está frente a la cámara
hablando     = False                # evita solapamiento de respuestas


def _responder_en_hilo(voz: VozBMO, texto: str, nombre: str | None):
    """Genera respuesta del LLM y la habla en un hilo separado."""
    global hablando, estado
    hablando = True
    estado = "PENSANDO..."
    respuesta = generar_respuesta(texto, nombre)
    estado = "HABLANDO..."
    voz.hablar(respuesta)
    estado = "LISTO (r=registrar, v=hablar, q=salir)"
    hablando = False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global estado, persona_actual, hablando

    Path("data").mkdir(exist_ok=True)

    # Inicializar módulos
    bmo_vision = VisionBMO(camera_index=0)
    bmo_voz    = VozBMO()

    print("\n✓ BMO listo. Presiona V para hablar, R para registrar, Q para salir.\n")

    while True:
        ret, frame = bmo_vision.cap.read()
        if not ret:
            break

        frame_final, detecciones = bmo_vision.procesar_rostro(frame)

        # Actualizar quién está frente a la cámara
        reconocidos = [d["nombre"] for d in detecciones if d["id"] is not None]
        persona_actual = reconocidos[0] if reconocidos else None

        # HUD
        _dibujar_hud(frame_final, estado, persona_actual)
        cv2.imshow("BMO", frame_final)

        key = cv2.waitKey(1) & 0xFF

        # ── V: Escuchar y responder ──────────────────────────────────────────
        if key == ord("v") and not hablando:
            estado = "ESCUCHANDO..."
            texto = bmo_voz.escuchar()
            if texto:
                t = threading.Thread(
                    target=_responder_en_hilo,
                    args=(bmo_voz, texto, persona_actual),
                    daemon=True,
                )
                t.start()
            else:
                estado = "No te escuché. Intenta de nuevo."

        # ── R: Registrar nuevo rostro ────────────────────────────────────────
        elif key == ord("r"):
            _registrar_visitante(bmo_vision, bmo_voz)

        # ── Q: Salir ─────────────────────────────────────────────────────────
        elif key == ord("q"):
            break

    bmo_vision.liberar()
    cv2.destroyAllWindows()
    print("✓ BMO desconectado")


# ── Registro de visitante ─────────────────────────────────────────────────────

def _registrar_visitante(bmo: VisionBMO, voz: VozBMO):
    global estado

    siguiente_id = bmo.siguiente_id()
    print(f"\n[!] REGISTRO #{siguiente_id}")
    nombre = input("¿Nombre del visitante?: ").strip().lower()
    if not nombre:
        return

    estado = f"CAPTURANDO {nombre}..."
    capturas = []
    count = 0

    print("BMO: ¡Mira la cámara!")
    while count < 30:
        ret, f = bmo.cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = bmo.face_cascade.detectMultiScale(gray, 1.1, 8, minSize=(60, 60))

        for (x, y, w, h) in faces:
            roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
            capturas.append(roi)
            count += 1
            cv2.rectangle(f, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.putText(f, f"Capturando: {count}/30", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("BMO - Registrando", f)
        cv2.waitKey(50)

    cv2.destroyWindow("BMO - Registrando")

    if capturas:
        bmo.aprender_rostro(siguiente_id, nombre, capturas)
        voz.hablar(f"¡Hola {nombre}! Ya te conozco.")
        estado = "LISTO (r=registrar, v=hablar, q=salir)"
    else:
        print("✗ No se detectó ningún rostro")
        estado = "LISTO (r=registrar, v=hablar, q=salir)"


# ── HUD ───────────────────────────────────────────────────────────────────────

def _dibujar_hud(frame, estado: str, persona: str | None):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 40), (0, 0, 0), -1)
    cv2.putText(frame, estado, (10, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    if persona:
        cv2.putText(frame, f"Hola, {persona}!", (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


if __name__ == "__main__":
    main()
