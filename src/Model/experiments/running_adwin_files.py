from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import get_adwin_binary_path
import time
adwin = AdwinGoldDevice()

try:
    process_number = 1

    if not adwin.is_connected:
        adwin.connect()

    # Proper cleanup like debug script
    print("Cleaning up any existing ADwin process...")
    try:
        adwin.stop_process(process_number)
        time.sleep(0.1)
    except Exception:
        pass
    try:
        adwin.clear_process(process_number)
    except Exception:
        pass
    odmr_pulsed_counter_path = get_adwin_binary_path('adwin_analog_out.TB1')
    adwin.update({'process_1': {'load': str(odmr_pulsed_counter_path)}})
    # Start the counting process
    adwin.start_process(process_number)
    time.sleep(0.1)  # Give process time to start
    print("done setup ADwin counting")

except Exception as e:
    print(f"Failed to setup ADwin counting: {e}")
