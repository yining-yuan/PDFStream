#!/usr/bin/env bash
# Startup script for PDFStream application

set -e

echo "======================================"
echo "PDFStream - Starting Application"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Download NLTK data
echo "Downloading NLTK data (punkt, stopwords, wordnet, omw-1.4, averaged_perceptron_tagger, brown)..."
python3 -c "import nltk; \
    nltk.download('punkt', quiet=True); \
    nltk.download('stopwords', quiet=True); \
    nltk.download('wordnet', quiet=True); \
    nltk.download('omw-1.4', quiet=True); \
    nltk.download('averaged_perceptron_tagger', quiet=True); \
    nltk.download('brown', quiet=True)"

# Create uploads directory
mkdir -p uploads

echo ""
echo "======================================"
echo "Starting PDFStream..."
echo "======================================"
echo ""
echo "Access the web interface at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the application
python3 app.py
