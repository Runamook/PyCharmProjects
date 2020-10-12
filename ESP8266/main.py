import pulse_detector as pd

base_agrs = {
    'interval': 100,
    'cache_file': 'hall_sensor.txt',
    'reset_timer': 100
}

http_args = {
    'http_server': '192.168.1.79'
}

temp_args = {
    'temp_sensor_pin': 4,       # D2
    # 'temp_adjustment': 0        # Value to add to the sensor data
}

m = pd.PulseDetector(pulse_pin=5, **base_agrs)
m.set_http_params(**http_args)
m.set_temp_params(**temp_args)
m.main()
