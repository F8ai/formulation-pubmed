"""
Background Processor Module

Handles continuous background processing of PubMed articles with progressive enhancement:
1. Metadata scraping
2. Abstract extraction
3. Full-text download
4. OCR processing for RAG
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from .pubmed_scraper import PubMedScraper
from .data_processor import DataProcessor
from .fulltext_downloader import FullTextDownloader
from .storage_manager import StorageManager
from .git_manager import GitManager
from .rss_generator import RSSGenerator
from .status_generator import StatusGenerator

logger = logging.getLogger(__name__)

class BackgroundProcessor:
    """Background processor for continuous PubMed article processing"""
    
    def __init__(self, config: Dict[str, Any], storage: StorageManager):
        self.config = config
        self.storage = storage
        self.scraper = PubMedScraper()
        self.processor = DataProcessor()
        self.downloader = FullTextDownloader()
        self.git_manager = GitManager()
        self.rss_generator = RSSGenerator(git_manager=self.git_manager)
        self.status_generator = StatusGenerator()
        
        self.running = False
        self.processing_queue = asyncio.Queue()
        self.processed_pmids = set()
        self.last_rss_generation = None
        self.last_status_update = None
        
        # Load processed PMIDs from index
        self._load_processed_index()
        
        # Setup Git configuration
        asyncio.create_task(self.git_manager.setup_git_config())
    
    def _load_processed_index(self):
        """Load index of already processed PMIDs"""
        try:
            index_path = os.path.join(self.storage.data_dir, "index", "processed_pmids.json")
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    data = json.load(f)
                    self.processed_pmids = set(data.get('pmids', []))
                logger.info(f"Loaded {len(self.processed_pmids)} processed PMIDs from index")
        except Exception as e:
            logger.error(f"Error loading processed index: {str(e)}")
            self.processed_pmids = set()
    
    def _save_processed_index(self):
        """Save index of processed PMIDs"""
        try:
            index_path = os.path.join(self.storage.data_dir, "index", "processed_pmids.json")
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            data = {
                'pmids': list(self.processed_pmids),
                'last_updated': datetime.now().isoformat(),
                'total_processed': len(self.processed_pmids)
            }
            
            with open(index_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving processed index: {str(e)}")
    
    async def start(self):
        """Start the background processing"""
        if self.running:
            logger.warning("Background processor already running")
            return
        
        self.running = True
        logger.info("Starting background PubMed processor")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._search_worker()),
            asyncio.create_task(self._processing_worker()),
            asyncio.create_task(self._fulltext_worker()),
            asyncio.create_task(self._ocr_worker()),
            asyncio.create_task(self._index_worker()),
            asyncio.create_task(self._rss_worker()),
            asyncio.create_task(self._status_worker())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in background processing: {str(e)}")
        finally:
            self.running = False
            logger.info("Background processor stopped")
    
    async def stop(self):
        """Stop the background processing"""
        self.running = False
        logger.info("Stopping background processor")
    
    async def _search_worker(self):
        """Worker that continuously searches for new articles"""
        logger.info("Starting search worker")
        
        while self.running:
            try:
                # Get search terms from config
                search_terms = self.config["search_terms"]
                date_range = self.config["search_parameters"]["date_range"]
                max_results = self.config["search_parameters"]["max_results_per_term"]
                
                # Search each category
                for category, terms in search_terms.items():
                    if not self.running:
                        break
                    
                    logger.info(f"Searching category: {category} with {len(terms)} terms")
                    
                    for term in terms:
                        if not self.running:
                            break
                        
                        try:
                            # Search PubMed
                            articles = await self.scraper.search_articles(
                                term=term,
                                max_results=max_results,
                                date_range=date_range
                            )
                            
                            # Add new articles to processing queue
                            for article in articles:
                                pmid = article.get('pmid')
                                if pmid and pmid not in self.processed_pmids:
                                    await self.processing_queue.put({
                                        'pmid': pmid,
                                        'article': article,
                                        'stage': 'metadata',
                                        'category': category,
                                        'search_term': term
                                    })
                            
                            # Rate limiting
                            await asyncio.sleep(self.config["scheduling"]["delay_between_requests"])
                            
                        except Exception as e:
                            logger.error(f"Error searching term '{term}': {str(e)}")
                            continue
                
                # Wait before next search cycle
                await asyncio.sleep(3600)  # 1 hour between search cycles
                
            except Exception as e:
                logger.error(f"Error in search worker: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _processing_worker(self):
        """Worker that processes metadata and abstracts"""
        logger.info("Starting processing worker")
        
        while self.running:
            try:
                # Get article from queue
                item = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                
                pmid = item['pmid']
                article = item['article']
                
                if pmid in self.processed_pmids:
                    continue
                
                logger.info(f"Processing metadata for PMID: {pmid}")
                
                # Process article metadata
                processed_article = self.processor.process_articles([article])[0]
                
                if processed_article:
                    # Store metadata and abstract
                    await self._store_metadata_and_abstract(pmid, processed_article)
                    
                    # Add to queue for full-text processing
                    await self.processing_queue.put({
                        'pmid': pmid,
                        'article': processed_article,
                        'stage': 'fulltext',
                        'category': item['category'],
                        'search_term': item['search_term']
                    })
                
                self.processed_pmids.add(pmid)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in processing worker: {str(e)}")
                await asyncio.sleep(1)
    
    async def _fulltext_worker(self):
        """Worker that downloads full text"""
        logger.info("Starting fulltext worker")
        
        while self.running:
            try:
                # Get article from queue
                item = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                
                if item['stage'] != 'fulltext':
                    # Put back in queue for other workers
                    await self.processing_queue.put(item)
                    continue
                
                pmid = item['pmid']
                article = item['article']
                
                logger.info(f"Downloading full text for PMID: {pmid}")
                
                # Download full text
                fulltext_data = await self.downloader.download_full_text(article)
                
                if fulltext_data and fulltext_data.get('full_text'):
                    # Store full text
                    await self.storage.store_article_fulltext(pmid, fulltext_data)
                    
                    # Add to queue for OCR processing
                    await self.processing_queue.put({
                        'pmid': pmid,
                        'article': fulltext_data,
                        'stage': 'ocr',
                        'category': item['category'],
                        'search_term': item['search_term']
                    })
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in fulltext worker: {str(e)}")
                await asyncio.sleep(1)
    
    async def _ocr_worker(self):
        """Worker that performs OCR processing for RAG"""
        logger.info("Starting OCR worker")
        
        while self.running:
            try:
                # Get article from queue
                item = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                
                if item['stage'] != 'ocr':
                    # Put back in queue for other workers
                    await self.processing_queue.put(item)
                    continue
                
                pmid = item['pmid']
                article = item['article']
                
                logger.info(f"Performing OCR processing for PMID: {pmid}")
                
                # Perform OCR processing
                await self._process_ocr_for_rag(pmid, article)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in OCR worker: {str(e)}")
                await asyncio.sleep(1)
    
    async def _index_worker(self):
        """Worker that updates indices and saves progress"""
        logger.info("Starting index worker")
        
        while self.running:
            try:
                # Save processed index every 5 minutes
                await asyncio.sleep(300)
                self._save_processed_index()
                
                # Update search index
                await self._update_search_index()
                
            except Exception as e:
                logger.error(f"Error in index worker: {str(e)}")
                await asyncio.sleep(60)
    
    async def _rss_worker(self):
        """Worker that generates RSS feeds"""
        logger.info("Starting RSS worker")
        
        while self.running:
            try:
                # Check if we should generate RSS feeds
                should_generate = self._should_generate_rss()
                
                if should_generate:
                    logger.info("Generating RSS feeds")
                    
                    # Generate all RSS feeds
                    feeds = await self.rss_generator.generate_rss_feeds(commit_to_git=True)
                    
                    if feeds:
                        self.last_rss_generation = datetime.now()
                        logger.info(f"Generated {len(feeds)} RSS feeds")
                        
                        # Commit RSS feeds to Git
                        await self.git_manager.commit_and_push_if_needed(
                            'rss_update', 
                            len(feeds), 
                            force_push=True
                        )
                
                # Wait 1 hour before next check
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in RSS worker: {str(e)}")
                await asyncio.sleep(300)
    
    async def _status_worker(self):
        """Worker that updates status pages"""
        logger.info("Starting status worker")
        
        while self.running:
            try:
                # Check if we should update status
                should_update = self._should_update_status()
                
                if should_update:
                    logger.info("Updating status page")
                    
                    # Generate status page
                    status_path = await self.status_generator.generate_status_page()
                    
                    if status_path:
                        self.last_status_update = datetime.now()
                        logger.info(f"Updated status page: {status_path}")
                        
                        # Commit status update to Git
                        await self.git_manager.commit_and_push_if_needed(
                            'status_update', 
                            1, 
                            force_push=True
                        )
                
                # Wait 30 minutes before next check
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Error in status worker: {str(e)}")
                await asyncio.sleep(300)
    
    async def _store_metadata_and_abstract(self, pmid: str, article: Dict[str, Any]):
        """Store metadata and abstract for an article"""
        try:
            # Create PMID directory
            pmid_dir = os.path.join(self.storage.data_dir, "articles", pmid)
            os.makedirs(pmid_dir, exist_ok=True)
            
            # Store abstract
            abstract_path = os.path.join(pmid_dir, "abstract", "content.txt")
            os.makedirs(os.path.dirname(abstract_path), exist_ok=True)
            with open(abstract_path, 'w', encoding='utf-8') as f:
                f.write(article.get('abstract', ''))
            
            # Store metadata
            metadata = {
                'pmid': pmid,
                'title': article.get('title', ''),
                'authors': article.get('authors', []),
                'journal': article.get('journal', ''),
                'publication_date': article.get('publication_date', ''),
                'doi': article.get('doi', ''),
                'keywords': article.get('keywords', []),
                'mesh_terms': article.get('mesh_terms', []),
                'url': article.get('url', ''),
                'relevance_score': article.get('relevance_score', 0.0),
                'formulation_relevance': article.get('formulation_relevance', {}),
                'cannabis_relevance': article.get('cannabis_relevance', {}),
                'extracted_entities': article.get('extracted_entities', {}),
                'key_phrases': article.get('key_phrases', []),
                'processing_stage': 'metadata_abstract',
                'processed_at': datetime.now().isoformat()
            }
            
            metadata_path = os.path.join(pmid_dir, "metadata", "article.json")
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stored metadata and abstract for PMID: {pmid}")
            
        except Exception as e:
            logger.error(f"Error storing metadata for PMID {pmid}: {str(e)}")
    
    async def _process_ocr_for_rag(self, pmid: str, article: Dict[str, Any]):
        """Process OCR data for RAG indexing"""
        try:
            pmid_dir = os.path.join(self.storage.data_dir, "articles", pmid)
            ocr_dir = os.path.join(pmid_dir, "ocr")
            os.makedirs(ocr_dir, exist_ok=True)
            
            # Extract text from PDF if available
            pdf_path = article.get('pdf_path', '')
            if pdf_path and os.path.exists(pdf_path):
                # Use existing PDF text extraction
                full_text = article.get('full_text', '')
                
                # Create RAG-ready chunks
                chunks = self._create_rag_chunks(full_text, pmid)
                
                # Save chunks for RAG
                chunks_path = os.path.join(ocr_dir, "rag_chunks.json")
                with open(chunks_path, 'w') as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)
                
                # Create searchable text
                searchable_text = self._create_searchable_text(article)
                searchable_path = os.path.join(ocr_dir, "searchable_text.txt")
                with open(searchable_path, 'w', encoding='utf-8') as f:
                    f.write(searchable_text)
                
                # Update metadata
                metadata_path = os.path.join(pmid_dir, "metadata", "article.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    metadata['processing_stage'] = 'complete'
                    metadata['rag_chunks_count'] = len(chunks)
                    metadata['ocr_processed_at'] = datetime.now().isoformat()
                    
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Completed OCR processing for PMID: {pmid}")
            
        except Exception as e:
            logger.error(f"Error processing OCR for PMID {pmid}: {str(e)}")
    
    def _create_rag_chunks(self, text: str, pmid: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Create RAG-ready text chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if len(chunk_text.strip()) > 50:  # Minimum chunk size
                chunks.append({
                    'pmid': pmid,
                    'chunk_id': f"{pmid}_{len(chunks)}",
                    'text': chunk_text,
                    'start_word': i,
                    'end_word': min(i + chunk_size, len(words)),
                    'word_count': len(chunk_words)
                })
        
        return chunks
    
    def _create_searchable_text(self, article: Dict[str, Any]) -> str:
        """Create searchable text combining all available content"""
        parts = []
        
        # Add title
        if article.get('title'):
            parts.append(f"TITLE: {article['title']}")
        
        # Add abstract
        if article.get('abstract'):
            parts.append(f"ABSTRACT: {article['abstract']}")
        
        # Add full text
        if article.get('full_text'):
            parts.append(f"FULL_TEXT: {article['full_text']}")
        
        # Add keywords
        if article.get('keywords'):
            parts.append(f"KEYWORDS: {', '.join(article['keywords'])}")
        
        # Add MeSH terms
        if article.get('mesh_terms'):
            parts.append(f"MESH_TERMS: {', '.join(article['mesh_terms'])}")
        
        return '\n\n'.join(parts)
    
    async def _update_search_index(self):
        """Update the search index with processed articles"""
        try:
            # This would integrate with your RAG system
            # For now, just log the update
            logger.info(f"Updated search index with {len(self.processed_pmids)} articles")
        except Exception as e:
            logger.error(f"Error updating search index: {str(e)}")
    
    def _should_generate_rss(self) -> bool:
        """Determine if RSS feeds should be generated"""
        # Generate RSS feeds every 6 hours or if never generated
        if not self.last_rss_generation:
            return True
        
        time_since_last = datetime.now() - self.last_rss_generation
        return time_since_last.total_seconds() > 21600  # 6 hours
    
    def _should_update_status(self) -> bool:
        """Determine if status page should be updated"""
        # Update status every 30 minutes or if never updated
        if not self.last_status_update:
            return True
        
        time_since_last = datetime.now() - self.last_status_update
        return time_since_last.total_seconds() > 1800  # 30 minutes
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        return {
            'running': self.running,
            'processed_count': len(self.processed_pmids),
            'queue_size': self.processing_queue.qsize(),
            'last_rss_generation': self.last_rss_generation.isoformat() if self.last_rss_generation else None,
            'last_status_update': self.last_status_update.isoformat() if self.last_status_update else None,
            'last_updated': datetime.now().isoformat()
        }