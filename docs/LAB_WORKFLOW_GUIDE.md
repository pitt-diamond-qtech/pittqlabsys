# Lab Workflow Guide

This document outlines the development workflow for the PittQLabSys project, designed to balance individual freedom with code quality and collaboration.

## 🎯 **Core Philosophy**

- **Individual Forks**: Maximum freedom to experiment and iterate quickly
- **Lab-wide Features**: Strict review and quality control for shared code
- **Collaboration**: Easy sharing of experiments between lab members

## 🏗️ **Repository Structure**

### **Main Repository**
- **`pitt-diamond-qtech/pittqlabsys`**: Contains only lab-wide, stable features
- **Purpose**: Shared codebase that benefits all lab members
- **Quality**: High standards, comprehensive testing, full documentation

### **Individual Forks**
- **`duttlab-sys/pittqlabsys-[setup-name]`**: Personal development spaces
- **Examples**: `pittqlabsys-single-nv`, `pittqlabsys-lev-diamond`, `pittqlabsys-cryo`
- **Purpose**: Hardware-specific experiments and rapid prototyping
- **Freedom**: Work however you want, break things, iterate quickly

## 🚀 **Getting Started**

### **1. Initial Setup**
```bash
# Fork the main repository on GitHub
# Name it: pittqlabsys-[your-setup-name]
# Use the duttlab-sys account (ask @Jonathan Beaumariage for password)

# Clone your fork locally
git clone https://github.com/duttlab-sys/pittqlabsys-[your-setup-name].git
cd pittqlabsys-[your-setup-name]

# Add upstream remote to stay synced with main repo
git remote add upstream https://github.com/pitt-diamond-qtech/pittqlabsys.git
```

### **2. Daily Development Workflow**
```bash
# Work however you want in your fork
git checkout main  # or create branches as needed
# Make changes, test, commit, push
git add .
git commit -m "Your message"
git push origin main

# Sync with upstream weekly (or whenever you want new features)
git fetch upstream
git merge upstream/main
git push origin main
```

## 🔄 **Individual Fork Workflow (Maximum Freedom)**

### **What You Can Do**
- ✅ Work directly on main branch if you prefer
- ✅ Create feature branches as needed
- ✅ Merge whenever you want
- ✅ No code review required
- ✅ Test as much or as little as you want
- ✅ Break things and fix them freely
- ✅ Experiment with different approaches
- ✅ Customize for your specific hardware
- ✅ Iterate quickly without bureaucracy

### **Your Fork, Your Rules**
```bash
# Example: Sarah working on cryo setup
git checkout main
# Add experimental cryostat control
git add .
git commit -m "WIP: trying new cryo approach"
git push origin main

# Later, when it works:
git commit -m "Fixed cryo control, works great!"
git push origin main
```

## 🔒 **Lab-wide Contributions (Strict Review)**

### **When to Contribute Back**
Only contribute to the main repository when you have something valuable for everyone:
- New experiment types that others might use
- Bug fixes that affect multiple setups
- Improvements to core functionality
- New device integrations
- Documentation improvements

### **Requirements for Lab-wide PRs**
- ✅ Must be tested with mock hardware
- ✅ Must include example script in `examples/`
- ✅ Must update relevant documentation
- ✅ Must not break existing experiments
- ✅ Must follow existing code patterns
- ✅ Must have clear commit messages
- ✅ Must include comprehensive description

### **Process**
```bash
# 1. Test thoroughly
python -m pytest tests/
python examples/your_experiment.py --test-only

# 2. Update documentation
# Update README.md, CHANGELOG.md, etc.

# 3. Create PR with detailed description
# Include what, why, and how it benefits the lab

# 4. Wait for review and approval from @gurudevdutt
```

## 🤝 **Sharing Experiments Between Lab Members**

### **Option 1: Direct Fork Access**
- All lab members have access to `duttlab-sys` account
- Can view and clone any fork: `pittqlabsys-single-nv`, `pittqlabsys-lev-diamond`, etc.
- **Pros**: Easy access to all experiments
- **Cons**: Risk of accidentally modifying someone else's repo

### **Option 2: Individual GitHub Accounts (Recommended)**
- Each lab member creates their own GitHub account
- Fork from main repo: `your-username/pittqlabsys-[setup-name]`
- **Pros**: Clear ownership, no accidental modifications
- **Cons**: Need to manage multiple accounts

### **Option 3: Hybrid Approach**
- Keep `duttlab-sys` for shared experiments
- Individual accounts for personal development
- Use `duttlab-sys` forks for "lab-wide" experiments that multiple people need

## 📋 **Recommended Approach for Sharing**

### **For Experiments Used by Multiple People:**
1. **Create in `duttlab-sys` fork** with clear naming: `pittqlabsys-shared-[experiment-name]`
2. **Add README** explaining what it's for and who uses it
3. **Tag team members** when making changes
4. **Use branches** for different versions/approaches

### **For Personal Experiments:**
1. **Use individual GitHub account** for personal development
2. **Share via direct access** when needed
3. **Contribute to main repo** when ready for lab-wide use

## 🔄 **Sync Strategy**

### **Individual Forks Should Sync:**
- **Weekly minimum** - to get new lab-wide features
- **Before major changes** - to avoid conflicts
- **When you want to contribute back** - to ensure compatibility
- **Whenever you have changes you want to preserve** - to avoid losing work

### **When NOT to Sync:**
- **In the middle of active development** - avoid merge conflicts
- **When your changes are experimental** - keep them isolated
- **When you're happy with your current version** - no need to update

## 🧪 **Testing and Quality Control**

### **Individual Forks:**
- **Test as much or as little as you want**
- **Use mock hardware for quick testing**
- **Test with real hardware when available**
- **No formal requirements**

### **Lab-wide Contributions:**
- **Must run full test suite**: `python -m pytest tests/`
- **Must test with mock hardware**: `python examples/your_experiment.py --test-only`
- **Must test with real hardware if available**
- **Must not break existing functionality**

### **Handling Divergent Forks:**
- **Use tests to identify conflicts**: Run `pytest` to see what breaks
- **Document changes**: Keep detailed changelog of modifications
- **Incremental merging**: Merge changes in small, testable chunks
- **Communication**: Discuss major changes with team before implementing

## 📚 **Documentation Standards**

### **Individual Forks:**
- **Document as much or as little as you want**
- **Keep personal notes** for your own reference
- **Update when you feel like it**

### **Lab-wide Contributions:**
- **Must update README.md** if adding new features
- **Must add examples** in `examples/` directory
- **Must update CHANGELOG.md** for significant changes
- **Must document hardware requirements** in experiment docstrings

## 🚨 **Safety Measures for Shared Account**

### **Preventing Accidental Modifications:**
1. **Always check which repo you're in** before making changes
2. **Use descriptive commit messages** that include setup name
3. **Create branches** for experimental work
4. **Communicate** when making changes to shared repos
5. **Use `git status`** to verify you're in the right repo

### **Best Practices:**
```bash
# Always check your current repo
git remote -v
# Should show: origin -> duttlab-sys/pittqlabsys-[your-setup]

# Use descriptive commit messages
git commit -m "[single-nv] Add new ODMR experiment for confocal bay"

# Create branches for experimental work
git checkout -b feature/new-experiment
```

## 📋 **Quick Reference Commands**

### **Daily Work (Your Fork):**
```bash
git status                           # Check current status
git add .                           # Stage changes
git commit -m "Your message"        # Commit changes
git push origin main                # Push to your fork
```

### **Syncing with Main Repo:**
```bash
git fetch upstream                  # Get latest changes
git merge upstream/main            # Merge into your main
git push origin main               # Update your fork
```

### **Contributing to Lab-wide Code:**
```bash
# 1. Test thoroughly
python -m pytest tests/
python examples/your_experiment.py --test-only

# 2. Update documentation
# 3. Create PR with detailed description
# 4. Wait for review and approval
```

## 🎯 **Lab-wide Features Wishlist**

We maintain a wishlist of features that would benefit the entire lab. Add your requests here:

### **Current Wishlist:**
- [ ] Automated data analysis pipeline
- [ ] Real-time experiment monitoring dashboard
- [ ] Hardware calibration management system
- [ ] Experiment result comparison tools
- [ ] Automated report generation

### **How to Add to Wishlist:**
1. **Create issue** in main repository
2. **Tag @gurudevdutt** for review
3. **Include detailed description** of what you need
4. **Explain how it would benefit the lab**

## ❓ **Getting Help**

- **Git/GitHub issues**: Ask @gurudevdutt or other experienced team members
- **Hardware problems**: Check device-specific documentation in `docs/`
- **Experiment development**: Look at existing examples in `examples/`
- **Code review**: Tag @gurudevdutt for lab-wide contributions

## 🔄 **Workflow Summary**

1. **Fork main repo** with descriptive name
2. **Work freely** in your fork - no restrictions
3. **Sync weekly** with upstream main
4. **Contribute back** when you have valuable features
5. **Share experiments** via direct access or shared repos
6. **Test thoroughly** before lab-wide contributions
7. **Document changes** appropriately

Remember: **Your fork is your playground, the main repo is our shared foundation.**
