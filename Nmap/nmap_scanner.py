import nmap, json

nm = nmap.PortScanner()
nm.scan("mickeymouseclub.asuscomm.com", arguments="-sU", ports="1194")
print(json.dumps(a, sort_keys=True, indent=4))

"""
{
    "nmap": {
        "command_line": "nmap -oX - -p 1194 -sU mickeymouseclub.asuscomm.com",
        "scaninfo": {
            "udp": {
                "method": "udp",
                "services": "1194"
            }
        },
        "scanstats": {
            "downhosts": "0",
            "elapsed": "1.24",
            "timestr": "Tue Mar 26 18:11:54 2019",
            "totalhosts": "1",
            "uphosts": "1"
        }
    },
    "scan": {
        "119.56.82.237": {
            "addresses": {
                "ipv4": "119.56.82.237"
            },
            "hostnames": [
                {
                    "name": "mickeymouseclub.asuscomm.com",
                    "type": "user"
                },
                {
                    "name": "237.82.56.119.unknown.m1.com.sg",
                    "type": "PTR"
                }
            ],
            "status": {
                "reason": "syn-ack",
                "state": "up"
            },
            "udp": {
                "1194": {
                    "conf": "3",
                    "cpe": "",
                    "extrainfo": "",
                    "name": "openvpn",
                    "product": "",
                    "reason": "udp-response",
                    "state": "open",
                    "version": ""
                }
            },
            "vendor": {}
        }
    }
}
"""

