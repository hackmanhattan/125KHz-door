#!/usr/bin/env python3
import signal, requests
from sys import exit
from json import load as jsondb
from time import sleep, time
from platform import machine, platform
from threading import Thread, Lock
from queue import Queue
from os import environ as env

class Dummy(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        if attr.isupper():
            return 0 if attr == "LOW" else 1
        return lambda *args: print("{}.{}: {}"
                                   .format(self.name, attr,repr(args)))
PINS = {"door": "P8_8",
        "green": "P8_10",
        "red": "P8_12",
        "key": "P8_14"}

if "125KHZ_TIME" not in env:
    env["125KHZ_TIME"] = "5"

if "125KHZ_CACHE" not in env:
    env["125KHZ_CACHE"] = "0.75"

rheaders = {}
if "125KHZ_AUTH" in env:
    rheaders["Authorization"] = "Bearer " + env["125KHZ_AUTH"]

GPIO = Dummy("GPIO")

if machine().startswith("arm") and "bone" in platform():
    import Adafruit_BBIO.GPIO as GPIO
elif machine().startswith("arm") and "ntc" in platform():
    import CHIP_IO.GPIO as GPIO
    PINS = {"door": "CSID0",
            "green": "CSID1",
            "red": "CSID2",
            "key": "CSID3"}
elif machine().startswith("arm"):
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    PINS = {
        "door": 7,
        "green": 8,
        "red": 10,
        "key": 11
    }
elif "125KHZ_ACL" not in env:
    env["125KHZ_ACL"] = "https://space.bo.x0.rs/acls/dev.json"

if "125KHZ_ACL" not in env:
    env["125KHZ_ACL"] = "https://spacy.hackmanhattan.com/cards/json/1"

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

fileio = Lock()

class Download(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.reqs = Queue()
        self.resps = Queue()

    def run(self):
        while True:
            try:
                request = self.reqs.get()
                aclr = request()
                self.resps.put(aclr.json())
                fileio.acquire()
                with open(env["125KHZ_JSONDB"], "w+") as cache:
                    cache.write(aclr.text)
                fileio.release()
            except Exception as e:
                print("Oh noes: {}".format(e))

def hasAccess(cuid, dwnlt):
    acl = None

    dwnlt.reqs.put(lambda: requests.get(env["125KHZ_ACL"], headers=rheaders))
    timeout = time() + float(env["125KHZ_CACHE"])
    while dwnlt.resps.empty() and time() < timeout:
        sleep(0.1)

    if dwnlt.resps.empty():
        print("Request failed, falling back on async cache")
        fileio.acquire()
        with open(env["125KHZ_JSONDB"]) as cache:
            acl = jsondb(cache)
        fileio.release()
        # Because the download was too slow, we discard the queue entry
        Thread(target=lambda: dwnlt.resps.get()).start()
    else:
        acl = dwnlt.resps.get()

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
                sleep(float(env["125KHZ_TIME"]))
        return
    print("Denied")
    if "125KHZ_NO_LED" not in env:
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["red"], value)
            if value:
                sleep(float(env["125KHZ_TIME"]))

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
        sensor = Thread(target = deadbolt)
        sensor.daemon = True
        sensor.start()

    db = Download()
    db.start()

    attempt = 0

    while True:
        cuid = input()

        # Make sure we discard attempts
        now = time()
        if now - attempt > 6:
            sesame(len(cuid) == 10 and cuid.isdigit() and hasAccess(cuid, db))
            attempt = now

if __name__ == "__main__":
    main()
