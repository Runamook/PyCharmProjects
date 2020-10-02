import pulse_detector as pd

base_agrs = {
    'interval': 100,
    'cache_file': 'hall_sensor.txt',
    'reset_timer': 100
}

http_args = {
    'http_server': '192.168.1.79'
}

m = pd.PulseDetector(pulse_pin=5, **base_agrs)
m.set_http_params(**http_args)
m.main()
