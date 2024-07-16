#!/usr/bin/env python3

# Set regs from command line.
# Intended to have same interface as the api one.

import asyncio
import logging
import socket
import sys
from typing import Callable, Dict, List, Optional, Tuple

from givenergy_modbus.exceptions import CommunicationError, ExceptionBase
from givenergy_modbus.client.client import Client
from givenergy_modbus.model.plant import Plant, Inverter
from givenergy_modbus.pdu import WriteHoldingRegisterRequest

_logger = logging.getLogger(__name__)


class MyPlant(Plant):
    def holding_register_updated(self, reg: int, value: int):
        print(f'holding reg {reg} now {value}')

async def get_set_regs():

    shorthand = {
        'cp': 'battery_charge_limit',
        'dp': 'battery_discharge_limit',
        'pt': 'battery_pause_mode',
        }

    client = Client(sys.argv[1], 8899)
    plant = MyPlant()
    plant.max_holding_reg=300
    client.plant=plant

    # first pass over the args to see if any are reads
    query = False
    for arg in [x.split('=', 1) for x in sys.argv[2:]]:
        if len(arg) == 1:
            query = True

    await client.connect()
    inverter = None

    if query:
        await client.refresh_plant(True)
        inverter = client.plant.inverter
        
    # another pass over the args, performing each in turn
    settings = []
    for arg in [x.split('=', 1) for x in sys.argv[2:]]:
        reg = arg[0]
        if reg in shorthand:
            reg = shorthand[reg]

        if len(arg) == 1:
            # just retrieve the setting
            print(reg, '=', inverter.get(reg))
        else:
            val = int(arg[1])
            settings.append(client.commands.write_named_register(reg, val))

    if len(settings) > 0:
        client.execute(settings, 2.0, 2)
    await asyncio.sleep(5)

    await client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(get_set_regs())
