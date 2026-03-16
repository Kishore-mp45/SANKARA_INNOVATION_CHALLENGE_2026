import json
from database import SessionLocal
from models.patient import Patient
from datetime import datetime

db = SessionLocal()
patients = db.query(Patient).filter(
    Patient.action_history != None,
    Patient.action_history != "[]",
).limit(5).all()

print(f"Found {len(patients)} patients with action_history")

now = datetime.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

for p in patients:
    history = json.loads(p.action_history) if p.action_history else []
    print(f"\nPatient: {p.name} (tracking_id={p.tracking_id}), entries={len(history)}")
    for e in history[:8]:
        print(f"  zone={e.get('zone')}, action={e.get('action')}, ts={e.get('timestamp')}")

db.close()
