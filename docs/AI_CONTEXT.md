# AI Assistant Context

## 🎯 **Project Overview**
PittQLabSys is a quantum information science laboratory automation system with comprehensive quality guidelines and a three-level development workflow.

## 📋 **Quality Standards (Always Follow)**

### **Commit Messages**
- Format: `[setup-name] Brief description`
- Include bullet points explaining what and why
- Mention testing (mock/real hardware)

### **Code Quality**
- Comprehensive docstrings with Args/Returns
- Type hints for all parameters
- Meaningful variable names
- Error handling for device operations
- No hardcoded values

### **Quality Assessment**
- Run `python scripts/assess_quality.py --commits 5` regularly
- Target scores: Individual (40-60), Setup (60-80), Lab-wide (80+)

## 🔄 **Workflow Levels**
1. **Individual Development**: Maximum freedom, optional quality checks
2. **Setup Collaboration**: Moderate quality focus, team consistency
3. **Lab-wide Contributions**: High quality standards, comprehensive testing

## 📚 **Key Documentation**
- `docs/QUALITY_GUIDELINES.md` - Complete quality standards
- `docs/LAB_WORKFLOW_GUIDE.md` - Three-level workflow
- `scripts/assess_quality.py` - Quality assessment tool
- `.github/pull_request_template.md` - PR checklist

## 🎯 **When Working on Code**
- Always check quality guidelines before suggesting changes
- Use the quality assessment tool to identify issues
- Follow the appropriate workflow level for the context
- Reference the quick reference guide for common patterns
