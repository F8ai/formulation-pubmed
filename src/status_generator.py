"""
Status Generator Module

Generates status pages and metrics for the PubMed scraper microservice.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class StatusGenerator:
    """Generates status pages and metrics"""
    
    def __init__(self, data_dir: str = "pubmed", docs_dir: str = "docs"):
        self.data_dir = data_dir
        self.docs_dir = docs_dir
        self.articles_dir = os.path.join(data_dir, "articles")
        self.index_dir = os.path.join(data_dir, "index")
        
    async def generate_status_page(self) -> str:
        """Generate the main status page HTML"""
        try:
            # Get metrics
            metrics = await self._get_metrics()
            
            # Generate HTML
            html = self._create_status_html(metrics)
            
            # Save to docs/articles/index.html
            status_path = os.path.join(self.docs_dir, "articles", "index.html")
            os.makedirs(os.path.dirname(status_path), exist_ok=True)
            
            with open(status_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"Generated status page: {status_path}")
            return status_path
            
        except Exception as e:
            logger.error(f"Error generating status page: {str(e)}")
            return ""
    
    async def _get_metrics(self) -> Dict[str, Any]:
        """Collect metrics from the data directory"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_pmids': 0,
            'stages': {
                'metadata': 0,
                'abstract': 0,
                'fulltext': 0,
                'ocr': 0,
                'complete': 0
            },
            'sources': {
                'pubmed_central': 0,
                'arxiv': 0,
                'sci_hub': 0,
                'direct_pdf': 0
            },
            'categories': {},
            'recent_articles': [],
            'processing_stats': {
                'avg_relevance_score': 0.0,
                'total_text_length': 0,
                'avg_text_length': 0
            },
            'daily_stats': []
        }
        
        try:
            # Count PMIDs and stages
            if os.path.exists(self.articles_dir):
                for pmid_dir in os.listdir(self.articles_dir):
                    pmid_path = os.path.join(self.articles_dir, pmid_dir)
                    if os.path.isdir(pmid_path):
                        metrics['total_pmids'] += 1
                        
                        # Check processing stage
                        stage = await self._get_processing_stage(pmid_path)
                        if stage in metrics['stages']:
                            metrics['stages'][stage] += 1
                        
                        # Get article details
                        article_data = await self._get_article_data(pmid_path)
                        if article_data:
                            # Count sources
                            source = article_data.get('fulltext_source', 'unknown')
                            if source in metrics['sources']:
                                metrics['sources'][source] += 1
                            
                            # Count categories
                            category = article_data.get('category', 'unknown')
                            metrics['categories'][category] = metrics['categories'].get(category, 0) + 1
                            
                            # Add to recent articles
                            if len(metrics['recent_articles']) < 10:
                                metrics['recent_articles'].append({
                                    'pmid': pmid_dir,
                                    'title': article_data.get('title', '')[:100] + '...',
                                    'journal': article_data.get('journal', ''),
                                    'date': article_data.get('publication_date', ''),
                                    'stage': stage,
                                    'relevance_score': article_data.get('relevance_score', 0.0)
                                })
                            
                            # Processing stats
                            relevance_score = article_data.get('relevance_score', 0.0)
                            text_length = article_data.get('text_length', 0)
                            
                            metrics['processing_stats']['total_text_length'] += text_length
                            if relevance_score > 0:
                                current_avg = metrics['processing_stats']['avg_relevance_score']
                                count = sum(1 for stage in metrics['stages'].values() if stage > 0)
                                metrics['processing_stats']['avg_relevance_score'] = (current_avg + relevance_score) / 2
            
            # Calculate averages
            if metrics['total_pmids'] > 0:
                metrics['processing_stats']['avg_text_length'] = (
                    metrics['processing_stats']['total_text_length'] / metrics['total_pmids']
                )
            
            # Get daily stats
            metrics['daily_stats'] = await self._get_daily_stats()
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
        
        return metrics
    
    async def _get_processing_stage(self, pmid_path: str) -> str:
        """Determine the processing stage of an article"""
        try:
            metadata_path = os.path.join(pmid_path, "metadata", "article.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                return metadata.get('processing_stage', 'metadata')
            
            # Check for files to determine stage
            if os.path.exists(os.path.join(pmid_path, "ocr", "rag_chunks.json")):
                return 'complete'
            elif os.path.exists(os.path.join(pmid_path, "fulltext", "content.txt")):
                return 'fulltext'
            elif os.path.exists(os.path.join(pmid_path, "abstract", "content.txt")):
                return 'abstract'
            else:
                return 'metadata'
                
        except Exception as e:
            logger.error(f"Error determining processing stage: {str(e)}")
            return 'metadata'
    
    async def _get_article_data(self, pmid_path: str) -> Optional[Dict[str, Any]]:
        """Get article data from PMID directory"""
        try:
            metadata_path = os.path.join(pmid_path, "metadata", "article.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading article data: {str(e)}")
        
        return None
    
    async def _get_daily_stats(self) -> List[Dict[str, Any]]:
        """Get daily processing statistics"""
        daily_stats = []
        
        try:
            # Get last 7 days
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                # Count articles processed on this date
                count = 0
                if os.path.exists(self.articles_dir):
                    for pmid_dir in os.listdir(self.articles_dir):
                        pmid_path = os.path.join(self.articles_dir, pmid_dir)
                        if os.path.isdir(pmid_path):
                            metadata_path = os.path.join(pmid_path, "metadata", "article.json")
                            if os.path.exists(metadata_path):
                                try:
                                    with open(metadata_path, 'r') as f:
                                        metadata = json.load(f)
                                    processed_at = metadata.get('processed_at', '')
                                    if date_str in processed_at:
                                        count += 1
                                except:
                                    continue
                
                daily_stats.append({
                    'date': date_str,
                    'count': count
                })
        
        except Exception as e:
            logger.error(f"Error getting daily stats: {str(e)}")
        
        return daily_stats
    
    def _create_status_html(self, metrics: Dict[str, Any]) -> str:
        """Create HTML status page"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulation PubMed Scraper Status</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .stat-card .subtitle {{
            color: #666;
            font-size: 0.9em;
        }}
        .section {{
            margin: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .section h2 {{
            margin: 0 0 20px 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            transition: width 0.3s ease;
        }}
        .recent-articles {{
            display: grid;
            gap: 15px;
        }}
        .article-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #28a745;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .article-title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .article-meta {{
            font-size: 0.9em;
            color: #666;
        }}
        .stage-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .stage-metadata {{ background: #ffc107; color: #000; }}
        .stage-abstract {{ background: #17a2b8; color: white; }}
        .stage-fulltext {{ background: #fd7e14; color: white; }}
        .stage-ocr {{ background: #6f42c1; color: white; }}
        .stage-complete {{ background: #28a745; color: white; }}
        .timestamp {{
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
            padding: 20px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Formulation PubMed Scraper</h1>
            <p>Real-time status and metrics for cannabis formulation research articles</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Articles</h3>
                <div class="number">{metrics['total_pmids']}</div>
                <div class="subtitle">PMID processed</div>
            </div>
            
            <div class="stat-card">
                <h3>Complete Articles</h3>
                <div class="number">{metrics['stages']['complete']}</div>
                <div class="subtitle">Full processing</div>
            </div>
            
            <div class="stat-card">
                <h3>Full Text Available</h3>
                <div class="number">{metrics['stages']['fulltext'] + metrics['stages']['ocr'] + metrics['stages']['complete']}</div>
                <div class="subtitle">With full text</div>
            </div>
            
            <div class="stat-card">
                <h3>Avg Relevance</h3>
                <div class="number">{metrics['processing_stats']['avg_relevance_score']:.2f}</div>
                <div class="subtitle">Relevance score</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Processing Pipeline Status</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <h4>Metadata ({metrics['stages']['metadata']})</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(metrics['stages']['metadata'] / max(metrics['total_pmids'], 1)) * 100}%"></div>
                    </div>
                </div>
                <div>
                    <h4>Abstract ({metrics['stages']['abstract']})</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(metrics['stages']['abstract'] / max(metrics['total_pmids'], 1)) * 100}%"></div>
                    </div>
                </div>
                <div>
                    <h4>Full Text ({metrics['stages']['fulltext']})</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(metrics['stages']['fulltext'] / max(metrics['total_pmids'], 1)) * 100}%"></div>
                    </div>
                </div>
                <div>
                    <h4>OCR/RAG ({metrics['stages']['ocr'] + metrics['stages']['complete']})</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {((metrics['stages']['ocr'] + metrics['stages']['complete']) / max(metrics['total_pmids'], 1)) * 100}%"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Data Sources</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                <div class="stat-card">
                    <h3>PubMed Central</h3>
                    <div class="number">{metrics['sources']['pubmed_central']}</div>
                </div>
                <div class="stat-card">
                    <h3>arXiv</h3>
                    <div class="number">{metrics['sources']['arxiv']}</div>
                </div>
                <div class="stat-card">
                    <h3>Sci-Hub</h3>
                    <div class="number">{metrics['sources']['sci_hub']}</div>
                </div>
                <div class="stat-card">
                    <h3>Direct PDF</h3>
                    <div class="number">{metrics['sources']['direct_pdf']}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Articles</h2>
            <div class="recent-articles">
                {self._format_recent_articles(metrics['recent_articles'])}
            </div>
        </div>
        
        <div class="timestamp">
            Last updated: {metrics['timestamp']}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => {{
            location.reload();
        }}, 30000);
    </script>
</body>
</html>
"""
    
    def _format_recent_articles(self, articles: List[Dict[str, Any]]) -> str:
        """Format recent articles for HTML"""
        if not articles:
            return "<p>No articles processed yet.</p>"
        
        html = ""
        for article in articles:
            stage_class = f"stage-{article['stage']}"
            html += f"""
            <div class="article-item">
                <div class="article-title">{article['title']}</div>
                <div class="article-meta">
                    PMID: {article['pmid']} | {article['journal']} | {article['date']}
                    <span class="stage-badge {stage_class}">{article['stage']}</span>
                    <span style="float: right;">Score: {article['relevance_score']:.2f}</span>
                </div>
            </div>
            """
        
        return html