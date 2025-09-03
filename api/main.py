"""
FastAPI server for webscraper API.

This server provides endpoints for:
1. Crawling websites and storing content
2. Searching through embedded content
3. Managing crawl jobs and status
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
import uuid

# Import our existing modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.crawler.crawler import Crawler
from src.embedder.embedder import Embedder
from src.search.semantic import SemanticSearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Webscraper API",
    description="API for crawling websites and semantic search",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CrawlRequest(BaseModel):
    url: HttpUrl
    max_depth: Optional[int] = 3
    max_pages: Optional[int] = 1000

class CrawlResponse(BaseModel):
    job_id: str
    status: str
    message: str

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# In-memory job storage (replace with Redis/database in production)
jobs: Dict[str, JobStatus] = {}

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Webscraper API is running", "version": "1.0.0"}

@app.post("/api/crawl", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Start a crawl job for the given URL.
    
    This endpoint:
    1. Creates a new crawl job
    2. Starts the crawl in the background
    3. Returns the job ID for status tracking
    """
    job_id = str(uuid.uuid4())
    
    # Create job status
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="started",
        message="Crawl job created",
        created_at=datetime.now()
    )
    
    # Start crawl in background
    background_tasks.add_task(run_crawl_job, job_id, str(request.url), request.max_depth, request.max_pages)
    
    return CrawlResponse(
        job_id=job_id,
        status="started",
        message="Crawl job started successfully"
    )

@app.get("/api/crawl/{job_id}/status", response_model=JobStatus)
async def get_crawl_status(job_id: str):
    """Get the status of a crawl job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.post("/api/search", response_model=SearchResponse)
async def search_content(request: SearchRequest):
    """
    Search through embedded content using semantic similarity.
    
    This endpoint:
    1. Encodes the search query
    2. Performs vector similarity search
    3. Returns ranked results
    """
    try:
        with SemanticSearch() as search:
            results = search.search(request.query, top_k=request.limit)
            
            # Convert to response format
            search_results = []
            for url, snippet, score in results:
                # Extract title from URL for now (could be enhanced)
                title = url.split('/')[-1] or url
                search_results.append(SearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    score=score
                ))
            
            return SearchResponse(
                results=search_results,
                total=len(search_results)
            )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/embed", response_model=CrawlResponse)
async def start_embed(background_tasks: BackgroundTasks):
    """
    Start an embedding job for all unembedded pages.
    
    This endpoint:
    1. Creates a new embed job
    2. Runs the embedder in the background
    3. Returns the job ID for status tracking
    """
    job_id = str(uuid.uuid4())
    
    # Create job status
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="started",
        message="Embed job created",
        created_at=datetime.now()
    )
    
    # Start embed in background
    background_tasks.add_task(run_embed_job, job_id)
    
    return CrawlResponse(
        job_id=job_id,
        status="started",
        message="Embed job started successfully"
    )

@app.get("/api/embed/{job_id}/status", response_model=JobStatus)
async def get_embed_status(job_id: str):
    """Get the status of an embed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

async def run_crawl_job(job_id: str, url: str, max_depth: int, max_pages: int):
    """
    Background task to run the crawl job.
    
    This function:
    1. Updates job status to running
    2. Runs the crawler
    3. Runs the embedder
    4. Updates job status to completed
    """
    try:
        # Update job status
        jobs[job_id].status = "running"
        jobs[job_id].message = "Starting crawl..."
        
        # Run crawler
        logger.info(f"Starting crawl for job {job_id}: {url}")
        crawler = Crawler()
        await crawler.crawl(url)
        
        # Update job status
        jobs[job_id].message = "Crawl completed, starting embedding..."
        
        # Run embedder
        logger.info(f"Starting embedding for job {job_id}")
        with Embedder() as embedder:
            embedder.run()
        
        # Update job status to completed
        jobs[job_id].status = "completed"
        jobs[job_id].message = "Crawl and embedding completed successfully"
        jobs[job_id].completed_at = datetime.now()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].message = f"Job failed: {str(e)}"
        jobs[job_id].completed_at = datetime.now()

async def run_embed_job(job_id: str):
    """
    Background task to run the embed job.
    
    This function:
    1. Updates job status to running
    2. Runs the embedder
    3. Updates job status to completed
    """
    try:
        # Update job status
        jobs[job_id].status = "running"
        jobs[job_id].message = "Starting embedding..."
        
        # Run embedder
        logger.info(f"Starting embedding for job {job_id}")
        with Embedder() as embedder:
            embedder.run()
        
        # Update job status to completed
        jobs[job_id].status = "completed"
        jobs[job_id].message = "Embedding completed successfully"
        jobs[job_id].completed_at = datetime.now()
        
        logger.info(f"Embed job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Embed job {job_id} failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].message = f"Embed job failed: {str(e)}"
        jobs[job_id].completed_at = datetime.now()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 