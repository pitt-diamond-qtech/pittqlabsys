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
- ✅ Must use the **[Pull Request Template](.github/pull_request_template.md)** for consistent formatting

### **Process**
```bash
# 1. Test thoroughly
python -m pytest tests/
python examples/your_experiment.py --test-only

# 2. Update documentation
# Update README.md, CHANGELOG.md, etc.

# 3. Create PR using the template
# Use the Pull Request Template (.github/pull_request_template.md)
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
- **Optional quality assessment**: `python scripts/assess_quality.py --commits 5`

### **Lab-wide Contributions:**
- **Must run full test suite**: `python -m pytest tests/`
- **Must test with mock hardware**: `python examples/your_experiment.py --test-only`
- **Must test with real hardware if available**
- **Must not break existing functionality**
- **Must run quality assessment**: `python scripts/assess_quality.py --commits 10`
- **Must address major quality issues** before submitting PRs

### **Quality Guidelines:**
For detailed quality standards, commit message formats, and code documentation requirements, see:
- **[📋 Quality Guidelines](QUALITY_GUIDELINES.md)** - Comprehensive quality standards and examples
- **Quality Assessment Tool** - `scripts/assess_quality.py` for objective quality metrics
- **GitHub Actions** - Automated quality checks run on all PRs and pushes to main

### **GitHub Actions Quality Checks:**
The repository includes automated quality checks that run on every pull request and push to main:
- **Code style** (flake8) - checks for syntax errors and style issues
- **Code formatting** (black) - ensures consistent code formatting
- **Documentation** (pydocstyle) - checks docstring quality
- **Tests** (pytest) - runs the test suite
- **Commit messages** - validates commit message format

> **⚠️ Note**: The GitHub Actions are currently set to **warn but not fail** on quality issues, allowing the repository to function while quality improvements are made incrementally.

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

## 👨‍🎓 **Student Example: Developing a Cryo Device Controller**

Let's follow Jannet, a new graduate student, as she develops a new cryostat temperature controller for the lab's cryo setup.

### **Step 1: Initial Setup**
```bash
# Jannet forks the main repository on GitHub
# Repository name: pittqlabsys-cryo
# Uses duttlab-sys account (gets password from @Jonathan Beaumariage)

# Clone her fork locally
git clone https://github.com/duttlab-sys/pittqlabsys-cryo.git
cd pittqlabsys-cryo

# Add upstream remote
git remote add upstream https://github.com/pitt-diamond-qtech/pittqlabsys.git

# Verify setup
git remote -v
# Should show:
# origin    https://github.com/duttlab-sys/pittqlabsys-cryo.git (fetch)
# origin    https://github.com/duttlab-sys/pittqlabsys-cryo.git (push)
# upstream  https://github.com/pitt-diamond-qtech/pittqlabsys.git (fetch)
# upstream  https://github.com/pitt-diamond-qtech/pittqlabsys.git (push)
```

### **Step 2: Daily Development (Maximum Freedom)**
```bash
# Jannet creates a feature branch for her work
git checkout -b jannet-features
git push origin jannet-features

# She creates a new device controller
# File: src/Controller/cryostat_controller.py
class CryostatController(Device):
    """
    Temperature controller for cryostat setup.
    
    Hardware: Lakeshore 336 temperature controller
    Communication: RS232 serial connection
    """
    
    def __init__(self, settings):
        super().__init__(settings)
        self.serial_port = settings.get('serial_port', 'COM3')
        self.baud_rate = settings.get('baud_rate', 9600)
        # ... implementation details
    
    def set_temperature(self, temp_kelvin):
        """Set target temperature in Kelvin."""
        # ... implementation
    
    def read_temperature(self):
        """Read current temperature."""
        # ... implementation

# She commits her work with descriptive messages
git add src/Controller/cryostat_controller.py
git commit -m "[cryo] Add Lakeshore 336 cryostat temperature controller

- Implements RS232 communication protocol
- Adds temperature setpoint and readback functions
- Includes safety interlocks for temperature limits
- Tested with mock hardware"

git push origin jannet-features
```

### **Step 3: Creating an Experiment**
```bash
# Sarah creates a new experiment that uses her cryostat
# File: src/Model/experiments/cryo_odmr.py
class CryoODMRExperiment(Experiment):
    """
    ODMR experiment with temperature control.
    
    Hardware Dependencies:
    - cryostat: For temperature control
    - microwave: For frequency sweeps
    - adwin: For data acquisition
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('temperature', 4.2, float, 'Temperature in Kelvin'),
        Parameter('start_freq', 2.87e9, float, 'Start frequency (Hz)'),
        Parameter('stop_freq', 2.88e9, float, 'Stop frequency (Hz)'),
        # ... more parameters
    ]
    
    _DEVICES = {
        'cryostat': 'cryostat',
        'microwave': 'microwave', 
        'adwin': 'adwin'
    }
    
    def __init__(self, devices, **kwargs):
        super().__init__(devices=devices, **kwargs)
        self.cryostat = self.devices['cryostat']['instance']
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
    
    def _function(self):
        """Run ODMR experiment at specified temperature."""
        # Set temperature
        self.cryostat.set_temperature(self.settings['temperature'])
        
        # Wait for temperature to stabilize
        time.sleep(30)
        
        # Run ODMR sweep
        # ... experiment logic
        
        # Return to room temperature
        self.cryostat.set_temperature(300)

# She commits this too
git add src/Model/experiments/cryo_odmr.py
git commit -m "[cryo] Add temperature-controlled ODMR experiment

- Integrates cryostat controller with ODMR measurements
- Adds temperature stabilization and safety checks
- Includes example usage and documentation
- Tested with mock hardware"

git push origin jannet-features
```

### **Step 4: Creating an Example Script**
```bash
# Sarah creates an example script for others to use
# File: examples/cryo_odmr_example.py
#!/usr/bin/env python3
"""
Cryo ODMR Example

This script demonstrates how to run temperature-controlled ODMR measurements.
"""

def create_devices(use_real_hardware=False, config_path=None):
    """Create device instances using device config manager."""
    if use_real_hardware:
        from src.core.device_config import load_devices_from_config
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        devices = {}
        for device_name, device_instance in loaded_devices.items():
            devices[device_name] = {'instance': device_instance}
        return devices
    else:
        # Mock devices for testing
        from src.Controller import MockCryostatController, MockSG384Generator, MockAdwinGoldDevice
        return {
            'cryostat': {'instance': MockCryostatController()},
            'microwave': {'instance': MockSG384Generator()},
            'adwin': {'instance': MockAdwinGoldDevice()}
        }

def run_cryo_odmr(use_real_hardware=False):
    """Run cryo ODMR experiment."""
    devices = create_devices(use_real_hardware)
    
    experiment = CryoODMRExperiment(
        devices=devices,
        name="CryoODMR_Example",
        settings={
            'temperature': 4.2,
            'start_freq': 2.87e9,
            'stop_freq': 2.88e9,
            'step_freq': 1e6
        }
    )
    
    print("Starting cryo ODMR experiment...")
    experiment.run()
    print("Experiment completed!")

if __name__ == "__main__":
    run_cryo_odmr(use_real_hardware=False)  # Test with mock hardware

# She commits this
git add examples/cryo_odmr_example.py
git commit -m "[cryo] Add example script for cryo ODMR experiment

- Demonstrates temperature-controlled ODMR measurements
- Includes both mock and real hardware support
- Shows proper device initialization and configuration
- Ready for lab members to use and modify"

git push origin jannet-features
```

### **Step 5: Testing Her Work**
```bash
# Sarah tests her new device controller
python examples/cryo_odmr_example.py
# Output: "Starting cryo ODMR experiment..."
#         "Experiment completed!"

# She tests with mock hardware first (always safe!)
python examples/cryo_odmr_example.py --real-hardware
# Tests with real hardware when available

# She runs the existing test suite to make sure she didn't break anything
python -m pytest tests/
# All tests pass - great!

# She runs quality assessment to see how her code measures up
python scripts/assess_quality.py --commits 5
# This helps her learn good practices and identify areas for improvement
```

### **Step 6: Collaborative Development in Cryo Setup**
```bash
# Jannet announces her work in lab chat
# "Hey cryo team! I've added a cryostat controller and cryo ODMR experiment 
#  in the jannet-features branch. Check it out and let me know what you think!"

# Other cryo team members can now:
# 1. Clone the shared cryo repo: git clone https://github.com/duttlab-sys/pittqlabsys-cryo.git
# 2. Check out her branch: git checkout jannet-features
# 3. Test her cryostat controller with their experiments
# 4. Provide feedback and suggestions
# 5. Create their own branches for improvements

# Example: Tristan wants to add confocal scanning at low temperature
git checkout -b feature/cryo-confocal-scan
# He develops his confocal experiment using Jannet's cryostat controller
# He commits and pushes his work
git add src/Model/experiments/cryo_confocal_scan.py
git commit -m "[cryo] Add confocal scanning at low temperature

- Uses Jannet's cryostat controller for temperature control
- Implements 2D scanning with temperature stabilization
- Adds safety checks for cryogenic conditions
- Tested with mock hardware"

git push origin feature/cryo-confocal-scan

# Jannet reviews Tristan's work and provides feedback
# They collaborate to integrate their experiments
# Eventually, when both features are working well, they merge to main
```

### **Step 7: Merging to Cryo Setup Main Branch**
```bash
# After testing and collaboration, Jannet merges her cryostat controller to main
git checkout main
git merge jannet-features
git push origin main

# Tristan also merges his confocal work
git checkout main
git merge feature/cryo-confocal-scan
git push origin main

# Now the pittqlabsys-cryo main branch contains:
# - Jannet's cryostat controller
# - Jannet's cryo ODMR experiment
# - Tristan's cryo confocal scan experiment
# - Any other cryo table experiments from the team

# The cryo team continues developing new features in branches
# and merging to main when they're stable and tested
```

### **Step 8: Contributing to Lab-wide Code (When Ready)**
After several months of testing and refinement in the cryo setup, the team decides their cryostat controller would benefit the entire lab:

```bash
# Jannet syncs with upstream to get latest changes
git fetch upstream
git merge upstream/main
git push origin main

# She runs quality assessment before creating PR
python scripts/assess_quality.py --commits 10
# Addresses any major issues before submitting

# She creates a comprehensive PR to the main repository
# PR Title: "Add Lakeshore 336 cryostat temperature controller and cryo ODMR experiment"
# 
# PR Description:
# "This PR adds temperature control capabilities to the lab's experiment suite.
# 
# ## Changes
# - New CryostatController device for Lakeshore 336 temperature controller
# - CryoODMRExperiment for temperature-controlled ODMR measurements  
# - Example script demonstrating usage
# - Comprehensive documentation and error handling
# 
# ## Testing
# - [x] Tested with mock hardware
# - [x] Tested with real Lakeshore 336 controller
# - [x] All existing tests pass
# - [x] New functionality tested
# 
# ## Benefits
# - Enables low-temperature measurements for entire lab
# - Standardizes cryostat control across different experiments
# - Provides safety interlocks and error handling
# - Easy to use with existing experiment framework"

# She waits for review from @gurudevdutt
# After approval, her code becomes part of the lab-wide codebase!
```

### **Key Takeaways from Jannet's Experience:**
1. **Started with her own fork** - maximum freedom to experiment
2. **Used feature branches** - `jannet-features` for organized development and collaboration
3. **Used descriptive commit messages** - easy to track changes
4. **Tested thoroughly** - mock hardware first, then real hardware
5. **Created example scripts** - made her work easy for others to use
6. **Collaborated with cryo team** - shared branches for feedback and integration
7. **Merged to setup main** - when features were stable and tested
8. **Contributed to lab-wide** - only after extensive testing and team approval

This shows the **three-level workflow**:
- **Individual branches** - for experimental development
- **Setup main branch** - for stable, tested features for that setup
- **Lab-wide main** - for features that benefit the entire lab

**Freedom to innovate, collaboration within setups, quality when sharing lab-wide!**

## 🔄 **Three-Level Workflow Summary**

### **Level 1: Individual Development (Maximum Freedom)**
1. **Fork main repo** with descriptive name for your setup
2. **Create feature branches** for experimental work
3. **Work freely** - no restrictions, break things, iterate quickly
4. **Test with mock hardware** for rapid development

### **Level 2: Setup Collaboration (Team Coordination)**
5. **Share branches** with setup team members
6. **Collaborate and integrate** experiments within the setup
7. **Merge to setup main** when features are stable and tested
8. **Sync weekly** with upstream main to get lab-wide features

### **Level 3: Lab-wide Contribution (Quality Control)**
9. **Contribute back** when you have valuable features for entire lab
10. **Test thoroughly** before lab-wide contributions
11. **Document changes** appropriately
12. **Wait for review** and approval

**Remember**: 
- **Your branches** are your playground for experimentation
- **Setup main** is your team's stable foundation
- **Lab-wide main** is our shared foundation for everyone
