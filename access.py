#!/usr/bin/env python3
import signal, requests
from sys import exit
from json import load as jsondb
from time import sleep, time
from platform import machine

class Dummy(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        if attr.isupper():
            return 1
        return lambda *args: print("{}.{}: {}"
                                   .format(self.name, attr,repr(args)))

if machine().startswith("arm"):
    import RPi.GPIO as GPIO
else:
    GPIO = Dummy("GPIO")

PINS = {
    "door": 7,
    "green": 8,
    "red": 10
}

def quit(signum, frame):
    GPIO.cleanup()
    print()
    exit()

def hasAccess(cuid):
    try:
        # /acls/ must only be accessible by the door client
        aclr = requests.get("https://space.bo.x0.rs/acls/hm.json")
        aclr = (aclr.ok, aclr)
    except:
        aclr = (False, None)

    if aclr[0]:
        with open("acldb.json", "w+") as db:
            # XXX check if valid json first, we don't want garbage
            db.write(aclr[1].text)
        acl = aclr[1].json()
    else:
        print("Request failed")
        acl = jsondb(open("acldb.json"))

    if cuid in acl.keys():
        return True

    return False

def sesame(decision):
    if decision:
        print("Granted")
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output([PINS["door"], PINS["green"]], value)
            if value:
                sleep(3)
    else:
        print("Denied")
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["red"], value)
            if value:
                sleep(3)

GPIO.setmode(GPIO.BOARD)
signal.signal(signal.SIGINT, quit)

GPIO.setup(list(PINS.values()), GPIO.OUT)

attempt = 0

while True:
    cuid = input()

    # Make sure we discard attempts
    now = time() 
    if now - attempt > 6:
        sesame(len(cuid) == 10 and cuid.isdigit() and hasAccess(cuid))
        attempt = now
