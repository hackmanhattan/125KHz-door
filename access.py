#!/usr/bin/env python3
import signal, requests
from sys import exit
from json import load as jsondb
from time import sleep, time
from platform import machine, platform
from threading import Thread
from os import environ as env

class Dummy(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        if attr.isupper():
            return 0 if attr == "LOW" else 1
        return lambda *args: print("{}.{}: {}"
                                   .format(self.name, attr,repr(args)))

PINS = {"door": "CSID0",
        "green": "CSID1",
        "red": "CSID2",
        "key": "CSID3"}

if "125KHZ_ACL" not in env:
    env["125KHZ_ACL"] = "https://space.bo.x0.rs/acls/hm.json"

GPIO = Dummy("GPIO")

if machine().startswith("arm") and "ntc" in platform():
    import CHIP_IO.GPIO as GPIO
elif machine().startswith("arm") and "bone" in platform():
    import Adafruit_BBIO.GPIO as GPIO
    PINS = {"door": "P8_14",
            "green": "P8_15",
            "red": "P8_16",
            "key": "P8_17"}
elif machine().startswith("arm"):
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    PINS = {
        "door": 7,
        "green": 8,
        "red": 10,
        "key": 11
    }

if "125KHZ_NO_DEADBOLT" in env:
    PINS.pop("key")
if "125KHZ_NO_LED" in env:
    [PINS.pop(k) for k in ["green", "red"]]

if len(GPIO.__dict__) == 1 and "125KHZ_JSONDB" not in env:
    env["125KHZ_JSONDB"] = "acldb.json"
elif "125KHZ_JSONDB" not in env:
    env["125KHZ_JSONDB"] = "/opt/125kHz-door/acldb.json"

def quit(signum, frame):
    GPIO.cleanup()
    print()
    exit()

def hasAccess(cuid):
    try:
        # /acls/ must only be accessible by the door client
        aclr = requests.get(env["125KHZ_ACL"], timeout=2)
        aclr = (aclr.ok, aclr)
    except:
        aclr = (False, None)

    acl = None
    if aclr[0]:
        try:
            acl = aclr[1].json()
            with open(env["125KHZ_JSONDB"], "w+") as db:
                db.write(aclr[1].text)
        except:
            pass
    if acl is None:
        print("Request failed, falling back on cache")
        acl = jsondb(open(env["125KHZ_JSONDB"]))

    if cuid in acl.keys():
        return True

    return False

def sesame(decision):
    if decision:
        print("Granted")
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["door"], value)
            if "125KHZ_NO_LED" not in env:
                GPIO.output(PINS["green"], value)
            if value:
                sleep(5)
        return
    print("Denied")
    if "125KHZ_NO_LED" not in env:
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["red"], value)
            if value:
                sleep(5)

def deadbolt():
    changed = False
    while True:
        opened = GPIO.input(PINS["key"])
        if opened and not changed:
            sleep(1)
            sesame(True)
            changed = True
        elif not opened and changed:
            changed = False
        sleep(0.5)

def main():
    signal.signal(signal.SIGINT, quit)

    for value in PINS.values():
        GPIO.setup(value, GPIO.OUT)

    if "125KHZ_NO_DEADBOLT" not in env:
        GPIO.setup(PINS["key"], GPIO.IN)
        Thread(target = deadbolt).start()

    attempt = 0

    while True:
        cuid = input()

        # Make sure we discard attempts
        now = time()
        if now - attempt > 6:
            sesame(len(cuid) == 10 and cuid.isdigit() and hasAccess(cuid))
            attempt = now

if __name__ == "__main__":
    main()
