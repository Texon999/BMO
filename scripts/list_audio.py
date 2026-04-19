import sounddevice as sd

devices = sd.query_devices()
default_in, default_out = sd.default.device

print("=== DISPOSITIVOS DE AUDIO ===\n")
for i, d in enumerate(devices):
    marker = ""
    if i == default_in:  marker += " [DEFAULT IN]"
    if i == default_out: marker += " [DEFAULT OUT]"
    if d["max_output_channels"] > 0:
        print(f"  [{i}] OUT | {d['name']}{marker}")

print(f"\nDefault output: {default_out} → {devices[default_out]['name']}")
