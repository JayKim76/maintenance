import os
import json
import sys
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    CONFIG_FILE = os.path.join(base_dir, "connections.json")
    env_path = os.path.join(base_dir, '.env')
else:
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    CONFIG_FILE = os.path.join(base_dir, "connections.json")
    env_path = os.path.join(base_dir, '.env')

load_dotenv(dotenv_path=env_path)

def ensure_thick_mode():
    """Ensure thick mode is initialized using ORACLE_CLIENT_DIR or fallback candidate paths."""
    try:
        import oracledb
        if not oracledb.is_thin_mode():
            return True, "Thick mode already active"

        env_dir = os.getenv("ORACLE_CLIENT_DIR")
        candidates = []
        if env_dir:
            candidates.append(env_dir)
        
        default_paths = [
            r"C:\oracle\instantclient_19_30",
            r"C:\oracle\instantclient_19_24",
            r"C:\oracle\instantclient_19_19",
            r"C:\oracle\instantclient_21_3",
            r"C:\oracle\instantclient",
            r"C:\instantclient_19_30",
            r"C:\instantclient"
        ]
        for p in default_paths:
            if p not in candidates:
                candidates.append(p)

        found_dir = None
        for c in candidates:
            if c and os.path.exists(c):
                found_dir = c
                break

        try:
            if found_dir:
                # Remove any old conflicting Oracle Home paths (e.g. C:\app\...\11.2.0\dbhome_1\bin) from PATH
                # and place found_dir as the FIRST entry in PATH to resolve DPI-1072 DLL version mismatch
                current_path = os.environ.get("PATH", "")
                path_parts = current_path.split(os.pathsep)
                clean_parts = [
                    p for p in path_parts
                    if "dbhome" not in p.lower() and "product\\11." not in p.lower()
                ]
                os.environ["PATH"] = found_dir + os.pathsep + os.pathsep.join(clean_parts)

                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(found_dir)
                    except Exception:
                        pass

                oracledb.init_oracle_client(lib_dir=found_dir)
                print(f"[OK] Thick mode initialized (lib_dir={found_dir})")
            else:
                oracledb.init_oracle_client()
                print("[OK] Thick mode initialized (system PATH)")
            
            if not oracledb.is_thin_mode():
                return True, "Thick mode initialized successfully"
            else:
                return False, "Driver remains in thin mode"
        except Exception as ex:
            ex_str = str(ex)
            if "already been initialized" in ex_str:
                return True, "Already initialized"
            print(f"[WARN] Failed to init thick mode: {ex_str}")
            return False, ex_str
    except Exception as e:
        print(f"[WARN] Error initializing thick mode: {e}")
        return False, str(e)

# Initialize thick mode immediately at module load time
# so the entire server process uses thick mode for all DB operations
ensure_thick_mode()

def _load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def _save_config(user, password, dsn):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"user": user, "password": password, "dsn": dsn}, f)
    except Exception as e:
        print(f"Error saving config: {e}")

def _remove_config():
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
    except Exception as e:
        print(f"Error removing config: {e}")

# Always start disconnected — user must connect via Connections page
DB_USER = None
DB_PASSWORD = None
DB_DSN = None
MOCK_MODE = True

pool = None

async def init_db():
    """Initialize DB in disconnected (MOCK) mode. User connects via the UI."""
    print("[STARTUP] Server started in disconnected mode. Use Connections page to connect.")

async def reconnect_db(user, password, dsn):
    """Re-establish DB connection pool dynamically from Settings"""
    global pool, MOCK_MODE, DB_USER, DB_PASSWORD, DB_DSN
    
    try:
        import oracledb
        thick_ok, thick_msg = ensure_thick_mode()
        
        if oracledb.is_thin_mode():
            err_msg = (
                f"Thick 모드 활성화 실패 ({thick_msg}). "
                "Oracle 11g 및 구버전 DB 접속을 위해 Thick 모드(Instant Client 64-bit)가 필수입니다. "
                "C:\\oracle\\instantclient_19_30 경로 또는 .env 파일의 ORACLE_CLIENT_DIR을 확인하세요."
            )
            print(f"[ERROR] {err_msg}")
            return False, err_msg

        # Close existing pool
        if pool:
            try:
                pool.close(force=True)
            except Exception as e:
                print(f"[WARN] Error closing old pool: {e}")
                
        # Create new pool (synchronous for Thick mode)
        new_pool = oracledb.create_pool(
            user=user,
            password=password,
            dsn=dsn,
            min=2,
            max=5,
            increment=1
        )
        
        # Update globals only on success
        pool = new_pool
        DB_USER = user
        DB_PASSWORD = password
        DB_DSN = dsn
        MOCK_MODE = False
        
        _save_config(user, password, dsn)
        
        print(f"[OK] Dynamically connected to Oracle DB: {DB_DSN}")
        return True, f"Successfully connected to {DB_DSN}"
        
    except Exception as e:
        err_msg = str(e)
        if "DPY-3010" in err_msg or "DPY-3015" in err_msg:
            err_msg += " (해결방법: 구버전 Oracle DB 접속을 위해 Thick 모드가 필요합니다. Instant Client가 C:\\oracle\\instantclient_19_30 등에 설치되어 있는지 확인하고 .env 파일의 ORACLE_THICK_MODE=true 및 ORACLE_CLIENT_DIR 경로를 확인하세요.)"
        print(f"[ERROR] Dynamic DB Connection Failed: {err_msg}")
        return False, err_msg

def _run_query(sql, fetch="all"):
    """Run a synchronous query against the pool and return results"""
    conn = pool.acquire()
    try:
        # callTimeout is a Connection-level attribute (milliseconds), not Cursor-level
        try:
            conn.callTimeout = 5000
        except AttributeError:
            pass
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            if fetch == "one":
                return cursor.fetchone()
            elif fetch == "all":
                return cursor.fetchall()
            else:
                return None
        finally:
            cursor.close()
    finally:
        pool.release(conn)

def _empty_metrics():
    """Return empty metrics structure when not connected"""
    return {
        "cpu_load": 0,
        "memory_usage": 0,
        "active_sessions": 0,
        "disk_io": 0,
        "top_sql": [],
        "wait_events": [],
        "connected": False
    }

async def get_db_metrics() -> Dict[str, Any]:
    """Fetch system metrics from DB — returns empty data if not connected"""
    if MOCK_MODE or not pool:
        return _empty_metrics()
    
    try:
        metrics = {"connected": True}
        
        # Active Sessions
        try:
            row = _run_query("SELECT count(*) FROM v$session WHERE status = 'ACTIVE' AND type != 'BACKGROUND'", "one")
            metrics['active_sessions'] = row[0] if row else 0
        except Exception as e:
            print(f"Error fetching active sessions: {e}")
            metrics['active_sessions'] = 0
        
        # CPU Load (from v$osstat)
        try:
            rows = _run_query("""
                SELECT value FROM v$osstat WHERE stat_name = 'IDLE_TIME' 
                UNION ALL 
                SELECT value FROM v$osstat WHERE stat_name = 'BUSY_TIME'
            """)
            if rows and len(rows) == 2:
                idle_time = float(rows[0][0])
                busy_time = float(rows[1][0])
                total_time = idle_time + busy_time
                metrics['cpu_load'] = round((busy_time / total_time) * 100, 1) if total_time > 0 else 0.0
            else:
                metrics['cpu_load'] = 0
        except Exception as e:
            print(f"Error fetching CPU load: {e}")
            metrics['cpu_load'] = 0
            
        # Memory Usage (from v$osstat)
        try:
            rows = _run_query("""
                SELECT stat_name, value FROM v$osstat 
                WHERE stat_name IN ('PHYSICAL_MEMORY_BYTES', 'FREE_MEMORY_BYTES')
            """)
            if rows and len(rows) == 2:
                mem_stats = {str(r[0]): float(r[1]) for r in rows}
                total_mem = mem_stats.get('PHYSICAL_MEMORY_BYTES', 0.0)
                free_mem = mem_stats.get('FREE_MEMORY_BYTES', 0.0)
                used_mem = total_mem - free_mem
                metrics['memory_usage'] = round((used_mem / total_mem) * 100, 1) if total_mem > 0 else 0.0
            else:
                metrics['memory_usage'] = 0
        except Exception as e:
            print(f"Error fetching memory usage: {e}")
            metrics['memory_usage'] = 0

        # Disk I/O (MB/s) - From v$sysmetric
        try:
            row = _run_query("""
                SELECT round((value/1024/1024), 2)
                FROM v$sysmetric 
                WHERE metric_name = 'Physical Read Total Bytes Per Sec'
            """, "one")
            metrics['disk_io'] = row[0] if row else 0
        except Exception as e:
            print(f"Error fetching Disk I/O: {e}")
            metrics['disk_io'] = 0
            
        # Wait Events Distribution (excluding Idle events)
        try:
            rows = _run_query("""
                SELECT * FROM (
                    SELECT wait_class, sum(time_waited) as time_waited
                    FROM v$system_wait_class 
                    WHERE wait_class != 'Idle'
                    GROUP BY wait_class
                    ORDER BY time_waited DESC
                ) WHERE ROWNUM <= 5
            """)
            
            colors = ["#f87171", "#fb923c", "#fbbf24", "#34d399", "#60a5fa"]
            total_wait = sum([r[1] for r in rows]) if rows else 0
            
            wait_events = []
            if rows:
                for idx, r in enumerate(rows):
                    pct = round((r[1] / total_wait) * 100, 1) if total_wait > 0 else 0
                    wait_events.append({
                        "name": r[0],
                        "value": pct,
                        "color": colors[idx % len(colors)]
                    })
            metrics['wait_events'] = wait_events
        except Exception as e:
            print(f"Error fetching wait events: {e}")
            metrics['wait_events'] = []
            
        # Top SQL
        try:
            sql_rows = _run_query("""
                SELECT * FROM (
                    SELECT sql_id, substr(replace(sql_text,chr(10),' '),1,60), round(elapsed_time/1e6,1)
                    FROM v$sql WHERE executions > 0 ORDER BY elapsed_time DESC
                ) WHERE ROWNUM <= 5
            """)
            metrics['top_sql'] = [{"sql_id": str(r[0]), "sql_text": str(r[1]), "elapsed_s": float(r[2])} for r in (sql_rows or [])]
        except Exception:
            metrics['top_sql'] = []

        # Tablespaces summary (Top 4)
        try:
            ts_rows = _run_query("""
                SELECT * FROM (
                    SELECT a.tablespace_name,
                           round(((a.total_mb - NVL(b.free_mb,0)) / NULLIF(a.total_mb,0))*100, 1) AS used_pct,
                           round(((a.total_mb - NVL(b.free_mb,0)) / NULLIF(a.max_mb,0))*100, 1) AS max_used_pct
                    FROM (
                        SELECT tablespace_name,
                               sum(bytes)/1024/1024 AS total_mb,
                               sum(CASE WHEN autoextensible = 'YES' AND maxbytes > bytes THEN maxbytes ELSE bytes END)/1024/1024 AS max_mb
                        FROM dba_data_files
                        GROUP BY tablespace_name
                    ) a
                    LEFT JOIN (
                        SELECT tablespace_name, sum(bytes)/1024/1024 AS free_mb
                        FROM dba_free_space
                        GROUP BY tablespace_name
                    ) b ON a.tablespace_name = b.tablespace_name
                    ORDER BY max_used_pct DESC NULLS LAST
                ) WHERE ROWNUM <= 4
            """)
            metrics['tablespaces'] = [{"name": str(r[0]), "used_pct": float(r[1] or 0), "max_used_pct": float(r[2] or 0)} for r in (ts_rows or [])]
        except Exception:
            metrics['tablespaces'] = []

        return metrics
                
    except Exception as e:
        print(f"Query Error: {e}")
        return _empty_metrics()

async def get_real_ash_history() -> list:
    if MOCK_MODE or not pool:
        return []
    try:
        rows = _run_query("""
            SELECT to_char(sample_time, 'HH24:MI'), count(*) as active_sessions, wait_class
            FROM v$active_session_history
            WHERE sample_time > sysdate - 30/(24*60)
            GROUP BY to_char(sample_time, 'HH24:MI'), wait_class
            ORDER BY 1
        """)
        data = [{"time": r[0], "active_sessions": r[1], "wait_class": r[2] or "CPU"} for r in rows]
        return data
    except Exception as e:
        print(f"Error fetching ASH: {e}")
        return []

async def get_real_top_sql() -> list:
    if MOCK_MODE or not pool:
        return []
    try:
        rows = _run_query("""
            SELECT * FROM (
                SELECT sql_id, substr(sql_text, 1, 100), cpu_time/1000000, elapsed_time/1000000, executions, parsing_schema_name, module
                FROM v$sql
                WHERE elapsed_time > 0
                ORDER BY elapsed_time DESC
            ) WHERE ROWNUM <= 15
        """)
        data = []
        for r in rows:
            data.append({
                "sql_id": str(r[0]),
                "sql_text": str(r[1]) if r[1] else "",
                "cpu_time": round(float(r[2]), 2) if r[2] else 0.0,
                "elapsed_time": round(float(r[3]), 2) if r[3] else 0.0,
                "executions": int(r[4]) if r[4] else 0,
                "parsing_schema": str(r[5]) if r[5] else "",
                "module": str(r[6]) if r[6] else ""
            })
        return data
    except Exception as e:
        print(f"Error fetching Top SQL: {e}")
        return []

import re

async def execute_custom_sql(sql_text: str, role: str = "VIEWER") -> dict:
    """Execute raw SQL statement and return results with role-based restriction"""
    if MOCK_MODE or not pool:
        return {"status": "error", "message": "Database not connected. Mock mode active."}
        
    if role == "VIEWER":
        return {"status": "error", "message": "VIEWER role is not allowed to execute any SQL queries."}

    try:
        # Pre-process: remove SQL*Plus commands and clean up
        lines = sql_text.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip SQL*Plus commands
            upper = stripped.upper()
            if upper.startswith(('SET ', 'SPOOL ', 'EXIT', 'QUIT', 'PROMPT ', 'WHENEVER ', 'DEFINE ', 'COLUMN ', 'TTITLE', 'BTITLE', 'REM ', 'ACCEPT ')):
                continue
            # Skip standalone slash (PL/SQL terminator)
            if stripped == '/':
                continue
            # Skip single-line comments
            if stripped.startswith('--'):
                continue
            cleaned_lines.append(line)
        
        cleaned_sql = '\n'.join(cleaned_lines)
        
        # Split by semicolon and filter empty
        statements = [s.strip() for s in cleaned_sql.split(';') if s.strip()]
        if not statements:
            return {"status": "error", "message": "No valid SQL statements found."}
            
        # Role check for individual statements (for OPERATOR)
        if role == "OPERATOR":
            for stmt in statements:
                stmt_clean = stmt.lstrip().upper()
                # Basic check: Only allow starting with SELECT or WITH
                if not (stmt_clean.startswith("SELECT") or stmt_clean.startswith("WITH") or stmt_clean.startswith("EXPLAIN PLAN")):
                    return {"status": "error", "message": f"Operation denied for OPERATOR role: Only SELECT queries are allowed."}

        conn = pool.acquire()
        try:
            # callTimeout is a Connection-level attribute (milliseconds), not Cursor-level
            try:
                conn.callTimeout = 15000  # custom SQL can be a bit longer
            except AttributeError:
                pass
            cursor = conn.cursor()
            try:
                results = []
                for stmt in statements:
                    stmt_upper = stmt.upper().lstrip()
                    if stmt_upper.startswith("SELECT") or stmt_upper.startswith("WITH") or stmt_upper.startswith("EXPLAIN PLAN"):
                        cursor.execute(stmt)
                        rows = cursor.fetchall()
                        columns = [col[0] for col in cursor.description] if cursor.description else []
                        results.append({
                            "type": "SELECT",
                            "columns": columns,
                            "rows": [list(r) for r in rows],
                            "message": f"{len(rows)} rows selected."
                        })
                    else:
                        cursor.execute(stmt)
                        conn.commit()
                        results.append({
                            "type": "DML",
                            "columns": [],
                            "rows": [],
                            "message": f"Statement executed. {cursor.rowcount} rows affected."
                        })
                
                if len(results) == 1:
                    return {
                        "status": "success",
                        "columns": results[0]["columns"],
                        "rows": results[0]["rows"],
                        "message": results[0]["message"]
                    }
                else:
                    return {
                        "status": "success",
                        "columns": ["Result"],
                        "rows": [[f"Executed {len(results)} statements successfully."]],
                        "message": "Multiple statements executed."
                    }
            finally:
                cursor.close()
        finally:
            pool.release(conn)
                    
    except Exception as e:
        print(f"Error executing custom SQL: {e}")
        return {"status": "error", "message": str(e)}
