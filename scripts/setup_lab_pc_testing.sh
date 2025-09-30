#!/bin/bash
# Setup script for lab PC testing of enhanced parameter validation

echo "🔧 Setting up Lab PC for Enhanced Parameter Validation Testing"
echo "=============================================================="

# Check if we're in the right directory
if [ ! -f "src/core/device.py" ]; then
    echo "❌ Error: Please run this script from the pittqlabsys root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found. Please create it first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate  # Linux"
    echo "   venv\\Scripts\\activate     # Windows"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate 2>/dev/null || venv/Scripts/activate 2>/dev/null

# Check if we're on the right branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "feature/parameter-validation-feedback" ]; then
    echo "⚠️  Warning: Not on feature/parameter-validation-feedback branch"
    echo "   Current branch: $current_branch"
    echo "   To switch: git checkout feature/parameter-validation-feedback"
fi

# Pull latest changes
echo "🔧 Pulling latest changes..."
git fetch origin
git pull origin feature/parameter-validation-feedback

# Check Python dependencies
echo "🔧 Checking Python dependencies..."
python -c "import PyQt5; print('✅ PyQt5 available')" || echo "❌ PyQt5 not available"
python -c "import pint; print('✅ pint available')" || echo "❌ pint not available"
python -c "import numpy; print('✅ numpy available')" || echo "❌ numpy not available"

# Run basic validation test
echo "🔧 Running basic validation test..."
python examples/test_validation_features.py --help 2>/dev/null || echo "⚠️  Basic test not available"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Ready to test:"
echo "   1. Mock hardware test: python examples/test_validation_features.py"
echo "   2. Real hardware test: python examples/test_real_hardware_validation.py"
echo "   3. GUI with mocks: python examples/test_gui_with_validation.py"
echo "   4. Full GUI: python src/View/windows_and_widgets/main_window.py"
echo ""
echo "📋 Test scenarios to try:"
echo "   - Set stage position to 15.0mm (should clamp to 10.0mm)"
echo "   - Set RF frequency to 8.0 GHz (should clamp to 6.0 GHz)"
echo "   - Set RF power to 25.0 mW (should clamp to 20.0 mW)"
echo "   - Watch for colored backgrounds and text box corrections"
echo ""
echo "📖 See docs/lab_pc_testing_guide.md for detailed instructions"
