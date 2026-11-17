from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os
import socket
import json
from typing import List, Dict, Any
from core.database import reconnect_db
import core.database as db_module
from core.auth import check_permission, Role

router = APIRouter(prefix="/api/settings", tags=["settings"])

class ConnectionInfo(BaseModel):
    host: str
    port: str
    service_name: str
    username: str
    password: str
    mode: str = "SERVICE_NAME" # SERVICE_NAME or SID

def check_tcp_connection(host: str, port: int, timeout: int = 3):
    """Fail fast if host is unreachable"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except  OSError:
        return False

@router.post("/test-connection")
async def test_connection(
    info: ConnectionInfo,
    role: Role = Depends(check_permission("modify_settings"))
):
    """Test Oracle DB Connection"""
    
    # 1. TCP Reachability Check (Fail Fast)
    try:
        port = int(info.port)
        if not check_tcp_connection(info.host, port):
             return {
                "status": "error", 
                "message": f"Network Error: Unable to reach {info.host}:{port} (TCP Connection Refused or Timeout)."
            }
    except ValueError:
         return {"status": "error", "message": "Invalid Port Number"}

    # Mock Connection for Testing
    if info.host == "localhost" and info.password == "mock":
        return {
            "status": "success",
            "message": f"Successfully connected to MOCK DB (Simulated)"
        }
    
    try:
        # Try importing driver
        try:
            import oracledb as db_driver
            db_module.ensure_thick_mode()
        except ImportError:
            try:
                import cx_Oracle as db_driver
            except ImportError:
                return {
                    "status": "error", 
                    "message": "Oracle Driver (python-oracledb or cx_Oracle) not found in server environment."
                }

        # Construct DSN based on Mode
        if info.mode == "SID":
            dsn = db_driver.makedsn(info.host, info.port, sid=info.service_name)
        else:
            dsn = f"{info.host}:{info.port}/{info.service_name}"

        # Try connecting
        connection = db_driver.connect(
            user=info.username,
            password=info.password,
            dsn=dsn
        )
        version = connection.version
        connection.close()
        
        return {
            "status": "success",
            "message": f"Successfully connected to {dsn} (DB Version: {version})"
        }
        
    except Exception as e:
        err_msg = str(e)
        if "DPI-1050" in err_msg:
            err_msg += " (해결방법: ORACLE_THICK_MODE=false 로 설정하여 Thin 모드를 사용하시거나, Oracle Instant Client 19c 이상 64-bit를 설치 후 ORACLE_CLIENT_DIR을 지정하세요.)"
        elif "DPY-3010" in err_msg or "DPY-3015" in err_msg:
            err_msg += " (해결방법: 구버전 DB 인증을 위해 Thick 모드가 필요합니다. Oracle Instant Client 19c 이상 64-bit를 설치하고 ORACLE_THICK_MODE=true 및 ORACLE_CLIENT_DIR을 설정하세요.)"
        return {
            "status": "error", 
            "message": f"Connection Failed: {err_msg}"
        }

@router.post("/connect")
async def connect_to_db(
    info: ConnectionInfo,
    role: Role = Depends(check_permission("modify_settings"))
):
    """Apply Oracle DB Connection globally"""
    
    # Construct DSN based on Mode
    try:
        if info.mode == "SID":
            import oracledb as db_driver
            dsn = db_driver.makedsn(info.host, info.port, sid=info.service_name)
        else:
            dsn = f"{info.host}:{info.port}/{info.service_name}"
            
        success, message = await reconnect_db(
            user=info.username,
            password=info.password,
            dsn=dsn
        )
        
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "error", "message": message}
            
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Connection Apply Failed: {str(e)}"
        }

@router.get("/status")
async def get_connection_status():
    """Check current DB connection status"""
    if db_module.MOCK_MODE or not db_module.pool:
        return {
            "connected": False,
            "dsn": None,
            "user": None
        }
    return {
        "connected": True,
        "dsn": db_module.DB_DSN,
        "user": db_module.DB_USER
    }

@router.post("/disconnect")
async def disconnect_db():
    """Disconnect from Oracle DB and revert to mock mode"""
    try:
        if db_module.pool:
            try:
                db_module.pool.close(force=True)
            except Exception:
                pass
        db_module.pool = None
        db_module.MOCK_MODE = True
        db_module.DB_USER = None
        db_module.DB_PASSWORD = None
        db_module.DB_DSN = None
        db_module._remove_config()
                 
        return {"status": "success", "message": "Disconnected from database."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

import sys
if getattr(sys, 'frozen', False):
    CONNECTIONS_FILE = os.path.join(os.path.dirname(sys.executable), "saved_connections.json")
else:
    CONNECTIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "saved_connections.json")

@router.get("/saved-connections")
async def get_saved_connections():
    """Get list of saved database connections"""
    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

@router.post("/saved-connections")
async def save_connections(
    connections: List[Dict[str, Any]],
    role: Role = Depends(check_permission("modify_settings"))
):
    """Save the list of database connections"""
    try:
        with open(CONNECTIONS_FILE, "w") as f:
            json.dump(connections, f, indent=4)
        return {"status": "success", "message": "Connections saved successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save connections: {str(e)}"}

@router.get("/last-connection")
async def get_last_connection():
    """Get last connected DB configuration or first saved connection for pre-filling form"""
    cfg = db_module._load_config()
    if not cfg:
        # Fallback to first saved connection if available
        if os.path.exists(CONNECTIONS_FILE):
            try:
                with open(CONNECTIONS_FILE, "r") as f:
                    saved = json.load(f)
                    if saved and isinstance(saved, list) and len(saved) > 0:
                        first = saved[0]
                        return {
                            "status": "success",
                            "alias": first.get("alias", ""),
                            "host": first.get("host", ""),
                            "port": first.get("port", "1521"),
                            "service_name": first.get("service_name", ""),
                            "username": first.get("username", "system"),
                            "password": first.get("password", ""),
                            "mode": first.get("mode", "SERVICE_NAME")
                        }
            except Exception:
                pass
        return {"status": "none"}

    user = cfg.get("user", "system")
    password = cfg.get("password", "")
    dsn = cfg.get("dsn", "")
    
    host = ""
    port = "1521"
    service_name = ""
    mode = "SERVICE_NAME"
    
    try:
        if "/" in dsn:
            hp, service_name = dsn.split("/", 1)
            mode = "SERVICE_NAME"
            if ":" in hp:
                host, port = hp.split(":", 1)
            else:
                host = hp
        elif ":" in dsn:
            parts = dsn.split(":")
            if len(parts) == 3:
                host, port, service_name = parts[0], parts[1], parts[2]
                mode = "SID"
            elif len(parts) == 2:
                host, port = parts[0], parts[1]
            else:
                host = dsn
        else:
            host = dsn
    except Exception:
        pass

    return {
        "status": "success",
        "alias": "",
        "host": host,
        "port": port,
        "service_name": service_name,
        "username": user,
        "password": password,
        "mode": mode
    }

