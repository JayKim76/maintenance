from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import os
import httpx
from typing import List, Any

from core.database import execute_custom_sql
from core.auth import get_current_role, check_permission, Role

router = APIRouter(
    prefix="/api/editor",
    tags=["editor"]
)

AGENT_URL = os.getenv("ORACLE_AGENT_URL")

class QueryRequest(BaseModel):
    sql: str

@router.post("/execute")
async def execute_query(
    request: QueryRequest, 
    role: Role = Depends(get_current_role)
):
    """
    Execute SQL query via Agent if configured, else DB.
    Authorized for ADMIN, DBA, OPERATOR.
    """
    if role == Role.VIEWER:
        raise HTTPException(status_code=403, detail="VIEWER role cannot execute SQL.")

    if AGENT_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{AGENT_URL}/execute", 
                    json={"sql": request.sql},
                    headers={"X-Role": role.value}
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {"status": "error", "message": f"Agent Error: {resp.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect to Agent: {str(e)}"}

    # Execute using real database connection
    try:
        result = await execute_custom_sql(request.sql, role=role.value)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Database execution failed: {str(e)}"}

@router.post("/upload")
async def upload_sql_file(
    file: UploadFile = File(...),
    role: Role = Depends(get_current_role)
):
    """
    Upload and execute SQL file content.
    Authorized for ADMIN, DBA, OPERATOR.
    """
    if role == Role.VIEWER:
        raise HTTPException(status_code=403, detail="VIEWER role cannot upload/execute SQL.")

    try:
        content = await file.read()
        
        # Try multiple encodings
        sql_text = None
        for encoding in ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949', 'latin-1']:
            try:
                sql_text = content.decode(encoding)
                break
            except (UnicodeDecodeError, ValueError):
                continue
        
        if sql_text is None:
            return {"status": "error", "message": "Failed to decode file. Unsupported encoding."}
        
        result = await execute_query(QueryRequest(sql=sql_text), role=role)
        
        # Include the uploaded SQL text in the response so client can display it
        if isinstance(result, dict):
            result['sql_text'] = sql_text
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
