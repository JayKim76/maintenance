from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import random
import os
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import random
from typing import List, Any

router = APIRouter(
    prefix="/api/editor",
    tags=["editor"]
)

AGENT_URL = os.getenv("ORACLE_AGENT_URL")

class QueryRequest(BaseModel):
    sql: str

@router.post("/execute")
async def execute_query(request: QueryRequest):
    """
    Execute SQL query via Agent if configured, else Mock.
    """
    if AGENT_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{AGENT_URL}/execute", json={"sql": request.sql})
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {"status": "error", "message": f"Agent Error: {resp.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect to Agent: {str(e)}"}

    # Mock Exec logic
    sql_upper = request.sql.strip().upper()
    
    # Simple Mock Logic based on query type
    columns = []
    rows = []
    
    if sql_upper.startswith("SELECT"):
        columns = ["ID", "NAME", "STATUS", "CREATED_AT", "VALUE"]
        for i in range(1, 11):
            rows.append([
                i, 
                f"Item_{i}_{random.randint(1000,9999)}", 
                random.choice(["ACTIVE", "INACTIVE", "PENDING"]),
                "2023-01-01 12:00:00",
                random.randint(10, 1000)
            ])
    else:
        # DML
        return {
            "status": "success",
            "message": f"Statement executed successfully. {random.randint(1, 100)} rows affected."
        }
        
    return {
        "status": "success",
        "columns": columns,
        "rows": rows,
        "message": "Query executed successfully."
    }

@router.post("/upload")
async def upload_sql_file(file: UploadFile = File(...)):
    """
    Upload and execute SQL file content.
    """
    try:
        content = await file.read()
        sql_text = content.decode("utf-8")
        
        # In real scenario, we would parse and execute multiple statements.
        # Here we just treat it as one execution for demo.
        
        return await execute_query(QueryRequest(sql=sql_text))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
