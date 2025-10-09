"""
Formulation PubMed Scraper Microservice

A FastAPI microservice for scraping PubMed articles related to cannabis formulation,
extraction methods, and related pharmaceutical research.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from datetime import datetime
import asyncio
import logging

from .pubmed_scraper import PubMedScraper
from .data_processor import DataProcessor
from .storage_manager import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Formulation PubMed Scraper",
    description="Microservice for scraping PubMed articles related to cannabis formulation research",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load search terms configuration
with open("data/pubmed.json", "r") as f:
    config = json.load(f)

# Initialize components
scraper = PubMedScraper()
processor = DataProcessor()
storage = StorageManager(
    data_dir=config["output_format"]["data_directory"],
    s3_bucket=config["output_format"]["s3_bucket"]
)

class SearchRequest(BaseModel):
    category: Optional[str] = None
    custom_terms: Optional[List[str]] = None
    max_results: Optional[int] = 100
    date_range: Optional[Dict[str, int]] = None

class SearchResponse(BaseModel):
    search_id: str
    status: str
    total_results: int
    processed_at: datetime
    message: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Formulation PubMed Scraper",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "scraper": "operational",
            "processor": "operational",
            "storage": "operational"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/search-terms")
async def get_search_terms():
    """Get available search term categories"""
    return {
        "categories": list(config["search_terms"].keys()),
        "total_categories": len(config["search_terms"]),
        "total_terms": sum(len(terms) for terms in config["search_terms"].values())
    }

@app.post("/search", response_model=SearchResponse)
async def search_pubmed(request: SearchRequest, background_tasks: BackgroundTasks):
    """Search PubMed for articles based on configuration"""
    try:
        search_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine search terms
        if request.custom_terms:
            search_terms = request.custom_terms
        elif request.category and request.category in config["search_terms"]:
            search_terms = config["search_terms"][request.category]
        else:
            # Use all terms from all categories
            search_terms = []
            for category_terms in config["search_terms"].values():
                search_terms.extend(category_terms)
        
        # Set parameters
        max_results = request.max_results or config["search_parameters"]["max_results_per_term"]
        date_range = request.date_range or config["search_parameters"]["date_range"]
        
        # Start background search
        background_tasks.add_task(
            perform_search,
            search_id,
            search_terms,
            max_results,
            date_range
        )
        
        return SearchResponse(
            search_id=search_id,
            status="started",
            total_results=0,
            processed_at=datetime.now(),
            message=f"Search initiated for {len(search_terms)} terms"
        )
        
    except Exception as e:
        logger.error(f"Error initiating search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def perform_search(search_id: str, search_terms: List[str], max_results: int, date_range: Dict[str, int]):
    """Background task to perform the actual search"""
    try:
        logger.info(f"Starting search {search_id} with {len(search_terms)} terms")
        
        all_results = []
        
        for term in search_terms:
            try:
                # Search PubMed
                results = await scraper.search_articles(
                    term=term,
                    max_results=max_results,
                    date_range=date_range
                )
                
                # Process results
                processed_results = processor.process_articles(results)
                all_results.extend(processed_results)
                
                # Add delay between requests
                await asyncio.sleep(config["scheduling"]["delay_between_requests"])
                
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {str(e)}")
                continue
        
        # Store results
        await storage.store_results(search_id, all_results)
        
        logger.info(f"Search {search_id} completed with {len(all_results)} results")
        
    except Exception as e:
        logger.error(f"Error in background search {search_id}: {str(e)}")

@app.get("/results/{search_id}")
async def get_results(search_id: str):
    """Get results for a specific search"""
    try:
        results = await storage.get_results(search_id)
        if not results:
            raise HTTPException(status_code=404, detail="Search results not found")
        
        return {
            "search_id": search_id,
            "total_results": len(results),
            "results": results,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving results for {search_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results")
async def list_searches():
    """List all available search results"""
    try:
        searches = await storage.list_searches()
        return {
            "searches": searches,
            "total_searches": len(searches)
        }
        
    except Exception as e:
        logger.error(f"Error listing searches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/results/{search_id}")
async def delete_results(search_id: str):
    """Delete specific search results"""
    try:
        success = await storage.delete_results(search_id)
        if not success:
            raise HTTPException(status_code=404, detail="Search results not found")
        
        return {"message": f"Search {search_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting results for {search_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)