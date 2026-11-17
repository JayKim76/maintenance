from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
import httpx

from core.database import get_real_ash_history, get_real_top_sql
import core.database as db_module

router = APIRouter(
    prefix="/api/performance",
    tags=["performance"]
)

# Agent URL (e.g., http://db-server-ip:8001)
AGENT_URL = os.getenv("ORACLE_AGENT_URL")

# Models
class AshData(BaseModel):
    time: str
    active_sessions: int
    wait_class: str

class SqlData(BaseModel):
    sql_id: str
    sql_text: str
    cpu_time: float
    elapsed_time: float
    executions: int
    parsing_schema: str
    module: str

# Endpoints
@router.get("/ash", response_model=List[AshData])
async def get_ash_history():
    """Return ASH history (last 30 minutes) — empty if not connected"""
    real_data = await get_real_ash_history()
    return real_data

@router.get("/top-sql")
async def get_top_sql():
    """Return Top SQL by elapsed time — empty if not connected"""
    if AGENT_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{AGENT_URL}/metrics/top-sql")
                if resp.status_code == 200:
                    return resp.json()
        except:
             pass

    real_data = await get_real_top_sql()
    return real_data

@router.get("/sql/{sql_id}")
async def get_sql_details(sql_id: str):
    """Return detailed SQL info including plan from v$sql / v$sql_plan"""
    if db_module.MOCK_MODE or not db_module.pool:
        return {"status": "error", "message": "Database not connected."}

    try:
        # Stats from v$sql (aggregate across child cursors)
        stats_rows = db_module._run_query(f"""
            SELECT sql_text,
                   sum(executions) AS executions,
                   round(sum(elapsed_time)/1e6, 2) AS elapsed_time,
                   round(sum(cpu_time)/1e6, 2) AS cpu_time,
                   sum(buffer_gets) AS buffer_gets,
                   sum(disk_reads) AS disk_reads,
                   sum(rows_processed) AS rows_processed
            FROM v$sql
            WHERE sql_id = '{sql_id}'
            GROUP BY sql_text
        """, fetch="one")

        if not stats_rows:
            return {"status": "error", "message": f"SQL ID '{sql_id}' not found in v$sql."}

        sql_text, execs, elapsed, cpu, bufs, reads, rows_p = stats_rows
        stats = {
            "executions": int(execs or 0),
            "elapsed_time": float(elapsed or 0),
            "cpu_time": float(cpu or 0),
            "buffer_gets": int(bufs or 0),
            "disk_reads": int(reads or 0),
            "rows_processed": int(rows_p or 0),
        }

        # Execution plan from v$sql_plan (first child cursor)
        plan_rows = db_module._run_query(f"""
            SELECT id, parent_id, operation, options,
                   object_name, cost, cardinality
            FROM v$sql_plan
            WHERE sql_id = '{sql_id}' AND child_number = 0
            ORDER BY id
        """)
        plan = []
        for r in (plan_rows or []):
            plan.append({
                "id": r[0],
                "parent_id": r[1],
                "operation": str(r[2] or ""),
                "options": str(r[3] or ""),
                "object": str(r[4] or ""),
                "cost": int(r[5]) if r[5] else 0,
                "cardinality": int(r[6]) if r[6] else 0,
            })

        return {
            "status": "success",
            "sql_id": sql_id,
            "sql_text": str(sql_text or ""),
            "stats": stats,
            "plan": plan,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
