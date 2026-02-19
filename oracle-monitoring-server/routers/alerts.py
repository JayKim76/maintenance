from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import random
import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

class Alert(BaseModel):
    id: int
    time: str
    severity: str
    message: str
    source: str

@router.get("/history", response_model=List[Alert])
async def get_alerts():
    severities = ["CRITICAL", "WARNING", "INFO"]
    sources = ["Database", "Listener", "OS", "Network"]
    msgs = [
        "Tablespace USERS usage > 90%",
        "High CPU Load on Instance ORCL1 (95%)",
        "Blocking Session Detected (SID 142 blocked by 12)",
        "Listener TNS-12541: No listener",
        "Archivelog destination is 85% full",
        "Swap usage increased to 15%",
        "Long running query detected (> 300s)"
    ]
    
    alerts = []
    now = datetime.datetime.now()
    for i in range(25):
        t = now - datetime.timedelta(minutes=random.randint(0, 1440)) # last 24h
        sev = random.choices(severities, weights=[1, 2, 5])[0]
        alerts.append({
            "id": i,
            "time": t.strftime("%Y-%m-%d %H:%M:%S"),
            "severity": sev,
            "message": random.choice(msgs),
            "source": random.choice(sources)
        })
    
    # Sort by time desc
    alerts.sort(key=lambda x: x['time'], reverse=True)
    return alerts
