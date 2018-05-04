# Low-Fi 125kHz RFID access for Hack Manhattan

Requirements:

* [CHIP](http://getchip.com/), [Raspberry Pi](https://www.raspberrypi.org/), or
  [BeagleBone Black](https://beagleboard.org/black)
* [USB HID (keyboard) 125kHz RFID reader](https://www.amazon.com/Reader-LANMU-125khz-Contactless-Proximity/dp/B07B7H6CQ2/)
* Python 3 & [CHIP_IO.GPIO](https://github.com/xtacocorex/CHIP_IO/),
  [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) or
  [Adafruit_BBIO.GPIO](https://github.com/adafruit/adafruit-beaglebone-io-python)
* Relay / Optocoupler to connect to an electric strike other other door-opening
  mechanism
* A working internet connection for bootstrapping
* systemd (sorry not sorry)

Optional:

* 1 green & 1 red LED and the appropriate resistors
* Deadbolt/key sensor for (non-RFID) legacy access
  ([ours](https://www.amazon.com/gp/product/B01I57HIJ0/))

## Setup

* Put `override.conf` in `/etc/systemd/system/getty@tty1.service.d/override.conf`
  and add the appropriate environment variables if you want to override default
  configuration
* `access.py` in `/opt/125kHz-door/`
* See `access.py` source for wiring. (Yes I'm lazy, it's for 3 different
  boards!)
* Make sure `125KHZ_ACL` URI isn't readable by any IP other than the keyless
  access device

## Configuration (environment variables)

* `125KHZ_ACL`: provide URI to access control list (see next section). Default:
  `https://space.bo.x0.rs/acls/hm.json`
* `125KHZ_JSONDB`: provides path for where the json database is stored.
   Default: `/opt/125kHz-door/acldb.json`, `acldb.json` for "debug" mode
* `125KHZ_TIME`: how long the relay to open the door is turned on. Default: 5
  seconds
* `125KHZ_NO_DEADBOLT`: if present it disables legacy access support. Default:
   not present.
* `125KHZ_NO_LED`: if present it disables green/red LEDs for status reports.
  Default: not present.

## `acldb.json` Format

125kHz RFID tags have 32bit IDs. The USB keyboard "types" this ID as a number
with leading zeros, hence:

    {
        "0000000001": "description",
        "0004044444": "Not an actual card"
    }
