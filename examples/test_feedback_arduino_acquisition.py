#!/usr/bin/env python3
"""
Test FeedbackArduino Acquisition Script

This script tests the FeedbackArduino device and experiments to verify they work
correctly with real or mock hardware. It performs:
- Device connection and ID verification
- Status and info queries
- Single-shot triggered acquisition (acquire block)
- Brief live plotting test
- Data validation

Usage:
    python test_feedback_arduino_acquisition.py
    python test_feedback_arduino_acquisition.py --real-hardware
    python test_feedback_arduino_acquisition.py --real-hardware --com-port COM10
    python test_feedback_arduino_acquisition.py --live-duration 5.0
"""

import argparse
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.feedback_arduino import FeedbackArduino
from src.Model.experiments.feedback_arduino_acquire_block import FeedbackArduinoAcquireBlock
from src.Model.experiments.feedback_arduino_live_plot import FeedbackArduinoLivePlot


def test_device_connection(arduino, use_real_hardware=True):
    """Test basic device connection and identification.

    Args:
        arduino: FeedbackArduino device instance
        use_real_hardware: Whether using real hardware or mock

    Returns:
        bool: True if test passes
    """
    print("\n" + "=" * 60)
    print("TEST 1: DEVICE CONNECTION")
    print("=" * 60)

    try:
        # Check connection status
        is_connected = arduino.is_connected
        print(f"✅ Connection status: {'Connected' if is_connected else 'Not connected'}")

        if not is_connected and use_real_hardware:
            print("❌ Device not connected!")
            return False

        if use_real_hardware:
            # Query device ID
            print("\n🔍 Querying device ID...")
            device_id = arduino._query('id')
            print(f"   Device ID: {device_id}")

            if 'SIS Arduino_Analog_I/O' in device_id:
                print("✅ Device ID verification passed")
            else:
                print(f"⚠️  Unexpected device ID: {device_id}")
                return False
        else:
            print("✅ Mock device initialized successfully")

        return True

    except Exception as e:
        print(f"❌ Device connection test failed: {e}")
        return False


def test_status_and_info(arduino, use_real_hardware=True):
    """Test status and info queries.

    Args:
        arduino: FeedbackArduino device instance
        use_real_hardware: Whether using real hardware

    Returns:
        bool: True if test passes
    """
    print("\n" + "=" * 60)
    print("TEST 2: STATUS AND INFO QUERIES")
    print("=" * 60)

    try:
        # Query status
        print("\n🔍 Querying device status...")
        status = arduino.read_probes('status')

        print(f"   ADC overload: {status['ADC_overload']}")
        print(f"   ADC DMA buffer overflow: {status['ADC_DMA_buffer_overflow']}")
        print(f"   USB output buffer overflow: {status['USB_output_buffer_overflow']}")
        print(f"   Any errors: {status['any_error']}")

        if status['any_error'] and use_real_hardware:
            print("⚠️  Device reports errors - may need power cycle")
        else:
            print("✅ Status query successful")

        # Query info (WARNING: this resets error flags!)
        print("\n🔍 Querying device info...")
        print("   ⚠️  Note: This clears error flags on the device")
        info = arduino.read_probes('info')

        print(f"   ADC channels: {info['adc_n_channels']}")
        print(f"   ADC sample rate: {info['adc_sample_rate_hz']/1e3:.1f} kHz")
        print(f"   ADC clock: {info['adc_clock_hz']/1e6:.1f} MHz")
        print(f"   Max samples: {info['max_samples']}")
        print(f"   DAC channels: {info['dac_n_channels']}")

        if info['adc_n_channels'] == 4:
            print("✅ Info query successful - 4 channels confirmed")
        else:
            print(f"⚠️  Expected 4 ADC channels, got {info['adc_n_channels']}")

        return True

    except Exception as e:
        print(f"❌ Status/info query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_acquire_block(arduino, use_real_hardware=True):
    """Test single-shot triggered acquisition.

    Args:
        arduino: FeedbackArduino device instance
        use_real_hardware: Whether using real hardware

    Returns:
        bool: True if test passes
    """
    print("\n" + "=" * 60)
    print("TEST 3: SINGLE-SHOT ACQUISITION (SCOPE MODE)")
    print("=" * 60)

    try:
        # Create experiment
        print("\n⚙️  Creating FeedbackArduinoAcquireBlock experiment...")
        experiment = FeedbackArduinoAcquireBlock(
            name='test_acquire_block',
            devices={'arduino': {'instance': arduino}},
            settings={
                'decimator': 100,
                'usb_data_n': 256,
                'trig_channel': 0,
                'trig_level': 0,
                'trig_hyst': 10,
                'max_wait_s': 10.0 if use_real_hardware else 1.0,
                'poll_dt': 0.02,
                'save': False,
            }
        )

        print("✅ Experiment created")
        print(f"   Decimator: {experiment.settings['decimator']}")
        print(f"   Data block size: {experiment.settings['usb_data_n']} int16 values")
        print(f"   Trigger channel: {experiment.settings['trig_channel']}")
        print(f"   Trigger level: {experiment.settings['trig_level']}")

        # Run experiment
        print("\n▶️  Running acquisition...")
        if not use_real_hardware:
            print("   (Using mock data)")

        experiment.run()

        # Check results
        if experiment.data is None:
            print("❌ No data acquired!")
            return False

        if 'error' in experiment.data:
            print(f"❌ Acquisition error: {experiment.data['error']}")
            return False

        # Validate data
        print("\n📊 Acquisition results:")
        print(f"   Channels: {experiment.data['n_channels']}")
        print(f"   Samples per channel: {experiment.data['n_samples']}")

        if use_real_hardware:
            print(f"   ADC sample rate: {experiment.data['adc_sample_rate_hz']/1e3:.1f} kHz")

        # Show sample statistics for each channel
        print("\n   Channel statistics:")
        for ch_name in ['chA', 'chB', 'chC', 'chD']:
            ch_data = experiment.data[ch_name]
            print(f"   {ch_name}: min={np.min(ch_data):6d}, max={np.max(ch_data):6d}, "
                  f"mean={np.mean(ch_data):7.1f}, std={np.std(ch_data):6.1f}")

        # Show first few samples
        print("\n   First 5 samples:")
        print("   idx |   chA  |   chB  |   chC  |   chD")
        print("   ----+--------+--------+--------+--------")
        for i in range(min(5, experiment.data['n_samples'])):
            print(f"   {i:3d} | {experiment.data['chA'][i]:6d} | "
                  f"{experiment.data['chB'][i]:6d} | "
                  f"{experiment.data['chC'][i]:6d} | "
                  f"{experiment.data['chD'][i]:6d}")

        print("\n✅ Single-shot acquisition test passed")
        return True

    except Exception as e:
        print(f"❌ Acquire block test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_plot(arduino, duration=2.0, use_real_hardware=True):
    """Test live plotting with continuous acquisition.

    Args:
        arduino: FeedbackArduino device instance
        duration: How long to run live acquisition (seconds)
        use_real_hardware: Whether using real hardware

    Returns:
        bool: True if test passes
    """
    print("\n" + "=" * 60)
    print("TEST 4: LIVE PLOTTING (FILTER MODE)")
    print("=" * 60)

    try:
        # Create experiment
        print(f"\n⚙️  Creating FeedbackArduinoLivePlot experiment (duration={duration}s)...")
        experiment = FeedbackArduinoLivePlot(
            name='test_live_plot',
            devices={'arduino': {'instance': arduino}},
            settings={
                'bandwidth': 1,
                'decimator': 100,
                'usb_data_n': 256,
                'pause_dt': 0.01,
                'history_blocks': 100,
                'max_runtime': duration,
                'save': False,
            }
        )

        print("✅ Experiment created")
        print(f"   Bandwidth: {experiment.settings['bandwidth']}")
        print(f"   Decimator: {experiment.settings['decimator']}")
        print(f"   Data block size: {experiment.settings['usb_data_n']} int16 values")
        print(f"   History blocks: {experiment.settings['history_blocks']}")

        # Run experiment
        print(f"\n▶️  Running live acquisition for {duration}s...")
        if not use_real_hardware:
            print("   (Using mock data)")

        start_time = time.time()
        experiment.run()
        elapsed = time.time() - start_time

        print(f"   Elapsed time: {elapsed:.2f}s")

        # Check results
        if experiment.data is None:
            print("❌ No data acquired!")
            return False

        if 'error' in experiment.data:
            print(f"❌ Acquisition error: {experiment.data['error']}")
            return False

        # Validate data
        print("\n📊 Live acquisition results:")
        print(f"   Blocks acquired: {experiment.data['block_count']}")
        print(f"   'None' responses: {experiment.data['none_count']}")
        print(f"   Block rate: {experiment.data['blocks_per_second']:.2f} blocks/s")
        print(f"   Samples per block: {experiment.data['n_samples_per_block']}")

        if use_real_hardware:
            print(f"   ADC sample rate: {experiment.data['adc_sample_rate_hz']/1e3:.1f} kHz")

        # Check history buffers
        hist_len = experiment.data['max_hist_samples']
        print(f"   History buffer size: {hist_len} samples")

        # Show rolling buffer statistics (ignoring NaN values from initialization)
        print("\n   Rolling buffer statistics (most recent data):")
        for ch_name in ['histA', 'histB', 'histC', 'histD']:
            ch_hist = experiment.data[ch_name]
            valid_data = ch_hist[~np.isnan(ch_hist)]
            if len(valid_data) > 0:
                print(f"   {ch_name}: valid={len(valid_data):4d}, "
                      f"min={np.min(valid_data):7.1f}, max={np.max(valid_data):7.1f}, "
                      f"mean={np.mean(valid_data):7.1f}")

        if experiment.data['block_count'] > 0:
            print("\n✅ Live plotting test passed")
            return True
        else:
            print("⚠️  No blocks acquired during live test")
            return False

    except Exception as e:
        print(f"❌ Live plot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feedback_arduino(use_real_hardware=False, com_port='COM10', live_duration=2.0):
    """Run all FeedbackArduino tests.

    Args:
        use_real_hardware: Use real Arduino hardware vs mock
        com_port: Serial COM port for Arduino
        live_duration: Duration for live plot test

    Returns:
        bool: True if all tests pass
    """
    print("\n" + "=" * 60)
    print("FEEDBACK ARDUINO TEST SUITE")
    print("=" * 60)
    print(f"Hardware mode: {'Real' if use_real_hardware else 'Mock'}")
    if use_real_hardware:
        print(f"COM port: {com_port}")
    print(f"Live test duration: {live_duration}s")

    all_passed = True

    # Initialize device
    print("\n🔧 Initializing FeedbackArduino device...")
    try:
        if use_real_hardware:
            arduino = FeedbackArduino(
                name='test_arduino',
                settings={'com_port': com_port}
            )
            print(f"✅ Real hardware initialized on {com_port}")
        else:
            # Mock device - we'll patch the serial connection
            from unittest.mock import Mock, patch, MagicMock

            with patch('src.Controller.feedback_arduino.serial.Serial'):
                import serial
                mock_serial = MagicMock()
                mock_serial.is_open = True
                mock_serial.in_waiting = 0
                mock_serial.read.return_value = b'SIS Arduino_Analog_I/O 20160119 TEST *14\n'
                serial.Serial.return_value = mock_serial

                arduino = FeedbackArduino(
                    name='mock_arduino',
                    settings={'com_port': 'COM10'}
                )

                # Set up mock responses for queries
                def mock_query(cmd):
                    if cmd == 'status':
                        return 'I 0 0 0 *3f'
                    elif cmd == 'start' or cmd == 'stop':
                        return 'OK *13'
                    else:
                        return 'OK *13'

                arduino._query = mock_query

                # Mock status/info probes
                arduino.read_probes = lambda key: {
                    'status': {
                        'ADC_overload': False,
                        'ADC_DMA_buffer_overflow': False,
                        'USB_output_buffer_overflow': False,
                        'any_error': False,
                    },
                    'info': {
                        'adc_n_channels': 4,
                        'adc_sample_rate_hz': 140000.0,
                        'adc_clock_hz': 14000000.0,
                        'max_samples': 8192,
                        'dac_n_channels': 0,
                    }
                }.get(key, {})

                # Mock data acquisition
                def mock_get_data(**kwargs):
                    return {
                        'kind': 'binary',
                        'samples_by_channel': np.random.randint(-1000, 1000, (64, 4), dtype=np.int16),
                        'n_channels': 4,
                        'n_samples_per_channel': 64,
                    }

                def mock_poll_data():
                    if np.random.random() > 0.3:  # 70% success rate
                        return {
                            'kind': 'binary',
                            'samples_by_channel': np.random.randint(-1000, 1000, (64, 4), dtype=np.int16),
                            'n_channels': 4,
                            'n_samples_per_channel': 64,
                        }
                    else:
                        return {'kind': 'none', 'remaining': 50}

                arduino.get_data_block = mock_get_data
                arduino.poll_data_block = mock_poll_data

                print("✅ Mock device initialized")

    except Exception as e:
        print(f"❌ Failed to initialize device: {e}")
        return False

    # Run tests
    tests = [
        ("Device Connection", lambda: test_device_connection(arduino, use_real_hardware)),
        ("Status and Info", lambda: test_status_and_info(arduino, use_real_hardware)),
        ("Acquire Block", lambda: test_acquire_block(arduino, use_real_hardware)),
        ("Live Plot", lambda: test_live_plot(arduino, live_duration, use_real_hardware)),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
            all_passed = all_passed and passed
        except Exception as e:
            print(f"\n❌ {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
            all_passed = False

    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        if use_real_hardware and arduino.is_connected:
            arduino.close()
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed - see details above")

    return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test FeedbackArduino Device and Experiments')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real Arduino hardware (default: use mock)')
    parser.add_argument('--com-port', type=str, default='COM10',
                       help='Serial COM port (default: COM10)')
    parser.add_argument('--live-duration', type=float, default=2.0,
                       help='Duration for live plot test in seconds (default: 2.0)')

    args = parser.parse_args()

    print("🎯 FeedbackArduino Test Suite")
    print(f"🔧 Hardware: {'Real' if args.real_hardware else 'Mock'}")
    if args.real_hardware:
        print(f"📡 COM Port: {args.com_port}")
    print(f"⏱️  Live test duration: {args.live_duration}s")

    success = test_feedback_arduino(
        use_real_hardware=args.real_hardware,
        com_port=args.com_port,
        live_duration=args.live_duration
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
