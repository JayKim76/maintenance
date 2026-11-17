from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import datetime
import core.database as db_module
from core.database import _run_query

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

class Alert(BaseModel):
    id: int
    time: str
    severity: str
    message: str
    source: str

@router.get("/history", response_model=List[Alert])
async def get_alerts():
    if db_module.MOCK_MODE:
        return []

    alerts = []
    alert_id = 1
    
    def try_query(q):
        try:
            res = _run_query(q)
            return res if res else []
        except Exception as e:
            print("Alert Query Error:", e)
            return []

    # 1. TNS Errors (Recent)
    tns_q = """
        select * from (
            select to_char(originating_timestamp, 'YYYY-MM-DD HH24:MI:SS') as time,
                   message_text as msg
            from v$diag_alert_ext
            where message_text like '%TNS-%'
            order by record_id desc
        ) where rownum <= 20
    """
    for r in try_query(tns_q):
        alerts.append({"id": alert_id, "time": str(r[0]), "severity": "WARNING", "message": str(r[1]), "source": "Listener"})
        alert_id += 1

    # 2. ORA- Errors (Recent)
    ora_q = """
        select * from (
            select to_char(originating_timestamp, 'YYYY-MM-DD HH24:MI:SS') as time,
                   message_text as msg
            from v$diag_alert_ext
            where message_text like '%ORA-%'
            order by record_id desc
        ) where rownum <= 20
    """
    for r in try_query(ora_q):
        sev = "CRITICAL" if "ORA-00600" in str(r[1]) or "ORA-07445" in str(r[1]) else "WARNING"
        alerts.append({"id": alert_id, "time": str(r[0]), "severity": sev, "message": str(r[1]), "source": "Database"})
        alert_id += 1

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Tablespace (MAX_USED_PCT > 90%)
    ts_q = """
        SELECT a.tablespace_name,
               round(((a.total_mb - nvl(b.free_mb,0)) / NULLIF(a.max_mb,0))*100, 1) AS max_used_pct,
               round(((a.total_mb - nvl(b.free_mb,0)) / NULLIF(a.total_mb,0))*100, 1) AS current_used_pct
        FROM (
            SELECT tablespace_name,
                   sum(bytes)/1024/1024 total_mb,
                   sum(case when autoextensible = 'YES' and maxbytes > bytes then maxbytes else bytes end)/1024/1024 max_mb
            FROM dba_data_files
            GROUP BY tablespace_name
        ) a
        LEFT JOIN (
            SELECT tablespace_name, sum(bytes)/1024/1024 free_mb
            FROM dba_free_space
            GROUP BY tablespace_name
        ) b ON a.tablespace_name = b.tablespace_name
        WHERE ((a.total_mb - nvl(b.free_mb,0)) / NULLIF(a.max_mb,0))*100 > 90
    """
    for r in try_query(ts_q):
        alerts.append({"id": alert_id, "time": now_str, "severity": "CRITICAL", "message": f"Tablespace {r[0]} real max usage exceeds 90% (Max: {r[1]}%, Current: {r[2]}%)", "source": "Database"})
        alert_id += 1

    # 4. Blocking sessions
    blk_q = """
        select s1.sid, s1.serial#, s2.sid blocking_sid
        from v$session s1 join v$session s2 on s1.blocking_session = s2.sid
    """
    for r in try_query(blk_q):
        alerts.append({"id": alert_id, "time": now_str, "severity": "WARNING", "message": f"Blocking Session Detected (SID {r[0]} is blocked by SID {r[2]})", "source": "Database"})
        alert_id += 1

    # Sort alerts by time desc
    alerts.sort(key=lambda x: x['time'], reverse=True)
    return alerts[:100]
