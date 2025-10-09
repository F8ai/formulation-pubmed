# Formulation PubMed Microservice Setup

## GitHub Repository Setup

1. Go to https://github.com/f8ai
2. Click "New repository"
3. Name it `formulation-pubmed`
4. Make it public
5. Don't initialize with README (we already have content)
6. Click "Create repository"

## Push Code to GitHub

After creating the repository, run these commands:

```bash
# Add the remote origin
git remote add origin https://github.com/f8ai/formulation-pubmed.git

# Push the code
git push -u origin main
```

## Deploy to AWS App Runner

1. Go to AWS App Runner console
2. Create a new service
3. Choose "Source code repository"
4. Connect to GitHub and select `f8ai/formulation-pubmed`
5. Use the `apprunner.yaml` configuration
6. Deploy the service

## Verify Deployment

Once deployed, you can:

1. **Check Health**: `https://your-app-runner-url/health`
2. **View Status**: `https://your-app-runner-url/status`
3. **View API Docs**: `https://your-app-runner-url/docs`
4. **View Status Page**: `https://f8ai.github.io/formulation-pubmed/articles/`
5. **View RSS Feeds**: `https://f8ai.github.io/formulation-pubmed/rss/`

## Expected Behavior

The microservice will:
- Start background processing on startup
- Search PubMed for cannabis formulation articles
- Process articles through the pipeline (metadata → abstract → full-text → OCR)
- Generate RSS feeds every 6 hours
- Update status page every 30 minutes
- Commit all changes to GitHub automatically

## Monitoring

Check the logs in AWS App Runner to see:
- Search progress
- Article processing
- RSS feed generation
- Git commits
- Error messages

## Configuration

The service uses the search terms defined in `data/pubmed.json`:
- Cannabis formulation terms
- Extraction methods
- Terpenes and cannabinoids
- Pharmaceutical aspects
- Stability testing
- Analytical methods
- Regulatory topics