#!/bin/bash

# Formulation PubMed Microservice Deployment Script
# This script helps deploy the microservice to AWS App Runner

set -e

echo "🚀 Formulation PubMed Microservice Deployment"
echo "=============================================="

# Check if GitHub repository exists
echo "📋 Checking GitHub repository..."
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "❌ No GitHub remote found. Please create the repository first:"
    echo "   1. Go to https://github.com/f8ai"
    echo "   2. Click 'New repository'"
    echo "   3. Name: 'formulation-pubmed'"
    echo "   4. Make it public"
    echo "   5. Don't initialize with README"
    echo ""
    echo "Then run:"
    echo "   git remote add origin https://github.com/f8ai/formulation-pubmed.git"
    echo "   git push -u origin main"
    exit 1
fi

# Check if we can push to GitHub
echo "📤 Pushing to GitHub..."
if git push origin main; then
    echo "✅ Successfully pushed to GitHub"
else
    echo "❌ Failed to push to GitHub. Please check your access rights."
    exit 1
fi

# Check AWS CLI
echo "🔍 Checking AWS CLI..."
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   brew install awscli"
    echo "   aws configure"
    exit 1
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run:"
    echo "   aws configure"
    exit 1
fi

echo "✅ AWS credentials configured"

# Check if S3 bucket exists
echo "🪣 Checking S3 bucket..."
BUCKET_NAME="f8ai-data"
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "📦 Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb "s3://$BUCKET_NAME" --region us-east-1
    echo "✅ S3 bucket created"
else
    echo "✅ S3 bucket exists"
fi

# Deploy to App Runner
echo "🚀 Deploying to AWS App Runner..."
echo ""
echo "To deploy to App Runner:"
echo "1. Go to AWS App Runner console"
echo "2. Create a new service"
echo "3. Choose 'Source code repository'"
echo "4. Connect to GitHub and select 'f8ai/formulation-pubmed'"
echo "5. Use the 'apprunner.yaml' configuration"
echo "6. Set environment variables:"
echo "   - AWS_ACCESS_KEY_ID: $(aws configure get aws_access_key_id)"
echo "   - AWS_SECRET_ACCESS_KEY: [your secret key]"
echo "   - AWS_DEFAULT_REGION: us-east-1"
echo ""

# Test local deployment
echo "🧪 Testing local deployment..."
if python test_local.py; then
    echo "✅ Local tests passed"
else
    echo "❌ Local tests failed. Please fix issues before deploying."
    exit 1
fi

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Deploy to AWS App Runner using the instructions above"
echo "2. Monitor at: https://your-app-url/health"
echo "3. View status at: https://your-app-url/status"
echo "4. Check RSS feeds at: https://f8ai.github.io/formulation-pubmed/rss/"
echo ""
echo "The microservice is ready to process cannabis formulation articles! 🌿"