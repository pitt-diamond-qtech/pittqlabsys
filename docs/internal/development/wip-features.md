# WIP Features in Development

## 🚧 **Work In Progress - Do Not Merge to Main Yet**

This document tracks features currently in development on the `dutt-features` branch that are not yet ready for production.

### **Device Validation Fallback Handling** (WIP - UNTESTED)
**Branch**: `dutt-features`  
**Commit**: `c276a1a`  
**Status**: Implemented but not tested  
**Risk Level**: Medium  

**Description**: Added fallback handling for devices without `validate_parameter` method to prevent misleading "success" feedback.

**Changes**:
- Added `'no_validation'` state (yellow background) for devices missing validation
- Added `'no_device'` state (gray background) when no device found
- Updated visual feedback system with warning states
- Added informative GUI history messages

**Testing Required**:
- [ ] Test with devices that have `validate_parameter` (SG384) - should work normally
- [ ] Test with devices that don't have `validate_parameter` (MCLNanoDrive, etc.) - should show yellow warning
- [ ] Test with parameters that have no device - should show gray info
- [ ] Verify GUI history messages are clear and helpful
- [ ] Check that warning states don't interfere with normal operation

**Files Modified**:
- `src/View/windows_and_widgets/widgets.py` (NumberClampDelegate)

**Next Steps**:
1. Test on lab PC with real hardware
2. Verify all device types work correctly
3. Confirm visual feedback is clear and helpful
4. Once tested and validated, merge to main branch

---

**Last Updated**: October 10, 2025  
**Branch**: `main` (production-ready code only)
