# Visual Feedback Test

This test isolates the visual feedback issue from the full GUI complexity to help diagnose why background colors are not appearing in the main application.

## Files

- `test_visual_feedback.py` - Main test application
- `run_visual_feedback_test.py` - Script to run the test with proper Python path
- `README.md` - This file

## How to Run

```bash
cd examples/debug
python run_visual_feedback_test.py
```

Or directly:
```bash
cd examples/debug
python test_visual_feedback.py
```

## What It Tests

1. **QTreeWidget with custom delegate** - Mimics the main application setup
2. **Mock device validation** - Simulates SG384 frequency clamping (> 4.1 GHz)
3. **Visual feedback** - Tests orange background for clamped values, green for success
4. **Debug logging** - Comprehensive logging to trace the issue

## Expected Behavior

1. **Click on frequency value** - Should open editor
2. **Enter value > 4.1 GHz** (e.g., `6.0`) - Should clamp to 4.1 GHz
3. **Orange background** - Should appear for clamped values
4. **Green background** - Should appear for valid values
5. **Auto-clear** - Background should clear after 3 seconds

## Debug Output

The test provides detailed logging:
- Delegate method calls
- Model data changes
- Visual feedback application
- Background color setting
- Viewport updates

## Troubleshooting

If visual feedback doesn't work:

1. **Check console logs** - Look for missing debug messages
2. **Verify delegate installation** - Should see "TestDelegate initialized"
3. **Check model data** - Should see FEEDBACK_ROLE and BackgroundRole being set
4. **Verify viewport updates** - Should see viewport().update() calls

## Common Issues

1. **No background color** - Model data not being set correctly
2. **Color appears briefly** - Viewport update not working
3. **No delegate calls** - Delegate not installed properly
4. **Validation not working** - Mock device not connected properly
