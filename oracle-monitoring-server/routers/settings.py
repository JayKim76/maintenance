from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import socket

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
async def test_connection(info: ConnectionInfo):
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
        return {
            "status": "error", 
            "message": f"Connection Failed: {str(e)}"
        }
