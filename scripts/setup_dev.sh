#!/bin/bash
set -e

echo "🚀 Setting up TraceOne Monitoring Service Development Environment"
echo "================================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "❌ Python 3.9+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -e ".[dev,test]"

# Create logs directory
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data

# Copy example environment file
if [ ! -f "config/dev.env" ]; then
    echo "📋 Creating development environment file..."
    cp config/dev.env.example config/dev.env
    echo "⚠️  Please edit config/dev.env with your D&B API credentials"
fi

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
if python -m pytest tests/unit/ -v; then
    echo "✅ Unit tests passed"
else
    echo "⚠️  Some tests failed - this might be expected without D&B credentials"
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected - you can use Docker Compose for development"
    echo "   Run: docker-compose -f docker/docker-compose.dev.yml up"
else
    echo "⚠️  Docker not detected - install Docker for containerized development"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/dev.env with your D&B API credentials"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run the service: python -m traceone_monitoring.cli status"
echo "4. Create a registration: python -m traceone_monitoring.cli create-registration --reference MyTest --duns 123456789"
echo "5. Monitor notifications: python -m traceone_monitoring.cli monitor --reference MyTest"
echo ""
echo "For development with Docker:"
echo "1. Copy config/dev.env to docker/.env"
echo "2. Run: docker-compose -f docker/docker-compose.dev.yml up"
echo ""
echo "Happy coding! 🚀"
