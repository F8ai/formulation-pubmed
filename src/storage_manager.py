"""
Storage Manager Module

Manages data storage and retrieval for the formulation-pubmed microservice.
Supports both local storage and S3 integration via DVC.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import dvc.api

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages data storage and retrieval with S3 support"""
    
    def __init__(self, data_dir: str = "data/pubmed", s3_bucket: str = "f8ai-data"):
        self.data_dir = data_dir
        self.s3_bucket = s3_bucket
        self.s3_prefix = "formulation-data/pubmed"
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3')
            self.s3_available = True
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.warning(f"S3 client initialization failed: {str(e)}")
            self.s3_client = None
            self.s3_available = False
        
        # Ensure local directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.data_dir,
            os.path.join(self.data_dir, "raw"),
            os.path.join(self.data_dir, "processed"),
            os.path.join(self.data_dir, "pdfs"),
            os.path.join(self.data_dir, "texts"),
            os.path.join(self.data_dir, "metadata"),
            os.path.join(self.data_dir, "search_results")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def store_results(self, search_id: str, results: List[Dict[str, Any]]) -> bool:
        """
        Store search results both locally and in S3
        
        Args:
            search_id: Unique identifier for the search
            results: List of processed article results
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for storage
            search_data = {
                'search_id': search_id,
                'total_results': len(results),
                'created_at': datetime.now().isoformat(),
                'results': results
            }
            
            # Store locally
            local_path = os.path.join(self.data_dir, "search_results", f"{search_id}.json")
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(search_data, f, indent=2, ensure_ascii=False)
            
            # Store in S3 if available
            if self.s3_available:
                s3_key = f"{self.s3_prefix}/search_results/{search_id}.json"
                await self._upload_to_s3(local_path, s3_key)
            
            # Update search index
            await self._update_search_index(search_id, search_data)
            
            logger.info(f"Stored {len(results)} results for search {search_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing results for search {search_id}: {str(e)}")
            return False
    
    async def get_results(self, search_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve search results
        
        Args:
            search_id: Unique identifier for the search
            
        Returns:
            List of results or None if not found
        """
        try:
            # Try local storage first
            local_path = os.path.join(self.data_dir, "search_results", f"{search_id}.json")
            
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('results', [])
            
            # Try S3 if local not found
            if self.s3_available:
                s3_key = f"{self.s3_prefix}/search_results/{search_id}.json"
                data = await self._download_from_s3(s3_key)
                if data:
                    return data.get('results', [])
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving results for search {search_id}: {str(e)}")
            return None
    
    async def list_searches(self) -> List[Dict[str, Any]]:
        """List all available searches"""
        try:
            searches = []
            
            # Check local storage
            search_dir = os.path.join(self.data_dir, "search_results")
            if os.path.exists(search_dir):
                for filename in os.listdir(search_dir):
                    if filename.endswith('.json'):
                        search_id = filename[:-5]  # Remove .json extension
                        file_path = os.path.join(search_dir, filename)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            searches.append({
                                'search_id': search_id,
                                'total_results': data.get('total_results', 0),
                                'created_at': data.get('created_at', ''),
                                'local_path': file_path
                            })
                        except Exception as e:
                            logger.warning(f"Error reading search file {filename}: {str(e)}")
            
            # Sort by creation date (newest first)
            searches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return searches
            
        except Exception as e:
            logger.error(f"Error listing searches: {str(e)}")
            return []
    
    async def delete_results(self, search_id: str) -> bool:
        """
        Delete search results
        
        Args:
            search_id: Unique identifier for the search
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from local storage
            local_path = os.path.join(self.data_dir, "search_results", f"{search_id}.json")
            if os.path.exists(local_path):
                os.remove(local_path)
            
            # Delete from S3 if available
            if self.s3_available:
                s3_key = f"{self.s3_prefix}/search_results/{search_id}.json"
                await self._delete_from_s3(s3_key)
            
            # Update search index
            await self._remove_from_search_index(search_id)
            
            logger.info(f"Deleted search results for {search_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting results for search {search_id}: {str(e)}")
            return False
    
    async def store_article_fulltext(self, pmid: str, fulltext_data: Dict[str, Any]) -> bool:
        """
        Store full text data for an article
        
        Args:
            pmid: PubMed ID
            fulltext_data: Full text data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store text file
            text_path = os.path.join(self.data_dir, "texts", f"{pmid}.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(fulltext_data.get('full_text', ''))
            
            # Store metadata
            metadata_path = os.path.join(self.data_dir, "metadata", f"{pmid}.json")
            metadata = {
                'pmid': pmid,
                'source': fulltext_data.get('full_text_source', ''),
                'pdf_path': fulltext_data.get('pdf_path', ''),
                'download_timestamp': fulltext_data.get('download_timestamp', ''),
                'text_length': len(fulltext_data.get('full_text', ''))
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Store PDF if available
            if fulltext_data.get('pdf_path') and os.path.exists(fulltext_data['pdf_path']):
                pdf_filename = f"{pmid}.pdf"
                pdf_dest = os.path.join(self.data_dir, "pdfs", pdf_filename)
                
                # Copy PDF to data directory
                import shutil
                shutil.copy2(fulltext_data['pdf_path'], pdf_dest)
                
                # Update metadata with new PDF path
                metadata['pdf_path'] = pdf_dest
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Upload to S3 if available
            if self.s3_available:
                await self._upload_article_to_s3(pmid, text_path, metadata_path)
            
            logger.info(f"Stored full text data for PMID {pmid}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing full text for PMID {pmid}: {str(e)}")
            return False
    
    async def get_article_fulltext(self, pmid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full text data for an article
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Full text data dictionary or None if not found
        """
        try:
            # Try local storage first
            text_path = os.path.join(self.data_dir, "texts", f"{pmid}.txt")
            metadata_path = os.path.join(self.data_dir, "metadata", f"{pmid}.json")
            
            if os.path.exists(text_path) and os.path.exists(metadata_path):
                with open(text_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                return {
                    'full_text': full_text,
                    'full_text_source': metadata.get('source', ''),
                    'pdf_path': metadata.get('pdf_path', ''),
                    'download_timestamp': metadata.get('download_timestamp', '')
                }
            
            # Try S3 if local not found
            if self.s3_available:
                return await self._download_article_from_s3(pmid)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving full text for PMID {pmid}: {str(e)}")
            return None
    
    async def _upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """Upload file to S3"""
        try:
            self.s3_client.upload_file(local_path, self.s3_bucket, s3_key)
            logger.debug(f"Uploaded {local_path} to s3://{self.s3_bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False
    
    async def _download_from_s3(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Download JSON file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return None
    
    async def _delete_from_s3(self, s3_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            logger.debug(f"Deleted s3://{self.s3_bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting from S3: {str(e)}")
            return False
    
    async def _upload_article_to_s3(self, pmid: str, text_path: str, metadata_path: str):
        """Upload article files to S3"""
        try:
            # Upload text file
            text_key = f"{self.s3_prefix}/texts/{pmid}.txt"
            await self._upload_to_s3(text_path, text_key)
            
            # Upload metadata
            metadata_key = f"{self.s3_prefix}/metadata/{pmid}.json"
            await self._upload_to_s3(metadata_path, metadata_key)
            
        except Exception as e:
            logger.error(f"Error uploading article {pmid} to S3: {str(e)}")
    
    async def _download_article_from_s3(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Download article files from S3"""
        try:
            # Download metadata
            metadata_key = f"{self.s3_prefix}/metadata/{pmid}.json"
            metadata = await self._download_from_s3(metadata_key)
            
            if not metadata:
                return None
            
            # Download text
            text_key = f"{self.s3_prefix}/texts/{pmid}.txt"
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=text_key)
            full_text = response['Body'].read().decode('utf-8')
            
            return {
                'full_text': full_text,
                'full_text_source': metadata.get('source', ''),
                'pdf_path': metadata.get('pdf_path', ''),
                'download_timestamp': metadata.get('download_timestamp', '')
            }
            
        except Exception as e:
            logger.error(f"Error downloading article {pmid} from S3: {str(e)}")
            return None
    
    async def _update_search_index(self, search_id: str, search_data: Dict[str, Any]):
        """Update the search index"""
        try:
            index_path = os.path.join(self.data_dir, "search_index.json")
            
            # Load existing index
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    index = json.load(f)
            else:
                index = {'searches': []}
            
            # Add or update search entry
            search_entry = {
                'search_id': search_id,
                'total_results': search_data.get('total_results', 0),
                'created_at': search_data.get('created_at', ''),
                'status': 'completed'
            }
            
            # Remove existing entry if present
            index['searches'] = [s for s in index['searches'] if s['search_id'] != search_id]
            
            # Add new entry
            index['searches'].append(search_entry)
            
            # Sort by creation date
            index['searches'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Save index
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error updating search index: {str(e)}")
    
    async def _remove_from_search_index(self, search_id: str):
        """Remove search from index"""
        try:
            index_path = os.path.join(self.data_dir, "search_index.json")
            
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    index = json.load(f)
                
                # Remove search entry
                index['searches'] = [s for s in index['searches'] if s['search_id'] != search_id]
                
                # Save updated index
                with open(index_path, 'w') as f:
                    json.dump(index, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error removing from search index: {str(e)}")
    
    def sync_to_s3(self):
        """Sync local data to S3 using DVC"""
        try:
            import subprocess
            result = subprocess.run(['dvc', 'push'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Successfully synced data to S3")
                return True
            else:
                logger.error(f"DVC push failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error syncing to S3: {str(e)}")
            return False
    
    def pull_from_s3(self):
        """Pull data from S3 using DVC"""
        try:
            import subprocess
            result = subprocess.run(['dvc', 'pull'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Successfully pulled data from S3")
                return True
            else:
                logger.error(f"DVC pull failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error pulling from S3: {str(e)}")
            return False