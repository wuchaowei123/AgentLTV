#!/bin/bash
# Scientific AI System - Setup Verification Script
# This script checks if your environment is properly configured

echo "🔍 Checking Scientific AI System Setup..."
echo "=================================================="
echo ""

# Check Python
echo "1️⃣  Python Installation"
if python --version &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo "   ✅ $PYTHON_VERSION"
else
    echo "   ❌ Python not found"
    echo "      Install Python 3.9+ and try again"
fi
echo ""

# Check conda environment
echo "2️⃣  Conda Environment"
if command -v conda &> /dev/null; then
    if [[ "$CONDA_DEFAULT_ENV" == "pytorch" ]]; then
        echo "   ✅ Conda environment: pytorch (active)"
    elif [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        echo "   ⚠️  Current environment: $CONDA_DEFAULT_ENV"
        echo "      Run: conda activate pytorch"
    else
        echo "   ⚠️  No conda environment active"
        echo "      Run: conda activate pytorch"
    fi
else
    echo "   ℹ️  Conda not found (using system Python)"
fi
echo ""

# Check dependencies
echo "3️⃣  Python Dependencies"
MISSING_DEPS=0
for package in pandas numpy scikit-learn google-genai pyyaml; do
    if python -c "import ${package//-/_}" 2> /dev/null; then
        echo "   ✅ $package"
    else
        echo "   ❌ $package (missing)"
        MISSING_DEPS=1
    fi
done
if [ $MISSING_DEPS -eq 1 ]; then
    echo "      Run: pip install -r requirements.txt"
fi
echo ""

# Check API credentials
echo "4️⃣  API Credentials"
if [[ -n "$GOOGLE_CLOUD_PROJECT" ]]; then
    echo "   ✅ Google Cloud Project: $GOOGLE_CLOUD_PROJECT"
    
    # Check if gcloud is authenticated
    if command -v gcloud &> /dev/null; then
        if gcloud auth application-default print-access-token &> /dev/null; then
            echo "   ✅ Google Cloud authenticated"
        else
            echo "   ⚠️  Google Cloud authentication needed"
            echo "      Run: gcloud auth application-default login"
        fi
    else
        echo "   ⚠️  gcloud CLI not found"
        echo "      Install from: https://cloud.google.com/sdk/docs/install"
    fi
elif [[ -n "$OPENAI_API_KEY" ]]; then
    echo "   ✅ OpenAI API Key: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
else
    echo "   ❌ No API credentials found"
    echo "      Set either GOOGLE_CLOUD_PROJECT or OPENAI_API_KEY"
    echo "      For Gemini: export GOOGLE_CLOUD_PROJECT='your-project-id'"
    echo "      For OpenAI: export OPENAI_API_KEY='sk-...'"
fi
echo ""

# Check core system
echo "5️⃣  Core System"
if python -c "from core.task_manager import TaskConfiguration" 2> /dev/null; then
    echo "   ✅ Core system imports working"
else
    echo "   ❌ Core system imports failed"
    echo "      Make sure you're in the MTCS_module directory"
    echo "      Run: pip install -r requirements.txt"
fi

if python -c "from core.database.db_manager import DatabaseManager" 2> /dev/null; then
    echo "   ✅ Database system working"
else
    echo "   ⚠️  Database system check failed"
fi
echo ""

# Check optional components
echo "6️⃣  Optional Components"
if command -v gemini &> /dev/null; then
    GEMINI_VERSION=$(gemini --version 2>&1 | head -1 || echo "version unknown")
    echo "   ✅ Gemini CLI: $GEMINI_VERSION"
else
    echo "   ℹ️  Gemini CLI not installed (optional for auto-fixer)"
    echo "      Install: npm install -g @google/gemini-cli"
fi

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo "   ✅ Node.js: $NODE_VERSION"
else
    echo "   ℹ️  Node.js not found (needed for Gemini CLI)"
fi
echo ""

# Check data files
echo "7️⃣  Example Data"
if [ -f "tasks/kaggle_machine_failures/data/train.csv" ]; then
    echo "   ✅ Example dataset available"
else
    echo "   ℹ️  Example dataset not downloaded"
    echo "      Run: python download_data.py"
fi
echo ""

# Final summary
echo "=================================================="
echo "📋 Setup Verification Complete"
echo ""
echo "Next steps:"
echo "  1. Fix any ❌ items above"
echo "  2. Run: python download_data.py (if needed)"
echo "  3. Run: python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 3"
echo ""

