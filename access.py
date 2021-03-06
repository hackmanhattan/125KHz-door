#!/usr/bin/env python3
import signal, subprocess, evdev
from sys import exit
from json import load as jsondb, loads as jsons
from time import sleep, time
from platform import machine, platform
from threading import Thread, Lock
from queue import Queue
from os import environ as env
from os.path import exists

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

if "KHZ125_READER" not in env:
    env["KHZ125_READER"] = "/dev/input/by-id/usb-Sycreader_RFID" \
                           "_Technology_Co.__Ltd_SYC_ID_IC_USB_Reader_" \
                           "08FF20140315-event-kbd"

if "KHZ125_TIME" not in env:
    env["KHZ125_TIME"] = "5"

if "KHZ125_CACHE" not in env:
    env["KHZ125_CACHE"] = "0.75"

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
elif "KHZ125_ACL" not in env:
    env["KHZ125_ACL"] = "https://space.bo.x0.rs/acls/dev.json"

if "KHZ125_ACL" not in env:
    env["KHZ125_ACL"] = "https://spacy.hackmanhattan.com/cards/json/1"

if "KHZ125_NO_DEADBOLT" in env:
    PINS.pop("key")
if "KHZ125_NO_LED" in env:
    [PINS.pop(k) for k in ["green", "red"]]

if len(GPIO.__dict__) == 1 and "KHZ125_JSONDB" not in env:
    env["KHZ125_JSONDB"] = "acldb.json"
elif "KHZ125_JSONDB" not in env:
    env["KHZ125_JSONDB"] = "/opt/125kHz-door/acldb.json"

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
                self.resps.put(jsons(aclr))
                fileio.acquire()
                with open(env["KHZ125_JSONDB"], "w+") as cache:
                    cache.write(aclr)
                fileio.release()
            except Exception as e:
                print("Oh noes: {}".format(e))

def hasAccess(cuid, dwnlt):
    acl = None

    # I feel conflicted about using curl here, but we keep having issues with
    # the requests library in a thread, where it locks up and the queue just
    # keeps growing
    cmd = ["curl", env["KHZ125_ACL"]]

    if "KHZ125_AUTH" in env:
        cmd[1:1] = ["-H", "Authorization: Bearer " + env["KHZ125_AUTH"]]

    print(cmd)
    dwnlt.reqs.put(lambda: subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                                     .stdout.read().decode("utf-8"))
    timeout = time() + float(env["KHZ125_CACHE"])
    while dwnlt.resps.empty() and time() < timeout:
        sleep(0.1)

    if dwnlt.resps.empty():
        print("Request failed, falling back on async cache")
        fileio.acquire()
        with open(env["KHZ125_JSONDB"]) as cache:
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
            if "KHZ125_NO_LED" not in env:
                GPIO.output(PINS["green"], value)
            if value:
                sleep(float(env["KHZ125_TIME"]))
        return
    print("Denied")
    if "KHZ125_NO_LED" not in env:
        for value in (GPIO.HIGH, GPIO.LOW):
            GPIO.output(PINS["red"], value)
            if value:
                sleep(float(env["KHZ125_TIME"]))

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
    try:
        while not exists(env["KHZ125_READER"]):
            sleep(1)
        device = evdev.InputDevice(env["KHZ125_READER"])
    except PermissionError:
        print("Insufficent permissions, run me as root!")
        exit(1)

    device.grab()

    def quit(signum, frame):
        device.ungrab()
        GPIO.cleanup()
        print("Bye")
        exit()

    signal.signal(signal.SIGINT, quit)

    for value in PINS.values():
        GPIO.setup(value, GPIO.OUT)

    if "KHZ125_NO_DEADBOLT" not in env:
        GPIO.setup(PINS["key"], GPIO.IN)
        sensor = Thread(target = deadbolt)
        sensor.daemon = True
        sensor.start()

    db = Download()
    db.start()

    attempt = 0

    cuid = ""

    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY and event.value == 1:
            e_code = event.code - 1
            if e_code >= 1 and e_code <= 10:
                if e_code == 10:
                    cuid += str(0)
                else:
                    cuid += str(e_code)
            elif e_code == 27: # enter minus one
                now = time()

                if now - attempt > 6:
                    sesame(len(cuid) == 10 and cuid.isdigit() and
                           hasAccess(cuid, db))
                    attempt = now

                cuid = ""

if __name__ == "__main__":
    main()
