# Quality Quick Reference

## 🎯 **Key Quality Standards**

### **Commit Messages**
```
[setup-name] Brief description

- Bullet point explaining what was changed
- Another bullet point explaining why
- Tested with mock/real hardware
```

### **Function Docstrings**
```python
def function_name(self, param: type) -> return_type:
    """
    Brief description of what function does.
    
    Args:
        param (type): Description of parameter
        
    Returns:
        return_type: Description of return value
        
    Tested with mock hardware
    """
```

### **Quality Assessment**
```bash
# Check recent commits
python scripts/assess_quality.py --commits 5

# Check specific files
python scripts/assess_quality.py --path src/Model/experiments/
```

### **Quality Goals by Level**
- **Individual Development**: 40-60 score, focus on functionality
- **Setup Collaboration**: 60-80 score, address major issues
- **Lab-wide Contributions**: 80+ score, production quality

## 📚 **Full Documentation**
- **[Quality Guidelines](QUALITY_GUIDELINES.md)** - Complete standards and examples
- **[Lab Workflow Guide](LAB_WORKFLOW_GUIDE.md)** - Three-level workflow
- **[Pull Request Template](.github/pull_request_template.md)** - PR checklist

## 🔧 **Quick Fixes**
- **Long lines**: Break into multiple lines
- **Missing docstrings**: Add comprehensive docstrings
- **Debug prints**: Replace with `self.log()`
- **Commit format**: Use `[setup-name]` prefix
