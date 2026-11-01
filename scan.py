#!/usr/bin/env python3
import os
import sys
import argparse
from bleak import BleakScanner
import asyncio
import json
import collections
import getpass
from ble_decoders import decode_ble_advertisment, ENV_BTHOME_KEY

parser = argparse.ArgumentParser()
parser.add_argument("timeout", help="Scan time", type=int)
parser.add_argument("--decode", help="Try to decode advertisement data", action="store_true")
parser.add_argument("--json", help="JSON output", action="store_true")
parser.add_argument("--filter", help="Filter MAC addresses starting with FILTER", default="")
parser.add_argument("--ask-bthome-key", help=f"Ask for BTHome AES key instead of reading it from {ENV_BTHOME_KEY} env variable", action="store_true")
parser.add_argument("--loop", help="Automatically restart scanning after timeout", action="store_true")
args = parser.parse_args()

async def scan(timeout):
    return await BleakScanner.discover(timeout=timeout, return_adv=True)

def scan_parse():
    """Scan, parse and print out the result"""

    # dict of {address: (BLEDevice, AdvertisementData)} (https://bleak.readthedocs.io/en/latest/api.html#bleak.backends.device.BLEDevice)
    devices_and_adv = asyncio.run(scan(args.timeout))
    devices_sorted = sorted(devices_and_adv.items(), key=lambda x: x[1][1].rssi, reverse=True)

    ret = collections.OrderedDict()

    for address, (device, adv_data) in devices_sorted:
        if args.filter and not device.address.lower().startswith(args.filter.lower()):
            continue

        device_name = (device.name or "Unknown")
        ret[device.address] = {
            'name' : device_name,
            'rssi' : str(adv_data.rssi),
        }

        decoded_data = None
        if args.decode:
            decoded_data = decode_ble_advertisment(adv_data, device.address)
            ret[device.address]['data'] = decoded_data
                
        if not args.json:
            print(device.address)
            print("\tName: " + device_name)
            print("\tRSSI: " + str(adv_data.rssi))
            if decoded_data:
                print("\tService Data: "+ str(decoded_data))

    if args.json:
        print(json.dumps(ret, indent=2))

try:
    # Ask for BTHome key if needed and store it in ENV
    if args.ask_bthome_key:
        os.environ[ENV_BTHOME_KEY] = getpass.getpass("Enter BTHome AES key: ")

    while True:
        scan_parse()

        if not args.loop:
            break

except KeyboardInterrupt:
    print("\nCTRL+C pressed. Exiting...", file=sys.stderr)
    exit(1)
