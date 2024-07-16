# modbus-scripts
misc. scripts that work with givenergy-modbus-async. Not at all polished. Will probably break from time to time.


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
