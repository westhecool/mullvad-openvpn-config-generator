import urllib.request
import json
import os
import ssl
import sys

PROTO = 'udp'
PORT = '1194'
if len(sys.argv) > 1:
    PORT = sys.argv[1]
if PORT == '80' or PORT == '443':
    PROTO = 'tcp'
COMMON_CONFIG = f'''client
dev tun
resolv-retry infinite
nobind
persist-key
persist-tun
verb 3
remote-cert-tls server
ping 10
ping-restart 60
sndbuf 524288
rcvbuf 524288
cipher AES-256-GCM
tls-cipher TLS-DHE-RSA-WITH-AES-256-GCM-SHA384
proto {PROTO}
auth-user-pass
ignore-unknown-option block-outside-dns
remote-random
'''

if not os.path.exists('mullvad_ca.crt'):
    print('You are missing the mullvad_ca.crt file. See the README to know how to obtain it.')
    exit(1)

CA = open('mullvad_ca.crt').read()

def write_config(name, remotes):
    f = open(name, 'w')
    f.write(COMMON_CONFIG)
    f.write(remotes)
    f.write(f'<ca>\n{CA}\n</ca>')
    f.close()

r = urllib.request.urlopen('https://api.mullvad.net/app/v1/relays', context=ssl.create_default_context())
relays = json.loads(r.read())
by_country = {}
by_city = {}
if not os.path.exists('servers/by-hostname'):
    os.makedirs('servers/by-hostname')
for relay in relays['openvpn']['relays']:
    if not relay['active']:
        continue
    write_config(f'servers/by-hostname/{relay['hostname']}.ovpn', f'remote {relay["ipv4_addr_in"]} {PORT} # {relay["hostname"]}\n')
    location = relays['locations'][relay['location']]
    if location['country'] not in by_country:
        by_country[location['country']] = []
    by_country[location['country']].append(relay)
    if not location['country'] in by_city:
        by_city[location['country']] = {}
    if not location['city'] in by_city[location['country']]:
        by_city[location['country']][location['city']] = []
    by_city[location['country']][location['city']].append(relay)

if not os.path.exists('servers/by-country'):
    os.makedirs('servers/by-country')
for country in by_country:
    remotes = ''
    for relay in by_country[country]:
        remotes += f'remote {relay["ipv4_addr_in"]} {PORT} # {relay["hostname"]}\n'
    write_config(f'servers/by-country/{country}.ovpn', remotes)

if not os.path.exists('servers/by-city'):
    os.makedirs('servers/by-city')
for country in by_city:
    for city in by_city[country]:
        remotes = ''
        for relay in by_city[country][city]:
            remotes += f'remote {relay["ipv4_addr_in"]} {PORT} # {relay["hostname"]}\n'
        write_config(f'servers/by-city/{country} - {city}.ovpn', remotes)

print('Successfully generated OpenVPN configs. Your usename will be your account id and your password will be "m".')