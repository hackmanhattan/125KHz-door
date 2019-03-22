# Low-Fi 125kHz RFID access for Hack Manhattan

Requirements:

* [BeagleBone Black](https://beagleboard.org/black) /
  [CHIP](http://getchip.com/) / [Raspberry Pi](https://www.raspberrypi.org/)
* [USB HID (keyboard) 125kHz RFID reader](https://www.amazon.com/Reader-LANMU-125khz-Contactless-Proximity/dp/B07B7H6CQ2/)
* Python 3 &
  [Adafruit_BBIO.GPIO](https://github.com/adafruit/adafruit-beaglebone-io-python) /
  [CHIP_IO.GPIO](https://github.com/xtacocorex/CHIP_IO/) /
  [RPi.GPIO](https://pypi.org/project/RPi.GPIO/)
* Relay / Optocoupler to connect to an electric strike other other door-opening
  mechanism
* A working internet connection for bootstrapping
* systemd (sorry not sorry)

Optional:

* 1 green & 1 red LED and the appropriate resistors
* Deadbolt/key sensor for (non-RFID) legacy access
  ([ours](https://www.amazon.com/gp/product/B01I57HIJ0/))

## Setup

* Place this repo in `/opt/125kHz-door/`
* Put the `125kHz-door.service` in `/etc/systemd/system/`
* Add the appropriate environment variables to `/opt/125kHz-door/envs` if you
  want to override default configuration
* See `access.py` source for wiring. (Yes I'm lazy, it's for 3 different
  boards!)
* Make sure `KHZ125_ACL` URI isn't readable by any IP other than the keyless
  access device

## Configuration (environment variables)

* `KHZ125_ACL`: provide URI to access control list (see next section).
  Default: `https://spacy.hackmanhattan.com/cards/json/1`
* `KHZ125_AUTH`: secret token for `Authorization: Bearer $KHZ125_AUTH`
  headers. Default: not present.
* `KHZ125_JSONDB`: provides path for where the json database is stored.
  Default: `/opt/125kHz-door/acldb.json`, `acldb.json` for "debug" mode
* `KHZ125_TIME`: how long the relay to open the door is turned on. Default: 5
  seconds
* `KHZ125_CACHE`: how long to wait for the HTTPS request to finish until
  falling back onto cache. Default: 0.75
* `KHZ125_NO_DEADBOLT`: if present it disables legacy access support. Default:
  not present.
* `KHZ125_NO_LED`: if present it disables green/red LEDs for status reports.
  Default: not present.
* `KHZ125_READER`: device path to the HID RFID reader

## `acldb.json` Format

125kHz RFID tags have 32bit IDs. The USB keyboard "types" this ID as a number
with leading zeros, hence:

    {
        "0000000001": "description",
        "0004044444": "Not an actual card"
    }
