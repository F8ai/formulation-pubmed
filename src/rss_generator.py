"""
RSS Feed Generator Module

Generates RSS feeds for newly discovered and processed articles.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import asyncio

from .git_manager import GitManager

logger = logging.getLogger(__name__)

class RSSGenerator:
    """Generates RSS feeds for articles"""
    
    def __init__(self, data_dir: str = "pubmed", docs_dir: str = "docs", git_manager: Optional[GitManager] = None):
        self.data_dir = data_dir
        self.docs_dir = docs_dir
        self.articles_dir = os.path.join(data_dir, "articles")
        self.rss_dir = os.path.join(docs_dir, "rss")
        self.git_manager = git_manager or GitManager()
        
        # Ensure RSS directory exists
        os.makedirs(self.rss_dir, exist_ok=True)
    
    async def generate_rss_feeds(self, commit_to_git: bool = True) -> List[str]:
        """Generate all RSS feeds and optionally commit to Git"""
        try:
            feeds = []
            
            # Generate main RSS feed
            main_feed = await self._generate_main_feed()
            if main_feed:
                feeds.append(main_feed)
            
            # Generate category-specific feeds
            category_feeds = await self._generate_category_feeds()
            feeds.extend(category_feeds)
            
            # Generate daily feed
            daily_feed = await self._generate_daily_feed()
            if daily_feed:
                feeds.append(daily_feed)
            
            # Generate RSS index
            index_feed = await self.generate_rss_index()
            if index_feed:
                feeds.append(index_feed)
            
            # Commit to Git if requested
            if commit_to_git and feeds:
                await self._commit_rss_feeds(feeds)
            
            logger.info(f"Generated {len(feeds)} RSS feeds")
            return feeds
            
        except Exception as e:
            logger.error(f"Error generating RSS feeds: {str(e)}")
            return []
    
    async def _generate_main_feed(self) -> Optional[str]:
        """Generate main RSS feed with all articles"""
        try:
            # Get recent articles (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            articles = await self._get_recent_articles(cutoff_date)
            
            if not articles:
                return None
            
            # Create RSS feed
            rss = self._create_rss_structure(
                title="Formulation PubMed Research Feed",
                description="Latest cannabis formulation research articles from PubMed",
                link="https://f8ai.github.io/formulation-pubmed/",
                language="en-us"
            )
            
            # Add articles to feed
            for article in articles:
                self._add_article_to_rss(rss, article)
            
            # Save RSS feed
            rss_path = os.path.join(self.rss_dir, "feed.xml")
            self._save_rss_feed(rss, rss_path)
            
            logger.info(f"Generated main RSS feed with {len(articles)} articles")
            return rss_path
            
        except Exception as e:
            logger.error(f"Error generating main RSS feed: {str(e)}")
            return None
    
    async def _generate_category_feeds(self) -> List[str]:
        """Generate category-specific RSS feeds"""
        try:
            feeds = []
            categories = [
                'cannabis_formulation',
                'extraction_methods',
                'terpenes',
                'cannabinoids',
                'pharmaceutical_formulation',
                'stability_testing',
                'analytical_methods',
                'regulatory'
            ]
            
            for category in categories:
                # Get articles for this category
                articles = await self._get_articles_by_category(category)
                
                if not articles:
                    continue
                
                # Create category RSS feed
                rss = self._create_rss_structure(
                    title=f"Formulation PubMed - {category.replace('_', ' ').title()}",
                    description=f"Latest {category.replace('_', ' ')} research articles",
                    link=f"https://f8ai.github.io/formulation-pubmed/rss/{category}.xml",
                    language="en-us"
                )
                
                # Add articles to feed
                for article in articles:
                    self._add_article_to_rss(rss, article)
                
                # Save category RSS feed
                rss_path = os.path.join(self.rss_dir, f"{category}.xml")
                self._save_rss_feed(rss, rss_path)
                feeds.append(rss_path)
                
                logger.info(f"Generated {category} RSS feed with {len(articles)} articles")
            
            return feeds
            
        except Exception as e:
            logger.error(f"Error generating category feeds: {str(e)}")
            return []
    
    async def _generate_daily_feed(self) -> Optional[str]:
        """Generate daily RSS feed with today's articles"""
        try:
            # Get today's articles
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            articles = await self._get_recent_articles(today)
            
            if not articles:
                return None
            
            # Create daily RSS feed
            rss = self._create_rss_structure(
                title=f"Formulation PubMed - Daily Feed ({today.strftime('%Y-%m-%d')})",
                description=f"Articles discovered on {today.strftime('%B %d, %Y')}",
                link="https://f8ai.github.io/formulation-pubmed/rss/daily.xml",
                language="en-us"
            )
            
            # Add articles to feed
            for article in articles:
                self._add_article_to_rss(rss, article)
            
            # Save daily RSS feed
            rss_path = os.path.join(self.rss_dir, "daily.xml")
            self._save_rss_feed(rss, rss_path)
            
            logger.info(f"Generated daily RSS feed with {len(articles)} articles")
            return rss_path
            
        except Exception as e:
            logger.error(f"Error generating daily RSS feed: {str(e)}")
            return None
    
    async def _get_recent_articles(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get articles discovered after cutoff date"""
        articles = []
        
        try:
            if not os.path.exists(self.articles_dir):
                return articles
            
            for pmid_dir in os.listdir(self.articles_dir):
                pmid_path = os.path.join(self.articles_dir, pmid_dir)
                if not os.path.isdir(pmid_path):
                    continue
                
                # Load article metadata
                article_data = await self._load_article_metadata(pmid_path)
                if not article_data:
                    continue
                
                # Check if article is recent enough
                processed_at = article_data.get('processed_at', '')
                if processed_at:
                    try:
                        article_date = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                        if article_date >= cutoff_date:
                            articles.append(article_data)
                    except ValueError:
                        continue
            
            # Sort by processing date (newest first)
            articles.sort(key=lambda x: x.get('processed_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting recent articles: {str(e)}")
        
        return articles
    
    async def _get_articles_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get articles by category"""
        articles = []
        
        try:
            if not os.path.exists(self.articles_dir):
                return articles
            
            for pmid_dir in os.listdir(self.articles_dir):
                pmid_path = os.path.join(self.articles_dir, pmid_dir)
                if not os.path.isdir(pmid_path):
                    continue
                
                # Load article metadata
                article_data = await self._load_article_metadata(pmid_path)
                if not article_data:
                    continue
                
                # Check if article belongs to category
                if article_data.get('category') == category:
                    articles.append(article_data)
            
            # Sort by processing date (newest first)
            articles.sort(key=lambda x: x.get('processed_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting articles by category {category}: {str(e)}")
        
        return articles
    
    async def _load_article_metadata(self, pmid_path: str) -> Optional[Dict[str, Any]]:
        """Load article metadata from PMID directory"""
        try:
            metadata_path = os.path.join(pmid_path, "metadata", "article.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading article metadata: {str(e)}")
        
        return None
    
    def _create_rss_structure(self, title: str, description: str, link: str, language: str) -> Element:
        """Create basic RSS structure"""
        rss = Element('rss')
        rss.set('version', '2.0')
        rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
        
        channel = SubElement(rss, 'channel')
        
        # Basic channel info
        SubElement(channel, 'title').text = title
        SubElement(channel, 'description').text = description
        SubElement(channel, 'link').text = link
        SubElement(channel, 'language').text = language
        SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        SubElement(channel, 'generator').text = 'Formulation PubMed Scraper'
        
        # Add atom:link for self-reference
        atom_link = SubElement(channel, 'atom:link')
        atom_link.set('href', link)
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')
        
        return rss
    
    def _add_article_to_rss(self, rss: Element, article: Dict[str, Any]):
        """Add article to RSS feed"""
        channel = rss.find('channel')
        
        item = SubElement(channel, 'item')
        
        # Title
        title = SubElement(item, 'title')
        title.text = article.get('title', 'Untitled')
        
        # Link
        link = SubElement(item, 'link')
        link.text = article.get('url', f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/")
        
        # Description
        description = SubElement(item, 'description')
        abstract = article.get('abstract', '')
        if len(abstract) > 500:
            abstract = abstract[:500] + '...'
        description.text = abstract
        
        # GUID
        guid = SubElement(item, 'guid')
        guid.text = f"pmid:{article.get('pmid', '')}"
        guid.set('isPermaLink', 'false')
        
        # Publication date
        pub_date = SubElement(item, 'pubDate')
        processed_at = article.get('processed_at', '')
        if processed_at:
            try:
                article_date = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                pub_date.text = article_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            except ValueError:
                pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Author
        authors = article.get('authors', [])
        if authors:
            author = SubElement(item, 'author')
            author.text = authors[0] if len(authors) == 1 else f"{authors[0]} et al."
        
        # Category
        category = article.get('category', '')
        if category:
            cat = SubElement(item, 'category')
            cat.text = category.replace('_', ' ').title()
        
        # Relevance score
        relevance_score = article.get('relevance_score', 0.0)
        if relevance_score > 0:
            relevance = SubElement(item, 'relevanceScore')
            relevance.text = str(relevance_score)
    
    def _save_rss_feed(self, rss: Element, file_path: str):
        """Save RSS feed to file"""
        try:
            # Convert to pretty XML
            rough_string = tostring(rss, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Remove empty lines
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(lines)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"Saved RSS feed: {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving RSS feed {file_path}: {str(e)}")
    
    async def generate_rss_index(self) -> str:
        """Generate RSS index page"""
        try:
            rss_files = []
            if os.path.exists(self.rss_dir):
                for file in os.listdir(self.rss_dir):
                    if file.endswith('.xml'):
                        rss_files.append(file)
            
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulation PubMed RSS Feeds</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .feed-list {{
            list-style: none;
            padding: 0;
        }}
        .feed-item {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }}
        .feed-item h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .feed-item p {{
            margin: 0 0 10px 0;
            color: #666;
        }}
        .feed-item a {{
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }}
        .feed-item a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Formulation PubMed RSS Feeds</h1>
        <ul class="feed-list">
            <li class="feed-item">
                <h3>Main Feed</h3>
                <p>All recent articles from the formulation PubMed scraper</p>
                <a href="feed.xml">Subscribe to Main Feed</a>
            </li>
            <li class="feed-item">
                <h3>Daily Feed</h3>
                <p>Articles discovered today</p>
                <a href="daily.xml">Subscribe to Daily Feed</a>
            </li>
            <li class="feed-item">
                <h3>Category Feeds</h3>
                <p>Specialized feeds for different research categories</p>
                <ul>
                    <li><a href="cannabis_formulation.xml">Cannabis Formulation</a></li>
                    <li><a href="extraction_methods.xml">Extraction Methods</a></li>
                    <li><a href="terpenes.xml">Terpenes</a></li>
                    <li><a href="cannabinoids.xml">Cannabinoids</a></li>
                    <li><a href="pharmaceutical_formulation.xml">Pharmaceutical Formulation</a></li>
                    <li><a href="stability_testing.xml">Stability Testing</a></li>
                    <li><a href="analytical_methods.xml">Analytical Methods</a></li>
                    <li><a href="regulatory.xml">Regulatory</a></li>
                </ul>
            </li>
        </ul>
        <p style="text-align: center; color: #666; margin-top: 30px;">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
"""
            
            # Save RSS index
            index_path = os.path.join(self.rss_dir, "index.html")
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"Generated RSS index: {index_path}")
            return index_path
            
        except Exception as e:
            logger.error(f"Error generating RSS index: {str(e)}")
            return ""
    
    async def _commit_rss_feeds(self, feeds: List[str]):
        """Commit RSS feeds to Git"""
        try:
            # Count total articles in feeds
            total_articles = 0
            for feed_path in feeds:
                if os.path.exists(feed_path):
                    # Count items in RSS feed (rough estimate)
                    with open(feed_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Count <item> tags
                        total_articles += content.count('<item>')
            
            # Create commit message
            commit_message = f"Update RSS feeds - {total_articles} articles across {len(feeds)} feeds - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Commit and push
            success = await self.git_manager.force_commit_and_push(commit_message)
            
            if success:
                logger.info(f"Successfully committed {len(feeds)} RSS feeds to GitHub")
            else:
                logger.warning("Failed to commit RSS feeds to GitHub")
                
        except Exception as e:
            logger.error(f"Error committing RSS feeds: {str(e)}")
    
    async def generate_single_feed(self, feed_type: str, commit_to_git: bool = True) -> Optional[str]:
        """Generate a single RSS feed type"""
        try:
            feed_path = None
            
            if feed_type == "main":
                feed_path = await self._generate_main_feed()
            elif feed_type == "daily":
                feed_path = await self._generate_daily_feed()
            elif feed_type in ["cannabis_formulation", "extraction_methods", "terpenes", 
                             "cannabinoids", "pharmaceutical_formulation", "stability_testing", 
                             "analytical_methods", "regulatory"]:
                articles = await self._get_articles_by_category(feed_type)
                if articles:
                    rss = self._create_rss_structure(
                        title=f"Formulation PubMed - {feed_type.replace('_', ' ').title()}",
                        description=f"Latest {feed_type.replace('_', ' ')} research articles",
                        link=f"https://f8ai.github.io/formulation-pubmed/rss/{feed_type}.xml",
                        language="en-us"
                    )
                    
                    for article in articles:
                        self._add_article_to_rss(rss, article)
                    
                    feed_path = os.path.join(self.rss_dir, f"{feed_type}.xml")
                    self._save_rss_feed(rss, feed_path)
            
            # Commit to Git if requested and feed was generated
            if commit_to_git and feed_path:
                await self._commit_rss_feeds([feed_path])
            
            return feed_path
            
        except Exception as e:
            logger.error(f"Error generating single feed {feed_type}: {str(e)}")
            return None