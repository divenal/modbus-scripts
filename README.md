# modbus-scripts
misc. scripts that work with givenergy-modbus-async. Not at all polished.
Will probably break from time to time.

There are several different versions of the "beta" modbus scripts around. We'll get them consolodated one day. These probably use my latest dev, which is 'dev6' at time of writing.

```
python --version              # need at least 3.10 I think
python -m venv modbus
. modbus/bin/activate         # on windows, I think it's modbus\bin\activate.bat
pip install git+https://github.com/divenal/givenergy-modbus-async@dev6
python lvcells.py 192.168.x.y
```

If you're nervous, could run server.py initially and connect the scripts to
that to test, before connecting to your live inverter. These are only
tested on my gen-3 hybrid inverter.


server.py is a simple modbus server which might be useful for testing/developing
modbus clients. It should be possible to give it different personalities by
feeding it different snapshots of register sets. Currently assumes at least my
'clean6' patches. May work with older versions - only signifcant change is
the location of 'framer' and 'codec' modules.

replay2.py is a simple script I use to feed a captured logfile back through
a plant instance, to recreate all the changes. At the end, you can hack the
code to interrogate things, etc.

setreg.py is was just a quick hack to allow registers to be read/written
from command line.

watch.py just connects to an inverter and watches the world go by. Possibly recording
to a file which can later be played through replay2 above.

lvcells.py displays cell voltages. Only suitable for low-voltage inverters (hybrids, and single-phase AC-coupled). AIO and (I think) 3-phase needs to look at different registers.
