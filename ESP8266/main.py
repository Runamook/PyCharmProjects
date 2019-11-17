import pulse_detector as pd

base_agrs = {
    'interval': 120,
    'cache_file': 'cold_water_cache.txt'
}

http_args = {
    'http_server': '192.168.5.11'
}

m = pd.PulseDetector(pulse_pin=5, **base_agrs)
m.set_http_params(**http_args)
m.main()
