"""
PubMed Scraper Module

Handles the actual scraping of PubMed articles using the Entrez API.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class PubMedScraper:
    """PubMed scraper using NCBI Entrez API"""
    
    def __init__(self, email: str = "your-email@example.com", api_key: Optional[str] = None):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = email
        self.api_key = api_key
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_articles(
        self, 
        term: str, 
        max_results: int = 100,
        date_range: Optional[Dict[str, int]] = None,
        retmax: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed for articles matching the given term
        
        Args:
            term: Search term
            max_results: Maximum number of results to return
            date_range: Date range dict with 'start_year' and 'end_year'
            retmax: Number of results per API call (max 20)
        
        Returns:
            List of article dictionaries
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Build search query
            query = self._build_query(term, date_range)
            
            # Search for PMIDs
            pmids = await self._search_pmids(query, max_results)
            
            if not pmids:
                logger.warning(f"No PMIDs found for term: {term}")
                return []
            
            # Fetch article details in batches
            articles = []
            for i in range(0, len(pmids), retmax):
                batch_pmids = pmids[i:i + retmax]
                batch_articles = await self._fetch_article_details(batch_pmids)
                articles.extend(batch_articles)
                
                # Rate limiting
                await asyncio.sleep(0.34)  # 3 requests per second max
            
            logger.info(f"Retrieved {len(articles)} articles for term: {term}")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching for term '{term}': {str(e)}")
            return []
    
    def _build_query(self, term: str, date_range: Optional[Dict[str, int]] = None) -> str:
        """Build PubMed search query"""
        query_parts = [f'"{term}"[Title/Abstract]']
        
        if date_range:
            start_year = date_range.get('start_year', 2020)
            end_year = date_range.get('end_year', 2024)
            query_parts.append(f'("{start_year}"[Date - Publication] : "{end_year}"[Date - Publication])')
        
        # Add article type filters
        query_parts.append('("Journal Article"[Publication Type] OR "Review"[Publication Type] OR "Clinical Trial"[Publication Type])')
        
        # Add language filter
        query_parts.append('"English"[Language]')
        
        return " AND ".join(query_parts)
    
    async def _search_pmids(self, query: str, max_results: int) -> List[str]:
        """Search for PMIDs using ESearch"""
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance',
            'email': self.email
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        url = f"{self.base_url}esearch.fcgi"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"ESearch API error: {response.status}")
                    return []
                
                data = await response.json()
                pmids = data.get('esearchresult', {}).get('idlist', [])
                
                logger.info(f"Found {len(pmids)} PMIDs for query: {query}")
                return pmids
                
        except Exception as e:
            logger.error(f"Error in ESearch: {str(e)}")
            return []
    
    async def _fetch_article_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch detailed article information using EFetch"""
        if not pmids:
            return []
        
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml',
            'rettype': 'abstract',
            'email': self.email
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        url = f"{self.base_url}efetch.fcgi"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"EFetch API error: {response.status}")
                    return []
                
                xml_content = await response.text()
                articles = self._parse_xml_response(xml_content)
                
                return articles
                
        except Exception as e:
            logger.error(f"Error in EFetch: {str(e)}")
            return []
    
    def _parse_xml_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse XML response from EFetch"""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall('.//PubmedArticle'):
                article_data = self._extract_article_data(article)
                if article_data:
                    articles.append(article_data)
                    
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
        
        return articles
    
    def _extract_article_data(self, article_element) -> Optional[Dict[str, Any]]:
        """Extract article data from XML element"""
        try:
            # PMID
            pmid = article_element.find('.//PMID')
            pmid_text = pmid.text if pmid is not None else "N/A"
            
            # Article title
            title = article_element.find('.//ArticleTitle')
            title_text = title.text if title is not None else "N/A"
            
            # Abstract
            abstract = article_element.find('.//AbstractText')
            abstract_text = abstract.text if abstract is not None else "N/A"
            
            # Authors
            authors = []
            author_list = article_element.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.find('.//LastName')
                    first_name = author.find('.//ForeName')
                    if last_name is not None:
                        author_name = last_name.text
                        if first_name is not None:
                            author_name += f", {first_name.text}"
                        authors.append(author_name)
            
            # Journal
            journal = article_element.find('.//Journal/Title')
            journal_text = journal.text if journal is not None else "N/A"
            
            # Publication date
            pub_date = self._extract_publication_date(article_element)
            
            # DOI
            doi = article_element.find('.//ELocationID[@EIdType="doi"]')
            doi_text = doi.text if doi is not None else "N/A"
            
            # Keywords
            keywords = []
            keyword_list = article_element.find('.//KeywordList')
            if keyword_list is not None:
                for keyword in keyword_list.findall('.//Keyword'):
                    if keyword.text:
                        keywords.append(keyword.text)
            
            # MeSH terms
            mesh_terms = []
            mesh_list = article_element.find('.//MeshHeadingList')
            if mesh_list is not None:
                for mesh in mesh_list.findall('.//MeshHeading'):
                    descriptor = mesh.find('.//DescriptorName')
                    if descriptor is not None and descriptor.text:
                        mesh_terms.append(descriptor.text)
            
            return {
                'pmid': pmid_text,
                'title': title_text,
                'abstract': abstract_text,
                'authors': authors,
                'journal': journal_text,
                'publication_date': pub_date,
                'doi': doi_text,
                'keywords': keywords,
                'mesh_terms': mesh_terms,
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting article data: {str(e)}")
            return None
    
    def _extract_publication_date(self, article_element) -> str:
        """Extract publication date from article element"""
        try:
            pub_date = article_element.find('.//PubDate')
            if pub_date is not None:
                year = pub_date.find('.//Year')
                month = pub_date.find('.//Month')
                day = pub_date.find('.//Day')
                
                year_text = year.text if year is not None else "N/A"
                month_text = month.text if month is not None else "01"
                day_text = day.text if day is not None else "01"
                
                return f"{year_text}-{month_text.zfill(2)}-{day_text.zfill(2)}"
        except Exception as e:
            logger.error(f"Error extracting publication date: {str(e)}")
        
        return "N/A"