#!/usr/bin/env python3

# Read a file containing a log of modbus activity.
# This can either be from a man-in-the-middle logger
# (ie listen on 8899, connect to real device, then pass everything through, recording to a file)
# or just a new connect which just records all traffic (exploiting the fact that the
# givenergy dongle appears to broadcast all modbus messages to all connected tcp clients).
# eg can use socat
#   socat -x -r binfile TCP-LISTEN:8899 TCP:host:8899   # in the middle
#   socat -x -u TCP:host:8899 CREATE:binfile            # spy

import gzip
import logging
import sys

from givenergy_modbus.exceptions import ExceptionBase
from givenergy_modbus.pdu.framer import ClientFramer
# from givenergy_modbus.framer import ClientFramer
from givenergy_modbus.model.plant import Plant
from givenergy_modbus.model.inverter import Inverter
from givenergy_modbus.pdu import TransparentResponse, HeartbeatRequest
from givenergy_modbus.model.register import HR, IR

_logger = logging.getLogger(__name__)

class MyPlant(Plant):
    def registers_updated(self, reg, count, values):
        print(reg, count)

def replay():
    """Read modbus frames from a file"""

    plant = MyPlant()

    for file in sys.argv[1:]:
        framer = ClientFramer()
        if file.endswith('.gz'):
            log = gzip.GzipFile(file, "rb")
        else:
            log = open(file, mode='rb')
        try:
            while len(frame := log.read(300)) > 0:
                try:
                    for message in framer.decode(frame):
                        print(message)
                        if isinstance(message, HeartbeatRequest):
                            pass
                        if isinstance(message, TransparentResponse):
                            #before = message.check
                            #encoded = message.encode()
                            #after = message.check
                            #print(f"{before:04x} -- {after:04x}")
                            plant.update(message)
                except (ExceptionBase, NotImplementedError) as e:
                    print(e)
        except EOFError as e:  # can happen if reading incomplete gzip files
            print(e)
        log.close()

        # plant.detect_batteries()
        # Now iterate over all inverter registers, showing last known state
        inv = plant.inverter
        x = inv.get('i_battery')
        for reg, val in inv.getall():
            print(reg, val)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: replay2.py binfile ...")
    replay()
