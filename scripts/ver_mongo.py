"""Ver datos actuales en MongoDB — ejecutar con .venv/Scripts/python.exe scripts/ver_mongo.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage import mongo_store

ok = mongo_store.connect()
if not ok:
    print("MongoDB no disponible")
    sys.exit(1)

s = mongo_store.stats()
print(f"\n=== MongoDB bmo_db ===")
print(f"Personas registradas:       {s.get('personas_total', 0)}")
print(f"Personas con embeddings:    {s.get('personas_con_embeddings', 0)}")
print(f"Mensajes de chat total:     {s.get('mensajes_total', 0)}")

print("\n--- Personas ---")
for doc in mongo_store._col("personas").find({}, {"nombre": 1, "visitas": 1, "ultima_vez": 1, "embeddings": 1}):
    emb_count = len(doc.get("embeddings", []))
    emb_dims  = len(doc["embeddings"][0]) if emb_count > 0 else 0
    print(f"  id={doc['_id']:4d}  nombre={doc['nombre']:<20}  visitas={doc.get('visitas',0)}  embeddings={emb_count}x{emb_dims}dims")

print("\n--- Últimos 10 mensajes de chat ---")
for doc in mongo_store._col("chat_history").find(
    {}, {"persona": 1, "role": 1, "content": 1, "ts": 1}
).sort("ts", -1).limit(10):
    ts = doc.get("ts", "?")
    print(f"  [{doc['persona']:<15}] {doc['role']:<10} {str(ts)[:19]}  {doc['content'][:55]}")

print()
