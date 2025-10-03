#!/bin/bash

# Ultra-fast deployment script for CapRover
# Optimized for minimal build context and maximum speed

set -e

echo "🚀 Starting ultra-fast deployment..."

# Use ultra-optimized dockerignore
cp .dockerignore.ultra .dockerignore
echo "✅ Applied ultra-optimized .dockerignore"

# Update captain-definition to use ultra-fast Dockerfile
cat > captain-definition << EOF
{
  "schemaVersion": 2,
  "dockerfilePath": "./Dockerfile.backend.ultra-fast"
}
EOF
echo "✅ Updated captain-definition for ultra-fast build"

# Create minimal tarball with only essential files
echo "📦 Creating minimal deployment package..."
tar -czf growthee-ultra-fast-deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env*' \
  --exclude='venv' \
  --exclude='frontend' \
  --exclude='results' \
  --exclude='tests' \
  --exclude='docs' \
  --exclude='*.tar.gz' \
  --exclude='*.md' \
  --exclude='check_*.py' \
  --exclude='create_*.py' \
  --exclude='update_*.py' \
  --exclude='fix_*.py' \
  --exclude='Dockerfile.backend.fast' \
  --exclude='Dockerfile.backend.minimal' \
  --exclude='Dockerfile.backend.prod' \
  --exclude='Dockerfile.backend.simple' \
  --exclude='Dockerfile.prod' \
  --exclude='docker-compose*.yml' \
  .

# Show package info
PACKAGE_SIZE=$(ls -lh growthee-ultra-fast-deploy.tar.gz | awk '{print $5}')
echo "✅ Ultra-fast deployment package created: $PACKAGE_SIZE"

# Verify essential files are included
echo "🔍 Verifying essential files..."
tar -tzf growthee-ultra-fast-deploy.tar.gz | grep -E '(captain-definition|Dockerfile.backend.ultra-fast|requirements-minimal.txt|api/main.py|prisma/schema.prisma)' || echo "⚠️  Some essential files might be missing"

echo "🎉 Ultra-fast deployment package ready!"
echo "📁 File: growthee-ultra-fast-deploy.tar.gz ($PACKAGE_SIZE)"
echo "🚀 Upload this to CapRover for lightning-fast deployment"

# Restore original dockerignore
if [ -f ".dockerignore.backup" ]; then
  cp .dockerignore.backup .dockerignore
  echo "✅ Restored original .dockerignore"
fi