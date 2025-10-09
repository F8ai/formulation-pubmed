# Formulation PubMed Microservice

A comprehensive microservice for automatically discovering, processing, and publishing cannabis formulation research articles from PubMed.

## 🚀 Features

- **Automated PubMed Search**: Continuously searches for cannabis formulation articles
- **Multi-Stage Processing Pipeline**: Metadata → Abstract → Full-text → OCR → RAG
- **Real-time RSS Feeds**: Auto-generated feeds for different research categories
- **Status Dashboard**: Live monitoring of processing pipeline and metrics
- **Cloud Storage**: S3 integration with DVC for data versioning
- **Automated Git Commits**: Automatic commits and pushes to GitHub
- **Docker Ready**: Containerized for easy deployment

## 📊 Current Status

The microservice is **actively running** and has already discovered:
- **4 real PubMed articles** with cannabis formulation research
- **Automated processing pipeline** working
- **RSS feeds generated** and updating
- **Status dashboard** live and monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PubMed API    │───▶│  Background      │───▶│   Data Storage  │
│   (Entrez)      │    │  Processor       │    │   (S3 + Local)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Outputs        │
                       │ • RSS Feeds      │
                       │ • Status Page    │
                       │ • Git Commits    │
                       └──────────────────┘
```

## 🛠️ Setup & Deployment

### Prerequisites
- Python 3.11+
- AWS S3 bucket (`f8ai-data`)
- GitHub repository access

### Local Development
```bash
# Clone repository
git clone https://github.com/f8ai/formulation-pubmed.git
cd formulation-pubmed

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_local.py

# Start microservice
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### AWS App Runner Deployment

1. **Create S3 Bucket**:
   - Bucket name: `f8ai-data`
   - Region: `us-east-1` (or your preferred region)
   - Public access: Blocked
   - Versioning: Enabled

2. **Deploy to App Runner**:
   - Use the provided `apprunner.yaml` configuration
   - Connect to GitHub repository
   - Set environment variables:
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `AWS_DEFAULT_REGION`

3. **Monitor Deployment**:
   - Health check: `https://your-app-url/health`
   - Status: `https://your-app-url/status`
   - API docs: `https://your-app-url/docs`

## 📁 Data Structure

```
pubmed/
├── articles/
│   └── {PMID}/
│       ├── metadata/
│       │   └── article.json
│       ├── abstract/
│       │   └── content.txt
│       ├── fulltext/
│       │   └── content.txt
│       ├── pdf/
│       │   └── article.pdf
│       ├── ocr/
│       │   └── extracted_text.txt
│       ├── images/
│       └── references/
│           └── references.json
├── search_results/
└── index/
```

## 🔍 Search Terms

The microservice searches for articles using these categories:

- **Cannabis Formulation**: Core formulation research
- **Extraction Methods**: CO2, ethanol, solvent extraction
- **Terpenes**: Terpene analysis and formulation
- **Cannabinoids**: THC, CBD, CBG formulation
- **Pharmaceutical Formulation**: Drug delivery systems
- **Stability Testing**: Shelf life and stability studies
- **Analytical Methods**: HPLC, GC-MS, testing methods
- **Regulatory**: FDA, compliance, quality control

## 📈 Monitoring

### Status Dashboard
- **URL**: `https://f8ai.github.io/formulation-pubmed/articles/`
- **Updates**: Every 30 minutes
- **Metrics**: Article counts, processing stages, relevance scores

### RSS Feeds
- **Main Feed**: `https://f8ai.github.io/formulation-pubmed/rss/feed.xml`
- **Daily Feed**: `https://f8ai.github.io/formulation-pubmed/rss/daily.xml`
- **Category Feeds**: Individual feeds for each research category

### API Endpoints
- `GET /health` - Service health check
- `GET /status` - Processing pipeline status
- `GET /docs` - Interactive API documentation

## 🔧 Configuration

Edit `data/pubmed.json` to customize:
- Search terms and parameters
- Processing intervals
- Output formats
- S3 storage settings

## 📊 Sample Data

The microservice has already discovered real articles like:

**"Predictors of Response to Medical Cannabis for Chronic Pain"**
- PMID: 39781554
- Journal: Cannabis (Albuquerque, N.M.)
- Authors: Giangregorio, Aidan; Wang, Li; et al.
- DOI: 10.26828/cannabis/2024/000259
- Relevance Score: 0.34

## 🚀 Deployment Commands

```bash
# Push to GitHub
git remote add origin https://github.com/f8ai/formulation-pubmed.git
git push -u origin main

# Deploy to AWS App Runner
# Use the AWS Console or CLI with apprunner.yaml

# Monitor deployment
curl https://your-app-url/health
curl https://your-app-url/status
```

## 📝 License

This project is part of the F8AI formulation research initiative.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues or questions, please open an issue on GitHub or contact the F8AI team.

---

**Status**: ✅ **LIVE** - Microservice is running and processing articles  
**Last Updated**: 2025-10-09  
**Articles Processed**: 4+ real PubMed articles  
**Next Update**: Continuous (every 6 hours for RSS, 30 minutes for status)