"""
Full Text Downloader Module

Downloads full text articles from PubMed, arXiv, and Sci-Hub as needed.
"""

import asyncio
import aiohttp
import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote
import json
from datetime import datetime
import hashlib

# PDF processing
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF

# Web scraping
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class FullTextDownloader:
    """Downloads full text articles from various sources"""
    
    def __init__(self, data_dir: str = "pubmed"):
        self.data_dir = data_dir
        self.pdf_dir = os.path.join(data_dir, "pdfs")
        self.text_dir = os.path.join(data_dir, "texts")
        self.metadata_dir = os.path.join(data_dir, "metadata")
        
        # Create directories
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        
        # Initialize web driver for Sci-Hub
        self.driver = None
        self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver for Sci-Hub access"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {str(e)}")
            self.driver = None
    
    async def download_full_text(self, article: Dict) -> Dict:
        """
        Download full text for an article from available sources
        
        Args:
            article: Article dictionary with metadata
            
        Returns:
            Updated article dictionary with full text information
        """
        pmid = article.get('pmid', '')
        doi = article.get('doi', '')
        title = article.get('title', '')
        
        logger.info(f"Attempting to download full text for PMID: {pmid}")
        
        # Check if already downloaded
        existing_text = self._check_existing_download(pmid)
        if existing_text:
            logger.info(f"Full text already exists for PMID: {pmid}")
            return existing_text
        
        # Try different sources in order of preference
        sources = [
            ('pubmed_central', self._download_from_pubmed_central),
            ('arxiv', self._download_from_arxiv),
            ('sci_hub', self._download_from_sci_hub),
            ('direct_pdf', self._download_direct_pdf)
        ]
        
        for source_name, download_func in sources:
            try:
                logger.info(f"Trying {source_name} for PMID: {pmid}")
                result = await download_func(article)
                
                if result and result.get('full_text'):
                    # Save the downloaded content
                    await self._save_full_text(pmid, result)
                    logger.info(f"Successfully downloaded full text from {source_name} for PMID: {pmid}")
                    return result
                    
            except Exception as e:
                logger.warning(f"Failed to download from {source_name} for PMID {pmid}: {str(e)}")
                continue
        
        logger.warning(f"Could not download full text for PMID: {pmid}")
        return article
    
    def _check_existing_download(self, pmid: str) -> Optional[Dict]:
        """Check if full text already exists for this PMID"""
        text_file = os.path.join(self.text_dir, f"{pmid}.txt")
        metadata_file = os.path.join(self.metadata_dir, f"{pmid}.json")
        
        if os.path.exists(text_file) and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                with open(text_file, 'r', encoding='utf-8') as f:
                    full_text = f.read()
                
                return {
                    'full_text': full_text,
                    'full_text_source': metadata.get('source', 'unknown'),
                    'pdf_path': metadata.get('pdf_path', ''),
                    'download_timestamp': metadata.get('download_timestamp', '')
                }
            except Exception as e:
                logger.error(f"Error reading existing download for PMID {pmid}: {str(e)}")
        
        return None
    
    async def _download_from_pubmed_central(self, article: Dict) -> Optional[Dict]:
        """Download full text from PubMed Central"""
        pmid = article.get('pmid', '')
        
        try:
            # Check if article is available in PMC
            pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(pmc_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract full text from HTML
                        full_text = self._extract_text_from_html(soup)
                        
                        if full_text and len(full_text) > 1000:  # Reasonable length check
                            return {
                                'full_text': full_text,
                                'full_text_source': 'pubmed_central',
                                'pdf_path': '',
                                'download_timestamp': datetime.now().isoformat()
                            }
        
        except Exception as e:
            logger.error(f"Error downloading from PubMed Central for PMID {pmid}: {str(e)}")
        
        return None
    
    async def _download_from_arxiv(self, article: Dict) -> Optional[Dict]:
        """Download full text from arXiv if available"""
        title = article.get('title', '').lower()
        
        # Check if title suggests arXiv paper
        if 'arxiv' not in title and 'preprint' not in title:
            return None
        
        try:
            # Search arXiv for the paper
            arxiv_query = self._build_arxiv_query(article)
            arxiv_url = f"http://export.arxiv.org/api/query?search_query={arxiv_query}&max_results=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(arxiv_url) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        soup = BeautifulSoup(xml_content, 'xml')
                        
                        entry = soup.find('entry')
                        if entry:
                            pdf_url = entry.find('link', {'type': 'application/pdf'})
                            if pdf_url:
                                pdf_url = pdf_url.get('href')
                                
                                # Download PDF
                                pdf_content = await self._download_pdf(pdf_url)
                                if pdf_content:
                                    # Extract text from PDF
                                    full_text = self._extract_text_from_pdf_content(pdf_content)
                                    
                                    if full_text:
                                        # Save PDF
                                        pdf_path = os.path.join(self.pdf_dir, f"{article.get('pmid', 'unknown')}.pdf")
                                        with open(pdf_path, 'wb') as f:
                                            f.write(pdf_content)
                                        
                                        return {
                                            'full_text': full_text,
                                            'full_text_source': 'arxiv',
                                            'pdf_path': pdf_path,
                                            'download_timestamp': datetime.now().isoformat()
                                        }
        
        except Exception as e:
            logger.error(f"Error downloading from arXiv: {str(e)}")
        
        return None
    
    async def _download_from_sci_hub(self, article: Dict) -> Optional[Dict]:
        """Download full text from Sci-Hub (use with caution)"""
        if not self.driver:
            logger.warning("Selenium driver not available for Sci-Hub access")
            return None
        
        doi = article.get('doi', '')
        if not doi or doi == 'N/A':
            return None
        
        try:
            # Sci-Hub URL (this may change frequently)
            sci_hub_url = f"https://sci-hub.se/{doi}"
            
            self.driver.get(sci_hub_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for PDF link
            pdf_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf']")
            
            if pdf_links:
                pdf_url = pdf_links[0].get_attribute('href')
                
                # Download PDF
                pdf_content = await self._download_pdf(pdf_url)
                if pdf_content:
                    # Extract text from PDF
                    full_text = self._extract_text_from_pdf_content(pdf_content)
                    
                    if full_text:
                        # Save PDF
                        pdf_path = os.path.join(self.pdf_dir, f"{article.get('pmid', 'unknown')}.pdf")
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_content)
                        
                        return {
                            'full_text': full_text,
                            'full_text_source': 'sci_hub',
                            'pdf_path': pdf_path,
                            'download_timestamp': datetime.now().isoformat()
                        }
        
        except Exception as e:
            logger.error(f"Error downloading from Sci-Hub: {str(e)}")
        
        return None
    
    async def _download_direct_pdf(self, article: Dict) -> Optional[Dict]:
        """Try to download PDF directly from journal website"""
        doi = article.get('doi', '')
        if not doi or doi == 'N/A':
            return None
        
        try:
            # Try common PDF URL patterns
            pdf_urls = [
                f"https://doi.org/{doi}.pdf",
                f"https://link.springer.com/content/pdf/{doi}.pdf",
                f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
                f"https://www.nature.com/articles/{doi.split('/')[-1]}.pdf"
            ]
            
            for pdf_url in pdf_urls:
                try:
                    pdf_content = await self._download_pdf(pdf_url)
                    if pdf_content and len(pdf_content) > 10000:  # Reasonable size check
                        # Extract text from PDF
                        full_text = self._extract_text_from_pdf_content(pdf_content)
                        
                        if full_text:
                            # Save PDF
                            pdf_path = os.path.join(self.pdf_dir, f"{article.get('pmid', 'unknown')}.pdf")
                            with open(pdf_path, 'wb') as f:
                                f.write(pdf_content)
                            
                            return {
                                'full_text': full_text,
                                'full_text_source': 'direct_pdf',
                                'pdf_path': pdf_path,
                                'download_timestamp': datetime.now().isoformat()
                            }
                except:
                    continue
        
        except Exception as e:
            logger.error(f"Error downloading direct PDF: {str(e)}")
        
        return None
    
    async def _download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF content from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Check if it's actually a PDF
                        if content.startswith(b'%PDF'):
                            return content
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {str(e)}")
        
        return None
    
    def _extract_text_from_html(self, soup: BeautifulSoup) -> str:
        """Extract text content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_text_from_pdf_content(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            # Try PyMuPDF first (better for complex PDFs)
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            
            if text and len(text) > 100:  # Reasonable text length
                return text
            
        except Exception as e:
            logger.warning(f"PyMuPDF failed, trying pdfplumber: {str(e)}")
        
        try:
            # Fallback to pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                return text
                
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
        
        try:
            # Final fallback to PyPDF2
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"All PDF extraction methods failed: {str(e)}")
            return ""
    
    def _build_arxiv_query(self, article: Dict) -> str:
        """Build arXiv search query from article metadata"""
        title = article.get('title', '')
        authors = article.get('authors', [])
        
        # Use first author and title for search
        query_parts = []
        
        if authors:
            first_author = authors[0].split(',')[0].strip()
            query_parts.append(f"au:{first_author}")
        
        if title:
            # Extract key words from title
            title_words = title.split()[:5]  # First 5 words
            query_parts.append(f"ti:{' '.join(title_words)}")
        
        return '+AND+'.join(query_parts)
    
    async def _save_full_text(self, pmid: str, result: Dict):
        """Save full text and metadata to files"""
        try:
            # Save text file
            text_file = os.path.join(self.text_dir, f"{pmid}.txt")
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(result['full_text'])
            
            # Save metadata
            metadata_file = os.path.join(self.metadata_dir, f"{pmid}.json")
            metadata = {
                'pmid': pmid,
                'source': result['full_text_source'],
                'pdf_path': result.get('pdf_path', ''),
                'download_timestamp': result['download_timestamp'],
                'text_length': len(result['full_text'])
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved full text for PMID {pmid}")
            
        except Exception as e:
            logger.error(f"Error saving full text for PMID {pmid}: {str(e)}")
    
    def close(self):
        """Close the Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None