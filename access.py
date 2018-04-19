#!/usr/bin/env python3
import signal, requests
from sys import exit
from json import load as jsondb
from time import sleep, time
from platform import machine, platform
from threading import Thread

class Dummy(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        if attr.isupper():
            return 1
        return lambda *args: print("{}.{}: {}"
                                   .format(self.name, attr,repr(args)))

PINS = {
    "door": 7,
    "green": 8,
    "red": 10,
    "key": 11
}

GPIO = Dummy("GPIO")

if machine().startswith("arm") and "ntc" in platform():
    import CHIP_IO.GPIO as GPIO
    PINS = {"door": "CSID0",
            "green": "CSID1",
            "red": "CSID2",
            "key": "CSID3"}
elif machine().startswith("arm"):
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)

def quit(signum, frame):
    GPIO.cleanup()
    print()
    exit()

def hasAccess(cuid):
    try:
        # /acls/ must only be accessible by the door client
        aclr = requests.get("https://space.bo.x0.rs/acls/hm.json", timeout=2)
        aclr = (aclr.ok, aclr)
    except:
        aclr = (False, None)

    acl = None
    if aclr[0]:
        try:
            acl = aclr[1].json()
            with open("acldb.json", "w+") as db:
                db.write(aclr[1].text)
        except:
            pass
    if acl is None:
        print("Request failed, falling back on cache")
        acl = jsondb(open("acldb.json"))

    if cuid in acl.keys():
        return True

    return False

def sesame(decision):
    if decision:
        print("Granted")
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["door"], value)
            GPIO.output(PINS["green"], value)
            if value:
                sleep(5)
        return
    print("Denied")
    for value in (GPIO.HIGH, GPIO.LOW):
        GPIO.output(PINS["red"], value)
        if value:
            sleep(5)

def deadbolt():
    changed = False
    while True:
        opened = GPIO.input(PINS["key"])
        if opened and not changed:
            sesame(True)
            changed = True
        elif not opened and changed:
            changed = False
        sleep(0.5)

def main():
    signal.signal(signal.SIGINT, quit)

    for value in PINS.values():
        GPIO.setup(value, GPIO.OUT)
    GPIO.setup(PINS["key"], GPIO.IN)

    attempt = 0

    Thread(target = deadbolt).start()

    while True:
        cuid = input()

        # Make sure we discard attempts
        now = time()
        if now - attempt > 6:
            sesame(len(cuid) == 10 and cuid.isdigit() and hasAccess(cuid))
            attempt = now

if __name__ == "__main__":
    main()
