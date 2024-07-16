#!/usr/bin/env python3

# This exploits that the fact that the givenergy dongle appears to broadcast
# modbus responses to all connected tcp clients, not just the one that made
# the request. So simply connect and passively watch what comes through.
# This doesn't respond to the heartbeat request, so the connection will get shut
# down after a few minutes.

import asyncio
import gzip
import logging
import socket
import sys
from typing import Callable, Dict, List, Optional, Tuple

from givenergy_modbus.exceptions import CommunicationError, ExceptionBase
from givenergy_modbus.client.client import Client
from givenergy_modbus.client import commands
from givenergy_modbus.model.plant import Plant

_logger = logging.getLogger(__name__)


async def watch():
    """Passively watch modbus traffic."""

    capture = None
    if len(sys.argv) > 2:
        fname = sys,argv[2]
        capture = gzip.GzipFile(fname, "wb") if fname.endswith(".gz") else open(fname, "wb")
    client = Client(sys.argv[1], 8899, recorder=capture)
    await client.watch_plant(None, timeout=5.0, refresh_period=30.0, passive=False, max_batteries=2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(watch())
