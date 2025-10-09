"""
Data Processor Module

Processes and enriches scraped PubMed articles for formulation research.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and enriches PubMed article data"""
    
    def __init__(self):
        self.formulation_keywords = [
            'formulation', 'extract', 'extraction', 'cannabinoid', 'terpene',
            'stability', 'bioavailability', 'dosage', 'delivery', 'pharmaceutical',
            'purification', 'distillation', 'concentration', 'potency'
        ]
        
        self.cannabis_terms = [
            'cannabis', 'marijuana', 'hemp', 'cbd', 'thc', 'cannabinoid',
            'terpene', 'myrcene', 'limonene', 'pinene', 'linalool'
        ]
    
    def process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of articles and add enrichment data
        
        Args:
            articles: List of raw article dictionaries
            
        Returns:
            List of processed article dictionaries
        """
        processed_articles = []
        
        for article in articles:
            try:
                processed_article = self._process_single_article(article)
                if processed_article:
                    processed_articles.append(processed_article)
            except Exception as e:
                logger.error(f"Error processing article {article.get('pmid', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Processed {len(processed_articles)} out of {len(articles)} articles")
        return processed_articles
    
    def _process_single_article(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single article and add enrichment data"""
        try:
            # Create a copy of the original article
            processed = article.copy()
            
            # Add enrichment data
            processed['relevance_score'] = self._calculate_relevance_score(article)
            processed['formulation_relevance'] = self._assess_formulation_relevance(article)
            processed['cannabis_relevance'] = self._assess_cannabis_relevance(article)
            processed['extracted_entities'] = self._extract_entities(article)
            processed['key_phrases'] = self._extract_key_phrases(article)
            processed['processing_timestamp'] = datetime.now().isoformat()
            
            # Filter out low-relevance articles
            if processed['relevance_score'] < 0.3:
                logger.debug(f"Filtering out low-relevance article: {article.get('pmid', 'unknown')}")
                return None
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            return None
    
    def _calculate_relevance_score(self, article: Dict[str, Any]) -> float:
        """Calculate relevance score based on content analysis"""
        score = 0.0
        
        # Title relevance (weight: 0.4)
        title = article.get('title', '').lower()
        title_score = self._calculate_text_relevance(title)
        score += title_score * 0.4
        
        # Abstract relevance (weight: 0.4)
        abstract = article.get('abstract', '').lower()
        abstract_score = self._calculate_text_relevance(abstract)
        score += abstract_score * 0.4
        
        # Keywords relevance (weight: 0.2)
        keywords = ' '.join(article.get('keywords', [])).lower()
        mesh_terms = ' '.join(article.get('mesh_terms', [])).lower()
        all_keywords = f"{keywords} {mesh_terms}"
        keyword_score = self._calculate_text_relevance(all_keywords)
        score += keyword_score * 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_text_relevance(self, text: str) -> float:
        """Calculate relevance score for a text string"""
        if not text:
            return 0.0
        
        # Count formulation-related terms
        formulation_count = sum(1 for keyword in self.formulation_keywords if keyword in text)
        
        # Count cannabis-related terms
        cannabis_count = sum(1 for term in self.cannabis_terms if term in text)
        
        # Calculate score based on term density
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        formulation_density = formulation_count / total_words
        cannabis_density = cannabis_count / total_words
        
        # Weighted score
        score = (formulation_density * 0.6) + (cannabis_density * 0.4)
        
        return min(score * 10, 1.0)  # Scale and cap at 1.0
    
    def _assess_formulation_relevance(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how relevant the article is to formulation research"""
        title = article.get('title', '').lower()
        abstract = article.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        formulation_indicators = {
            'extraction_methods': self._count_terms(text, [
                'extraction', 'co2', 'ethanol', 'hydrocarbon', 'distillation',
                'purification', 'supercritical', 'solvent'
            ]),
            'stability_testing': self._count_terms(text, [
                'stability', 'shelf life', 'degradation', 'storage', 'temperature',
                'humidity', 'oxidation'
            ]),
            'analytical_methods': self._count_terms(text, [
                'hplc', 'gc-ms', 'analysis', 'quantification', 'chromatography',
                'spectroscopy', 'mass spectrometry'
            ]),
            'pharmaceutical_aspects': self._count_terms(text, [
                'bioavailability', 'pharmacokinetics', 'dosage', 'delivery',
                'pharmaceutical', 'drug', 'therapeutic'
            ])
        }
        
        total_indicators = sum(formulation_indicators.values())
        
        return {
            'indicators': formulation_indicators,
            'total_indicators': total_indicators,
            'relevance_level': self._get_relevance_level(total_indicators)
        }
    
    def _assess_cannabis_relevance(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how relevant the article is to cannabis research"""
        title = article.get('title', '').lower()
        abstract = article.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        cannabis_indicators = {
            'cannabinoids': self._count_terms(text, [
                'thc', 'cbd', 'cbg', 'cbn', 'cannabinoid', 'cannabidiol',
                'tetrahydrocannabinol'
            ]),
            'terpenes': self._count_terms(text, [
                'terpene', 'myrcene', 'limonene', 'pinene', 'linalool',
                'caryophyllene', 'humulene'
            ]),
            'cannabis_plant': self._count_terms(text, [
                'cannabis', 'marijuana', 'hemp', 'cannabis sativa',
                'cannabis indica', 'cannabis ruderalis'
            ])
        }
        
        total_indicators = sum(cannabis_indicators.values())
        
        return {
            'indicators': cannabis_indicators,
            'total_indicators': total_indicators,
            'relevance_level': self._get_relevance_level(total_indicators)
        }
    
    def _extract_entities(self, article: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract relevant entities from the article"""
        title = article.get('title', '')
        abstract = article.get('abstract', '')
        text = f"{title} {abstract}"
        
        entities = {
            'cannabinoids': self._extract_cannabinoids(text),
            'terpenes': self._extract_terpenes(text),
            'extraction_methods': self._extract_extraction_methods(text),
            'analytical_methods': self._extract_analytical_methods(text),
            'dosage_forms': self._extract_dosage_forms(text)
        }
        
        return entities
    
    def _extract_cannabinoids(self, text: str) -> List[str]:
        """Extract cannabinoid mentions from text"""
        cannabinoids = [
            'THC', 'CBD', 'CBG', 'CBN', 'CBC', 'THCV', 'CBDV',
            'cannabidiol', 'tetrahydrocannabinol', 'cannabigerol',
            'cannabinol', 'cannabichromene'
        ]
        
        found = []
        for cannabinoid in cannabinoids:
            if cannabinoid.lower() in text.lower():
                found.append(cannabinoid)
        
        return found
    
    def _extract_terpenes(self, text: str) -> List[str]:
        """Extract terpene mentions from text"""
        terpenes = [
            'myrcene', 'limonene', 'pinene', 'linalool', 'caryophyllene',
            'humulene', 'terpinolene', 'ocimene', 'bisabolol'
        ]
        
        found = []
        for terpene in terpenes:
            if terpene.lower() in text.lower():
                found.append(terpene)
        
        return found
    
    def _extract_extraction_methods(self, text: str) -> List[str]:
        """Extract extraction method mentions from text"""
        methods = [
            'CO2 extraction', 'supercritical CO2', 'ethanol extraction',
            'hydrocarbon extraction', 'steam distillation', 'distillation',
            'purification', 'fractionation'
        ]
        
        found = []
        for method in methods:
            if method.lower() in text.lower():
                found.append(method)
        
        return found
    
    def _extract_analytical_methods(self, text: str) -> List[str]:
        """Extract analytical method mentions from text"""
        methods = [
            'HPLC', 'GC-MS', 'LC-MS', 'chromatography', 'spectroscopy',
            'mass spectrometry', 'NMR', 'UV-Vis', 'FTIR'
        ]
        
        found = []
        for method in methods:
            if method.lower() in text.lower():
                found.append(method)
        
        return found
    
    def _extract_dosage_forms(self, text: str) -> List[str]:
        """Extract dosage form mentions from text"""
        forms = [
            'capsule', 'tablet', 'oil', 'tincture', 'topical', 'cream',
            'ointment', 'patch', 'inhalation', 'vaporizer'
        ]
        
        found = []
        for form in forms:
            if form.lower() in text.lower():
                found.append(form)
        
        return found
    
    def _extract_key_phrases(self, article: Dict[str, Any]) -> List[str]:
        """Extract key phrases from the article"""
        title = article.get('title', '')
        abstract = article.get('abstract', '')
        
        # Simple key phrase extraction based on common patterns
        phrases = []
        
        # Look for formulation-related phrases
        formulation_patterns = [
            r'cannabis\s+formulation',
            r'cannabinoid\s+extraction',
            r'terpene\s+profile',
            r'stability\s+testing',
            r'bioavailability\s+study',
            r'pharmaceutical\s+formulation'
        ]
        
        text = f"{title} {abstract}".lower()
        for pattern in formulation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phrases.extend(matches)
        
        return list(set(phrases))  # Remove duplicates
    
    def _count_terms(self, text: str, terms: List[str]) -> int:
        """Count occurrences of terms in text"""
        count = 0
        text_lower = text.lower()
        for term in terms:
            count += text_lower.count(term.lower())
        return count
    
    def _get_relevance_level(self, indicator_count: int) -> str:
        """Get relevance level based on indicator count"""
        if indicator_count >= 5:
            return "high"
        elif indicator_count >= 2:
            return "medium"
        else:
            return "low"