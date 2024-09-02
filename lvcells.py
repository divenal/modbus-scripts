#!/usr/bin/env python3

"""Connect to inverter and record cell voltages.

Note that this is low-voltage inverters only. AIO
needs to use different registers.
"""

import asyncio
import logging
import sys
from datetime import datetime

from givenergy_modbus.client.client import Client
from givenergy_modbus.model.plant import Plant
from givenergy_modbus.model.register import IR

_logger = logging.getLogger(__name__)


async def cells():
    """Connect to inverter and loop, displaying cell voltages."""

    # we only need the first page of inverter input registers (for
    # battery power), so don't bother doing a full detect.
    # Also, assume exactly one battery.
    registers = {IR(0)}
    plant = Plant(registers=registers, num_batteries=1)
    client = Client(sys.argv[1], 8899, plant=plant)
    await client.connect()

    while True:
        now = datetime.now()
        await client.refresh_plant(full_refresh=False, retries=4)

        inverter = plant.inverter
        batt = plant.batteries[0]
        print(f"{now.hour:02d}:{now.minute:02d} {batt.soc:3d}% "
              f"{inverter.p_battery:5d} "
              f" {batt.v_cell_01:6.3f}"
              f" {batt.v_cell_02:6.3f}"
              f" {batt.v_cell_03:6.3f}"
              f" {batt.v_cell_04:6.3f}"
              f" {batt.v_cell_05:6.3f}"
              f" {batt.v_cell_06:6.3f}"
              f" {batt.v_cell_07:6.3f}"
              f" {batt.v_cell_08:6.3f}"
              f" {batt.v_cell_09:6.3f}"
              f" {batt.v_cell_10:6.3f}"
              f" {batt.v_cell_11:6.3f}"
              f" {batt.v_cell_12:6.3f}"
              f" {batt.v_cell_13:6.3f}"
              f" {batt.v_cell_14:6.3f}"
              f" {batt.v_cell_15:6.3f}"
              f" {batt.v_cell_16:6.3f}"
              )

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(cells())
