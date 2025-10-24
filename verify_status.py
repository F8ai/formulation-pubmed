#!/usr/bin/env python3
"""
Simple verification script for the microservice status
"""

import os
import json
import asyncio
from pathlib import Path

async def verify_articles():
    """Verify the articles and their processing status"""
    print("🔍 Verifying PubMed articles...")
    
    articles_dir = Path("pubmed/articles")
    if not articles_dir.exists():
        print("❌ Articles directory not found")
        return
    
    articles = []
    for pmid_dir in articles_dir.iterdir():
        if pmid_dir.is_dir():
            metadata_file = pmid_dir / "metadata" / "article.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        article_data = json.load(f)
                    articles.append(article_data)
                except Exception as e:
                    print(f"⚠️ Error reading {metadata_file}: {e}")
    
    print(f"✅ Found {len(articles)} articles")
    
    # Show article details
    for i, article in enumerate(articles, 1):
        print(f"\n📄 Article {i}:")
        print(f"   PMID: {article.get('pmid', 'N/A')}")
        print(f"   Title: {article.get('title', 'N/A')[:80]}...")
        print(f"   Journal: {article.get('journal', 'N/A')}")
        print(f"   Stage: {article.get('processing_stage', 'N/A')}")
        print(f"   Relevance: {article.get('relevance_score', 0):.2f}")
    
    # Check processing stages
    stages = {}
    for article in articles:
        stage = article.get('processing_stage', 'unknown')
        stages[stage] = stages.get(stage, 0) + 1
    
    print(f"\n📊 Processing Stages:")
    for stage, count in stages.items():
        print(f"   {stage}: {count} articles")
    
    # Check for abstracts
    abstract_count = 0
    for pmid_dir in articles_dir.iterdir():
        if pmid_dir.is_dir():
            abstract_file = pmid_dir / "abstract" / "content.txt"
            if abstract_file.exists():
                abstract_count += 1
    
    print(f"\n📝 Abstracts available: {abstract_count}")
    
    # Check for full text
    fulltext_count = 0
    for pmid_dir in articles_dir.iterdir():
        if pmid_dir.is_dir():
            fulltext_file = pmid_dir / "fulltext" / "content.txt"
            if fulltext_file.exists():
                fulltext_count += 1
    
    print(f"📄 Full text available: {fulltext_count}")
    
    return len(articles)

async def verify_status_page():
    """Verify the status page content"""
    print("\n📊 Verifying status page...")
    
    status_file = Path("docs/articles/index.html")
    if not status_file.exists():
        print("❌ Status page not found")
        return
    
    with open(status_file, 'r') as f:
        content = f.read()
    
    # Check for key metrics
    if "Total Articles" in content:
        print("✅ Status page contains 'Total Articles'")
    
    if "Recent Articles" in content:
        print("✅ Status page contains 'Recent Articles'")
    
    # Extract the total articles count
    import re
    match = re.search(r'<div class="number">(\d+)</div>', content)
    if match:
        total_count = int(match.group(1))
        print(f"✅ Status page shows {total_count} total articles")
    else:
        print("⚠️ Could not find total articles count in status page")

async def verify_data_files():
    """Verify the data files in docs"""
    print("\n📁 Verifying data files...")
    
    docs_data_dir = Path("docs/pubmed/data/articles")
    if not docs_data_dir.exists():
        print("❌ Docs data directory not found")
        return
    
    json_files = list(docs_data_dir.rglob("*.json"))
    print(f"✅ Found {len(json_files)} JSON files in docs")
    
    txt_files = list(docs_data_dir.rglob("*.txt"))
    print(f"✅ Found {len(txt_files)} text files in docs")
    
    # Check specific article
    article_39781554 = docs_data_dir / "39781554"
    if article_39781554.exists():
        print("✅ Article 39781554 data available in docs")
        
        metadata_file = article_39781554 / "metadata" / "article.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            print(f"   Title: {data.get('title', 'N/A')[:60]}...")
            print(f"   Stage: {data.get('processing_stage', 'N/A')}")

async def main():
    """Run all verifications"""
    print("🚀 Formulation PubMed Microservice - Status Verification")
    print("=" * 60)
    
    # Verify articles
    article_count = await verify_articles()
    
    # Verify status page
    await verify_status_page()
    
    # Verify data files
    await verify_data_files()
    
    print("\n" + "=" * 60)
    print("✅ Verification complete!")
    print(f"📊 Summary: {article_count} articles found and processed")
    print("🌐 GitHub Pages: https://f8ai.github.io/formulation-pubmed/")
    print("📁 Data Browser: https://f8ai.github.io/formulation-pubmed/pubmed/")

if __name__ == "__main__":
    asyncio.run(main())