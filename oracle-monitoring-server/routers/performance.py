from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import random
import os
import httpx
from datetime import datetime, timedelta

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
    """Return mock ASH history (last 30 minutes)"""
    data = []
    now = datetime.datetime.now()
    wait_classes = ["User I/O", "System I/O", "Concurrency", "CPU"]
    
    # Generate 30 data points
    for i in range(30):
        t = now - datetime.timedelta(minutes=30 - i)
        # For stacked area chart, we might need multiple entries per timestamp or aggregate
        # Here simplifying: Total Active Sessions
        data.append({
            "time": t.strftime("%H:%M"),
            "active_sessions": random.randint(10, 150),
            "wait_class": random.choice(wait_classes)
        })
    return data

@router.get("/top-sql")
async def get_top_sql():
    """Return Top SQL by elapsed time"""
    if AGENT_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{AGENT_URL}/metrics/top-sql")
                if resp.status_code == 200:
                    return resp.json()
        except:
             pass

    # Mock Data Fallback
    sql_texts = [
        "SELECT * FROM sales_orders WHERE status = 'PENDING' AND region = :1",
        "UPDATE inventory_stock SET quantity = quantity - :qty WHERE item_id = :id",
        "INSERT INTO user_audit_log (user_id, action_time, action_type) VALUES (:1, SYSDATE, :2)",
        "SELECT /*+ FULL(t) */ count(*) FROM heavy_transaction_table t JOIN reference_data r ON t.ref_id = r.id",
        "DELETE FROM session_cache WHERE last_access < SYSDATE - 1/24",
        "BEGIN update_customer_score(:cust_id); END;",
        "SELECT product_id, sum(amount) FROM daily_sales GROUP BY product_id ORDER BY 2 DESC"
    ]
    modules = ["OrderEntry", "Reporting", "BackgroundJob", "UserInterface", "JDBC Thin Client"]
    schemas = ["APP_MAIN", "HR_PROD", "DW_LOAD", "SYS"]
    
    data = []
    for i in range(15):
        data.append({
            "sql_id": f"{random.choice('abcdef0123456789')}{random.randint(10000,99999)}",
            "sql_text": random.choice(sql_texts),
            "cpu_time": round(random.uniform(0.1, 15.0), 2),
            "elapsed_time": round(random.uniform(0.5, 60.0), 2),
            "executions": random.randint(5, 10000),
            "parsing_schema": random.choice(schemas),
            "module": random.choice(modules)
        })
    
    # Sort by elapsed time descending
    data.sort(key=lambda x: x['elapsed_time'], reverse=True)
    return data

@router.get("/sql/{sql_id}")
async def get_sql_details(sql_id: str):
    """Return detailed SQL info including plan"""
    # Mock data based on SQL ID
    return {
        "sql_id": sql_id,
        "sql_text": """SELECT /*+ FULL(o) */ 
    o.order_id, o.order_date, c.customer_name, Sum(l.quantity * l.unit_price) amount
FROM 
    orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items l ON o.order_id = l.order_id
WHERE 
    o.order_date >= TRUNC(SYSDATE - 7)
    AND c.region = 'APAC'
GROUP BY 
    o.order_id, o.order_date, c.customer_name
ORDER BY 
    amount DESC""",
        "stats": {
            "executions": random.randint(100, 10000),
            "elapsed_time": round(random.uniform(10, 500), 2),
            "cpu_time": round(random.uniform(5, 400), 2),
            "buffer_gets": random.randint(10000, 5000000),
            "disk_reads": random.randint(0, 50000),
            "rows_processed": random.randint(1000, 100000)
        },
        "plan": [
            {"id": 0, "parent_id": None, "operation": "SELECT STATEMENT", "options": "", "object": "", "cost": 1520, "cardinality": 100},
            {"id": 1, "parent_id": 0, "operation": "SORT", "options": "ORDER BY", "object": "", "cost": 1520, "cardinality": 100},
            {"id": 2, "parent_id": 1, "operation": "HASH", "options": "GROUP BY", "object": "", "cost": 1520, "cardinality": 100},
            {"id": 3, "parent_id": 2, "operation": "HASH JOIN", "options": "", "object": "", "cost": 1400, "cardinality": 5000},
            {"id": 4, "parent_id": 3, "operation": "TABLE ACCESS", "options": "FULL", "object": "CUSTOMERS", "cost": 300, "cardinality": 1000},
            {"id": 5, "parent_id": 3, "operation": "HASH JOIN", "options": "", "object": "", "cost": 1000, "cardinality": 50000},
            {"id": 6, "parent_id": 5, "operation": "TABLE ACCESS", "options": "FULL", "object": "ORDERS", "cost": 400, "cardinality": 10000},
            {"id": 7, "parent_id": 5, "operation": "TABLE ACCESS", "options": "FULL", "object": "ORDER_ITEMS", "cost": 500, "cardinality": 100000}
        ]
    }
