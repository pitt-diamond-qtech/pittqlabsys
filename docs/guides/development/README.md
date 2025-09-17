# Development Guide

This section contains guides for developers working on PittQLabSys.

## 🚀 Getting Started

### Essential Reading
- [Lab Workflow](lab-workflow.md) - How we collaborate and work together
- [Development Guide](development-guide.md) - General development guidelines
- [Quality Guidelines](quality-guidelines.md) - Code quality standards

### Quick Reference
- [Quality Quick Reference](quality-quick-reference.md) - Quick quality checklist
- [Testing with Mock](testing-with-mock.md) - Testing without real hardware

## 🔧 Development Topics

### Experiment Development
- [Experiment Development](experiment-development.md) - Creating new experiments
- [Experiment Iterator Guide](experiment-iterator-guide.md) - Using experiment iterators

### Device Development
- [Device Development](device-development.md) - Creating new devices

### Collaboration
- [Contribution Guidelines](contribution-guidelines.md) - How to contribute to the project
- [Shared Account Safety](shared-account-safety.md) - Working with shared accounts

## 🎯 Development Workflow

### 1. Setup
1. Fork the main repository
2. Clone your fork locally
3. Set up development environment
4. Read [Lab Workflow](lab-workflow.md)

### 2. Development
1. Create feature branches
2. Write code following [Quality Guidelines](quality-guidelines.md)
3. Test with [Mock Hardware](testing-with-mock.md)
4. Test with real hardware when available

### 3. Collaboration
1. Share branches with team members
2. Get feedback and iterate
3. Merge to setup main when stable
4. Contribute to lab-wide when ready

### 4. Quality Control
1. Run quality assessment tools
2. Address any issues
3. Test thoroughly
4. Document changes

## 📋 Development Standards

### Code Quality
- Follow [Quality Guidelines](quality-guidelines.md)
- Use [Quality Quick Reference](quality-quick-reference.md) as checklist
- Run quality assessment tools regularly

### Testing
- Use [Testing with Mock](testing-with-mock.md) for development
- Test with real hardware when available
- Write comprehensive tests

### Documentation
- Document all public APIs
- Include examples in docstrings
- Update relevant guides when adding features

### Git Workflow
- Use descriptive commit messages
- Create feature branches for new work
- Keep main branch stable
- Sync with upstream regularly

## 🔗 Related Resources

### Technical Reference
- [Configuration Reference](../../reference/configuration.md) - System configuration
- [Parameter System](../../reference/parameter-class-analysis.md) - Parameter system details
- [API Reference](../../reference/) - Technical specifications

### Architecture
- [System Architecture](../../architecture/) - High-level system design
- [Device Architecture](../../architecture/device-architecture.md) - Device system design

### Internal Development
- [Development Notes](../../internal/development/) - Internal development progress
- [Planning Documents](../../internal/planning/) - Implementation plans

## ❓ Getting Help

### Common Issues
1. **Code not working**: Check [Testing with Mock](testing-with-mock.md)
2. **Quality issues**: Run quality assessment tools
3. **Git problems**: Ask experienced team members
4. **Hardware issues**: Check [Hardware Guides](../hardware/)

### Resources
- **Code Review**: Tag @gurudevdutt for lab-wide contributions
- **Technical Questions**: Check [Reference](../../reference/) section
- **Architecture Questions**: Look at [Architecture](../../architecture/) section

## 📝 Contributing to Development Guides

When updating development guides:

1. **Keep them current** with the latest practices
2. **Include examples** where helpful
3. **Cross-reference** related guides
4. **Test the instructions** before publishing
5. **Update this README** when adding new guides

---

*These guides are designed to help developers work effectively with PittQLabSys. For technical details, check the [Reference](../../reference/) section.*
