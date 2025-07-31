# Git Branch Strategy

## Current Branch Structure

### `dutt-role-based` (Current Role-Based Development)
**Contains:** Complete role-based experiment system + all improvements
- ✅ Role-based experiment architecture (`device_roles.py`, `role_based_experiment.py`)
- ✅ Experiment configuration management (`experiment_config.py`)
- ✅ New ODMR experiment using role-based system
- ✅ Comprehensive examples directory with working demo
- ✅ Extensive documentation for role-based system
- ✅ Configuration files for different labs
- ✅ Comprehensive tests for role-based system
- ✅ All original improvements (pathlib, microwave generators, etc.)

### `dutt-features` (Original Improvements Only)
**Contains:** Original improvements without role-based system
- ✅ Path handling improvements with pathlib
- ✅ New microwave generator classes (SG384, Windfreak SynthUSBII)
- ✅ Improved testing with pytest fixtures
- ✅ Documentation improvements
- ✅ Professional README and acknowledgments
- ❌ No role-based experiment system
- ❌ No examples directory
- ❌ No role-based experiments

### `main` (Stable/Release)
**Contains:** Original codebase
- ❌ Missing many improvements from feature branches
- ❌ Needs testing and merging of improvements first

## Recommended Workflow

### Phase 1: Test Original Improvements
1. **Switch to:** `dutt-features`
2. **Test:** All the original improvements (pathlib, microwave generators, etc.)
3. **Fix:** Any issues found during testing
4. **Merge:** To `main` when stable

### Phase 2: Evaluate Role-Based System
1. **Stay on:** `dutt-role-based` 
2. **Test:** Role-based experiment system
3. **Decide:** Whether to adopt role-based approach or stick with original
4. **Merge:** If approved, merge role-based system to `main`

## Branch Commands

```bash
# Switch to original improvements only
git checkout dutt-features

# Switch to role-based system (current development)
git checkout dutt-role-based

# Switch to main (stable)
git checkout main

# Push role-based work to remote
git push origin dutt-role-based

# Create new branch from specific commit
git checkout -b new-branch-name commit-hash
```

## What Each Branch Represents

### `dutt-features`
- **Purpose:** Conservative improvements to existing system
- **Risk:** Low - maintains existing architecture
- **Benefit:** Immediate improvements without major changes
- **Use Case:** When you want to improve the current system incrementally

### `dutt-role-based` 
- **Purpose:** Major architectural change with role-based system
- **Risk:** Higher - new architecture needs validation
- **Benefit:** More flexible, hardware-agnostic experiments
- **Use Case:** When you want to make experiments more portable across labs

## Next Steps

1. **Test `dutt-features`** thoroughly
2. **Merge to `main`** when stable
3. **Evaluate role-based system** in `dutt-role-based`
4. **Decide on architecture** based on testing results
5. **Merge chosen approach** to `main`

## File Organization

### Original Improvements (dutt-features)
- Path handling with pathlib
- New microwave generator classes
- Improved testing
- Documentation improvements
- Professional README

### Role-Based System (dutt-role-based)
- Everything from original improvements
- Role-based experiment architecture
- Configuration management system
- Examples and demonstrations
- Comprehensive documentation 