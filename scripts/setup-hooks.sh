#!/bin/bash

# TraceOne Monitoring - Git Hooks Setup Script
# This script sets up pre-commit hooks and other development tools

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message $BLUE "🚀 Setting up TraceOne Monitoring development environment..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_message $RED "❌ Error: Not in a git repository"
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    print_message $RED "❌ Poetry is not installed. Please install Poetry first:"
    print_message $YELLOW "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

print_message $GREEN "✅ Poetry found"

# Install dependencies
print_message $BLUE "📦 Installing dependencies..."
poetry install

# Install pre-commit
print_message $BLUE "🔧 Installing pre-commit hooks..."
poetry run pre-commit install

# Install commit-msg hook for commitizen
poetry run pre-commit install --hook-type commit-msg

# Create secrets baseline for detect-secrets
print_message $BLUE "🔒 Setting up secrets detection..."
if [ ! -f .secrets.baseline ]; then
    poetry run detect-secrets scan --baseline .secrets.baseline
    print_message $GREEN "✅ Created secrets baseline"
else
    print_message $YELLOW "⚠️  Secrets baseline already exists"
fi

# Run pre-commit on all files to ensure everything is working
print_message $BLUE "🧪 Running pre-commit checks on all files..."
if poetry run pre-commit run --all-files; then
    print_message $GREEN "✅ All pre-commit checks passed!"
else
    print_message $YELLOW "⚠️  Some pre-commit checks failed. Please review and fix the issues."
fi

# Create local development environment file template
if [ ! -f .env.local ]; then
    print_message $BLUE "📝 Creating local environment template..."
    cat > .env.local << EOF
# TraceOne Monitoring - Local Development Environment
# Copy this file and customize for your local development setup

# TraceOne API Configuration
TRACEONE_API_BASE_URL=https://api.traceone.app
TRACEONE_API_KEY=your_api_key_here
TRACEONE_API_SECRET=your_api_secret_here

# Application Configuration
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Redis Configuration (for caching)
REDIS_URL=redis://localhost:6379/0

# Monitoring Configuration
POLL_INTERVAL=60
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=5

# Optional: Custom configuration file path
# CONFIG_FILE_PATH=/path/to/custom/config.yaml
EOF
    print_message $GREEN "✅ Created .env.local template"
    print_message $YELLOW "⚠️  Please update .env.local with your actual configuration"
else
    print_message $YELLOW "⚠️  .env.local already exists"
fi

# Create development scripts directory
mkdir -p scripts/dev

# Create a development runner script
cat > scripts/dev/run-dev.sh << 'EOF'
#!/bin/bash

# Development runner script for TraceOne Monitoring

# Load environment variables
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Run the monitoring service in development mode
poetry run python -m src.main --config config/development.yaml --verbose
EOF

chmod +x scripts/dev/run-dev.sh

# Create a test runner script
cat > scripts/dev/run-tests.sh << 'EOF'
#!/bin/bash

# Test runner script with coverage

set -e

echo "🧪 Running tests with coverage..."

# Run tests with coverage
poetry run pytest tests/ \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --verbose \
    --tb=short

echo "📊 Coverage report generated in htmlcov/"
echo "🌐 Open htmlcov/index.html in your browser to view detailed coverage"
EOF

chmod +x scripts/dev/run-tests.sh

print_message $GREEN "✅ Created development scripts:"
print_message $BLUE "   - scripts/dev/run-dev.sh (run development server)"
print_message $BLUE "   - scripts/dev/run-tests.sh (run tests with coverage)"

# Final setup message
print_message $GREEN "
🎉 Development environment setup complete!

Next steps:
1. Update .env.local with your TraceOne API credentials
2. Run 'poetry shell' to activate the virtual environment
3. Use 'scripts/dev/run-dev.sh' to start the development server
4. Use 'scripts/dev/run-tests.sh' to run tests
5. Make sure all commits follow conventional commit format

Happy coding! 🚀
"

# Show git status
print_message $BLUE "📋 Current git status:"
git status --short
