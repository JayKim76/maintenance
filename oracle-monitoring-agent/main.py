import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import oracledb
try:
    oracledb.init_oracle_client()
except Exception:
    pass
import os
import datetime

# --- Configuration ---
# DB Connection Info (Load from Env or Default)
DB_USER = os.getenv("DB_USER", "system")
DB_PASSWORD = os.getenv("DB_PASSWORD", "oracle")
DB_DSN = os.getenv("DB_DSN", "localhost/XE")

from pydantic import BaseModel

app = FastAPI(title="Oracle Monitoring Agent")

class QueryRequest(BaseModel):
    sql: str

# ... (pool setup)

@app.post("/execute")
async def execute_query(request: QueryRequest):
    """
    Execute arbitrary SQL from Monitoring Server.
    """
    try:
        if not pool:
             raise Exception("DB Pool not initialized")
             
        with pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.execute(request.sql)
                # Fetch results if SELECT
                if request.sql.strip().upper().startswith("SELECT"):
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    # Serialize rows (handle dates etc if needed, but for now simple)
                    return {
                        "status": "success",
                        "columns": columns,
                        "rows": rows
                    }
                else:
                    return {
                        "status": "success",
                        "message": f"Executed. Rows affected: {cursor.rowcount}"
                    }
    except Exception as e:
        return {"status": "error", "message": str(e)}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global DB Pool
pool = None

async def get_db_connection():
    global pool
    if not pool:
        try:
            pool = oracledb.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                dsn=DB_DSN,
                min=2,
                max=5,
                increment=1
            )
            print(f"Connected to Oracle DB: {DB_DSN}")
        except Exception as e:
            print(f"Failed to connect to Oracle DB: {e}")
            raise HTTPException(status_code=500, detail=f"DB Connection Error: {str(e)}")
    
    return pool.acquire()

@app.on_event("startup")
async def startup_event():
    # Attempt connection on startup
    try:
        await get_db_connection()
    except:
        pass # Allow startup even if DB is down initially

@app.get("/")
def health_check():
    return {"status": "running", "agent": "oracle-monitoring-agent-v1"}

@app.get("/metrics/ash")
def get_ash_metrics():
    """
    Collect Active Session History (ASH) roughly mimicking real-time active sessions.
    """
    # Query to get active sessions grouped by wait class
    sql = """
    SELECT 
        TO_CHAR(sample_time, 'HH24:MI') as time_str,
        wait_class,
        COUNT(*) as session_count
    FROM 
        v$active_session_history
    WHERE 
        sample_time > SYSDATE - 1/24/60 # Last 1 minute
    GROUP BY 
        TO_CHAR(sample_time, 'HH24:MI'), wait_class
    ORDER BY 
        time_str
    """
    
    # Needs real DB execution.
    # For now, if no DB connection, return error or mock?
    # User asked for the DAEMON code, so we write REAL code.
    
    try:
        if not pool:
             raise Exception("DB Pool not initialized")
             
        with pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                # Format: [{"time": "10:00", "active_sessions": 10, "wait_class": "CPU"}]
                result = []
                for row in rows:
                    result.append({
                        "time": row[0],
                        "wait_class": row[1] if row[1] else "CPU", # NULL often means CPU
                        "active_sessions": row[2]
                    })
                return result
    except Exception as e:
         return {"error": str(e), "note": "Ensure Agent is running on DB Server with correct credentials."}

@app.get("/metrics/top-sql")
def get_top_sql():
    """
    Get Top SQL by Elapsed Time
    """
    sql = """
    SELECT 
        sql_id,
        substr(sql_text, 1, 100) as sql_text,
        elapsed_time / 1000000 as elapsed_sec,
        cpu_time / 1000000 as cpu_sec,
        executions,
        module
    FROM 
        v$sql
    WHERE 
        elapsed_time > 0
    ORDER BY 
        elapsed_time DESC
    FETCH FIRST 10 ROWS ONLY
    """
    
    try:
        if not pool:
             raise Exception("DB Pool not initialized")
             
        with pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Run Agent on Port 8001 (Distinct from Server 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)
