import os
import random
from typing import Dict, Any

# Environment variables
DB_USER = os.getenv("DB_USER", "system")
DB_PASSWORD = os.getenv("DB_PASSWORD", "oracle")
DB_DSN = os.getenv("DB_DSN", "localhost/orclpdb1")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

pool = None

async def init_db():
    """Initialize DB connection pool (or Mock setup)"""
    global pool, MOCK_MODE
    if MOCK_MODE:
        print("⚡ Running in MOCK MODE (No real DB connection)")
        return
    
    try:
        import oracledb
        # Initialize Oracle Client (Thin mode default, Thick mode if lib dir set)
        pool = oracledb.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            min=2,
            max=5,
            increment=1
        )
        print(f"✅ Connected to Oracle DB: {DB_DSN}")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        print("⚠️ Falling back to MOCK MODE due to connection failure")
        MOCK_MODE = True

async def get_db_metrics() -> Dict[str, Any]:
    """Fetch system metrics from DB or Generate Mock Data"""
    if MOCK_MODE:
        return _generate_mock_metrics()
    
    # Real DB Query
    try:
        if not pool:
            return _generate_mock_metrics()
            
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Example: Get Average Active Sessions (AAS)
                await cursor.execute("SELECT count(*) FROM v$session WHERE status = 'ACTIVE' AND type != 'BACKGROUND'")
                row = await cursor.fetchone()
                active_sessions = row[0] if row else 0
                
                # Mocking others for now as real queries are complex
                base_mock = _generate_mock_metrics()
                base_mock['active_sessions'] = active_sessions
                return base_mock
                
    except Exception as e:
        print(f"Query Error: {e}")
        return _generate_mock_metrics()

def _generate_mock_metrics():
    """Generate realistic random data for dashboard"""
    return {
        "cpu_load": round(random.uniform(15, 45), 1),
        "memory_usage": round(random.uniform(40, 70), 1),
        "active_sessions": random.randint(80, 150),
        "disk_io": random.randint(200, 500), # MB/s
        "top_sql": [
            {"sql_id": "84r398fn", "elapsed_time": 4.5, "cpu_time": 2.1, "executions": 120},
            {"sql_id": "92anf832", "elapsed_time": 3.2, "cpu_time": 1.5, "executions": 85},
            {"sql_id": "1m39d92s", "elapsed_time": 1.2, "cpu_time": 0.8, "executions": 450},
        ],
        "wait_events": [
            {"name": "User I/O", "value": random.randint(30, 50), "color": "#84cc16"},
            {"name": "System I/O", "value": random.randint(10, 30), "color": "#06b6d4"},
            {"name": "Concurrency", "value": random.randint(5, 15), "color": "#8b5cf6"},
            {"name": "Commit", "value": random.randint(5, 10), "color": "#f59e0b"},
            {"name": "Other", "value": random.randint(5, 10), "color": "#64748b"},
        ]
    }
