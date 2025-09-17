# Shared Account Safety Guide

This document outlines safety measures and best practices for using the shared `duttlab-sys` GitHub account.

## 🚨 **Critical Safety Rules**

### **Always Verify Your Repository**
```bash
# Before making ANY changes, check which repo you're in
git remote -v
# Should show: origin -> duttlab-sys/pittqlabsys-[your-setup]

# Check current branch
git branch
# Should show your current branch

# Check status
git status
# Should show your current changes
```

### **Use Descriptive Commit Messages**
```bash
# Good: Include setup name and clear description
git commit -m "[single-nv] Add new ODMR experiment for confocal bay"
git commit -m "[cryo] Fix temperature control bug in cryostat integration"
git commit -m "[lev-diamond] Update laser power settings for new setup"

# Bad: Vague or missing setup information
git commit -m "Fixed bug"
git commit -m "Added experiment"
git commit -m "Updated code"
```

## 🛡️ **Prevention Strategies**

### **1. Repository Verification Checklist**
Before making any changes, always verify:
- [ ] **Correct repository** - check `git remote -v`
- [ ] **Correct branch** - check `git branch`
- [ ] **Clean working directory** - check `git status`
- [ ] **Recent backup** - ensure your work is saved elsewhere

### **2. Branch Strategy**
```bash
# Create branches for experimental work
git checkout -b feature/new-experiment
git checkout -b bugfix/temperature-control
git checkout -b tristan/odmr-improvements

# This prevents accidental changes to main branches
```

### **3. Communication Protocol**
- **Announce changes** in lab chat before making significant modifications
- **Tag team members** when making changes to shared experiments
- **Use descriptive branch names** that include your name or setup
- **Document changes** in commit messages and PR descriptions

## 🔍 **Verification Commands**

### **Check Current Repository**
```bash
# Verify you're in the right repo
git remote -v
# Should show: origin -> duttlab-sys/pittqlabsys-[your-setup]

# Check repository URL
git config --get remote.origin.url
# Should show: https://github.com/duttlab-sys/pittqlabsys-[your-setup].git
```

### **Check Current Branch**
```bash
# See current branch
git branch
# Should show: * main (or your feature branch)

# See all branches
git branch -a
# Shows local and remote branches
```

### **Check Working Directory**
```bash
# See what files have changed
git status
# Shows modified, staged, and untracked files

# See specific changes
git diff
# Shows unstaged changes

git diff --cached
# Shows staged changes
```

## 🚨 **Emergency Procedures**

### **If You Accidentally Modified Wrong Repository**
```bash
# 1. Stop immediately - don't commit
git status

# 2. Stash your changes
git stash push -m "Accidental changes to wrong repo"

# 3. Switch to correct repository
cd /path/to/correct/repository

# 4. Apply your changes there
git stash pop

# 5. Verify you're in the right place
git remote -v
```

### **If You Committed to Wrong Repository**
```bash
# 1. Don't push yet!
# 2. Reset the commit (keeps changes)
git reset --soft HEAD~1

# 3. Switch to correct repository
cd /path/to/correct/repository

# 4. Apply your changes
git add .
git commit -m "Your commit message"

# 5. Push to correct repository
git push origin main
```

### **If You Pushed to Wrong Repository**
```bash
# 1. Contact @gurudevdutt immediately
# 2. Don't make more changes
# 3. Document what happened
# 4. Wait for guidance on how to fix
```

## 📋 **Daily Safety Checklist**

### **Before Starting Work**
- [ ] **Check repository** - `git remote -v`
- [ ] **Check branch** - `git branch`
- [ ] **Check status** - `git status`
- [ ] **Pull latest changes** - `git pull origin main`
- [ ] **Create backup branch** - `git checkout -b backup/$(date +%Y%m%d)`

### **Before Making Changes**
- [ ] **Verify you're in correct repo**
- [ ] **Create feature branch** if making significant changes
- [ ] **Announce your work** in lab chat
- [ ] **Check for recent changes** by others

### **Before Committing**
- [ ] **Review changes** - `git diff`
- [ ] **Check file list** - `git status`
- [ ] **Write descriptive commit message**
- [ ] **Include setup name** in commit message

### **Before Pushing**
- [ ] **Double-check repository** - `git remote -v`
- [ ] **Review commit message**
- [ ] **Test your changes** if possible
- [ ] **Consider creating PR** for significant changes

## 🔧 **Best Practices**

### **Repository Management**
```bash
# Always work in feature branches for significant changes
git checkout -b feature/your-feature-name

# Use descriptive branch names
git checkout -b tristan/odmr-experiment
git checkout -b sarah/cryo-control
git checkout -b bugfix/temperature-sensor

# Regular backups
git checkout -b backup/$(date +%Y%m%d)
git push origin backup/$(date +%Y%m%d)
```

### **Commit Messages**
```bash
# Format: [setup-name] Brief description
git commit -m "[single-nv] Add new ODMR experiment for confocal bay"
git commit -m "[cryo] Fix temperature control PID parameters"
git commit -m "[lev-diamond] Update laser power calibration"

# Include more details for significant changes
git commit -m "[single-nv] Add new ODMR experiment for confocal bay

- Implements temperature-dependent ODMR measurements
- Adds cryostat control integration
- Includes data analysis functions
- Tested with mock hardware"
```

### **Communication**
- **Announce major changes** before starting
- **Tag relevant team members** when making changes
- **Document your work** in commit messages
- **Ask for help** if unsure about anything

## 🚨 **Warning Signs**

### **Stop and Verify If You See:**
- **Different repository name** than expected
- **Unfamiliar file changes** in git status
- **Unexpected branch names** in git branch
- **Conflicting changes** from other team members
- **Any uncertainty** about what you're doing

### **When in Doubt:**
1. **Stop immediately**
2. **Check repository** - `git remote -v`
3. **Ask for help** - contact @gurudevdutt
4. **Don't commit or push** until you're sure
5. **Document what happened** for future reference

## 📞 **Emergency Contacts**

- **@gurudevdutt**: Primary contact for any issues
- **Lab Chat**: For quick questions and announcements
- **GitHub Issues**: For documenting problems and solutions

## 🔄 **Recovery Procedures**

### **If You Made Changes to Wrong Repository**
1. **Don't panic** - most issues can be fixed
2. **Stop making changes** immediately
3. **Document what happened** - what repo, what changes
4. **Contact @gurudevdutt** for guidance
5. **Follow recovery instructions** carefully

### **If Someone Else's Work Was Affected**
1. **Contact them immediately** - don't try to fix it yourself
2. **Document what happened** - what you changed, when
3. **Coordinate recovery** with the affected person
4. **Learn from the mistake** - update your safety procedures

## 📚 **Learning Resources**

- **Git Basics**: https://git-scm.com/docs
- **GitHub Workflow**: https://docs.github.com/en/get-started
- **Lab Workflow Guide**: `docs/LAB_WORKFLOW_GUIDE.md`
- **Contribution Guidelines**: `docs/CONTRIBUTION_GUIDELINES.md`

## 🎯 **Remember**

- **Safety first** - always verify before making changes
- **Communication is key** - announce your work and ask questions
- **Mistakes happen** - learn from them and improve procedures
- **Team support** - we're all here to help each other succeed

**When in doubt, ask for help. It's better to ask a question than to make a mistake.**
