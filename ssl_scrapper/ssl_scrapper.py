import ssl, socket, pprint, urllib.request
import http.client

pp = pprint.PrettyPrinter(indent = 4)


def printer(hostname):
    s = socket.create_connection((hostname, 443))
    context = ssl.create_default_context()
    ss = context.wrap_socket(s, server_hostname = hostname)

    cert = ss.getpeercert(hostname)
    pp.pprint(cert)

    return cert


li = ['nag.ru', 'valetudo.ru', 'https://expert.ru', 'vz.ru']


r = urllib.request.urlopen(li[2])

