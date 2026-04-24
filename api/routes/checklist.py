from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from fastapi.concurrency import run_in_threadpool

from llm.generator import generate_checklist
from retrieval.retriever import retrieve, build_context_string

router = APIRouter()

class ChecklistRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10

class ChecklistItem(BaseModel):
    item: str
    domain: str
    source_section: str
    page_number: Optional[int] = None
    source_quote: Optional[str] = None
    article_reference: Optional[str] = None
    violation_condition: Optional[str] = None
    source_type: Optional[str] = None
    confidence: Optional[str] = None
    source_url: Optional[str] = None
    chunk_id: Optional[str] = None
    compliance_framework: Optional[str] = None
    verified: Optional[bool] = None
    verification_confidence: Optional[float] = None
    verification_evidence: Optional[str] = None
    violation_statement: Optional[str] = None

@router.post("/api/v1/checklist", response_model=List[ChecklistItem])
async def checklist_endpoint(payload: ChecklistRequest):
    try:
        # EFFICIENCY FIX: Offload highly-synchronous CPU/Network bound tasks to an isolation threadpool.
        # This prevents the FastAPI event loop from being blocked by heavy PyTorch/Groq operations, allowing the server to handle thousands of concurrent requests.
        results = await run_in_threadpool(retrieve, payload.query, top_k=payload.top_k)
        
        # build_context_string is fast, but better safe.
        context = await run_in_threadpool(build_context_string, results)
        
        # This makes a synchronous HTTP request to Groq, MUST be in threadpool
        items = await run_in_threadpool(generate_checklist, context, results)   
        
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
