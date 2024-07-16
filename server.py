"""
A very crude modbus server which might give the appearance of
being an inverter to client scripts. Can be given different
register snapshots to give it different personalities.

Should support concurrent connections - not something I need,
but basically falls out free. Note that it does *not* send
responses to all connected clients, only the one that made
the request.

Changes to holding registers should persist while the script runs,
but will not be preserved between runs - each launch will start from
the clean state.

Does not implement heartbeat requests. I don't need that, but
if someone was implementing a brand new client from scratch,
it might be useful to add that. Shouldn't be hard - just
a time-limit stored in each InverterEmulator instance (one
per connection), and then the main loop can check whether
any of the connections need to be tested.
"""

import selectors
import socket

from typing import ClassVar, Sequence

from givenergy_modbus.model.register import Register, HR, IR
from givenergy_modbus.pdu.framer import ServerFramer
from givenergy_modbus.pdu.transparent import (
    READINPUT,
    READHOLDING,
    WRITEHOLDING,
    TransparentResponse,
    ReadInputRegistersResponse,
    ReadHoldingRegistersResponse,
    WriteHoldingRegisterResponse,
)

# You can set these to your local dongle and inverter serial numbers,
# and that way the transmitted binary should be identical to that
# sent by the inverter itself.
# TODO: get the inverter serial from HR(13)..HR(17)
DONGLE_SERIAL='WH1234G567'
INVERTER_SERIAL='FD9876G543'

# global variables
myplant: "Plant" = None   # singleton instance
mysel = selectors.DefaultSelector()


class RegisterBlock:
    """One contiguous block of input or holding registers."""

    # The set of slave addresses that the register is visible to
    # eg AIO only does 0x11, whereas hybrids also respond on 0x30, 0x31, 0x32 and maybe others.
    # For hybrid batteries, it would be 0x32 + battery number
    slave_addresses: Sequence[int]

    # first register, eg HR(0), IR(60)
    base: Register

    # set of values - array for holding registers, any sequence type for input registers
    values: Sequence[int]

    def __init__(self, slave_addresses, base, values):
        self.slave_addresses = slave_addresses
        self.base = base
        self.values = values

    def __repr__(self):
        return f"RegisterBlock({self.slave_addresses}, {self.base}, (...)"

class Plant:
    """Abstract base class for a plant."""

    # A plant is just modelled as a collection of register blocks
    # For any request, just need to search through the blocks to
    # find the one targetted.

    # provided by specific plant sub-classes
    regblocks: ClassVar[Sequence[RegisterBlock]]

    # lookup table to choose appropriate TransparentResponse class
    # for any given request (based on transparent function code within).
    _lut: ClassVar[dict[int, TransparentResponse]] = {
        READINPUT: ReadInputRegistersResponse,
        READHOLDING: ReadHoldingRegistersResponse,
        WRITEHOLDING: WriteHoldingRegisterResponse,
    }

    def find_block(self, request):
        """Find the block which contains the register(s) addressed by the request"""

        # TODO - this rejects requests where count goes beyond supported registers
        # should we instead, say, return just the registers available ?
        # When asked for a holding register that doesn't exist, inverter seems
        # to just ignore the request. But if asked for a range that starts valid
        # and becomes invalid, should we ignore it, or give an error ?

        for b in self.regblocks:
            if (request.slave_address in b.slave_addresses and
                request.register_class is type(b.base) and
                request.base_register >= int(b.base) and
                request.base_register + request.register_count <=  int(b.base) + len(b.values)
            ):
                return b
        return None

    def process_request(self, request):
        """Given a TransparentRequest, compose a suitable TransparentResponse."""

        block = self.find_block(request)
        if block is None:
            print("no register block found for ", request)
            return None

        # otherwise we now need to construct a suitable response
        offs = request.base_register - int(block.base)
        count = request.register_count

        tfc = request.transparent_function_code
        if tfc == WRITEHOLDING:
            block.values[offs] = request.register_values[0]

        cls = self._lut[tfc]
        response = cls(slave_address = request.slave_address,
                       base_register = request.base_register,
                       register_count = request.register_count,
                       register_values = block.values[offs:offs + count],
                       inverter_serial_number = INVERTER_SERIAL,
                       data_adapter_serial_number = DONGLE_SERIAL,
                       )
        return response

class HybridG3(Plant):
    """A concrete plant representing a third-gen hybrid (5kW, firmware 309/3015)"""

    regblocks = (
        # holding registers 0-359
        RegisterBlock(
            (0x11, 0x30, 0x31, 0x32), HR(0), [
                # 0-59
                0x2001, 0x0003, 0x0c32, 0x0000, 0x0000, 0xc350, 0x0e10, 0x0001, 0x4446, 0x3232,
                0x3332, 0x4730, 0x3334, 0x4644, 0x3233, 0x3237, 0x4734, 0x3036, 0x0bc7, 0x0135,
                0x0001, 0x0135, 0x0002, 0x0000, 0xc000, 0x0042, 0x1770, 0x0001, 0x0000, 0x0000,
                0x0011, 0x0001, 0x0004, 0x0007, 0x008c, 0x0018, 0x0007, 0x000f, 0x0016, 0x001a,
                0x0011, 0x0001, 0x0002, 0x0000, 0x0320, 0x0712, 0x0065, 0x0001, 0x0000, 0x0000,
                0x0064, 0x0000, 0x0000, 0x0001, 0x0001, 0x00ba, 0x0834, 0x086f, 0x0001, 0x0001,
                
                # 60-119
                0x0514, 0x001e, 0x001e, 0x0730, 0x0a3e, 0x128e, 0x1450, 0x007d, 0x0032, 0x03e8,
                0x0019, 0x0708, 0x0aaa, 0x125c, 0x1450, 0x007a, 0x0019, 0x0019, 0x0019, 0x0758,
                0x0a14, 0x1298, 0x1446, 0x0a3e, 0x5342, 0x312e, 0x3000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x001e, 0x0212, 0x0001, 0x10e0, 0x16da, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0006, 0x0001,
                0x0004, 0x000d, 0x000a, 0x0000, 0x0004, 0x0001, 0x0050, 0x0000, 0x0000, 0x0000,
                
                # 120-179
                0x0000, 0x0000, 0x0000, 0x0018, 0x0000, 0x0001, 0x0000, 0x0000, 0x0001, 0x0001,
                0x00ff, 0x4e20, 0x00ff, 0x4e20, 0x00ff, 0x4e20, 0x00ff, 0x4e20, 0x09b4, 0x09e2,
                0x0844, 0x0816, 0x0014, 0x0005, 0x096f, 0x08fc, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x000f, 0x0000, 0x0000, 0x0000,
                
                # 180-239
                0x5858, 0x5858, 0x5858, 0x5858, 0x5858, 0x5858, 0x5858, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0001, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                
                # 240-299
                0x0000, 0x0000, 0x0050, 0x0000, 0x0000, 0x0012, 0x0000, 0x0000, 0x000a, 0x0000,
                0x0000, 0x0064, 0x0000, 0x0000, 0x0064, 0x0000, 0x0000, 0x0064, 0x0000, 0x0000,
                0x0064, 0x0000, 0x0000, 0x0064, 0x0000, 0x0000, 0x0064, 0x0000, 0x0000, 0x0064,
                0x0000, 0x0000, 0x0007, 0x0000, 0x0000, 0x001e, 0x0000, 0x0000, 0x0014, 0x0000,
                0x0000, 0x0004, 0x0000, 0x0000, 0x0004, 0x0000, 0x0000, 0x0004, 0x0000, 0x0000,
                0x0004, 0x0000, 0x0000, 0x0004, 0x0000, 0x0000, 0x0004, 0x0000, 0x0000, 0x0004,
                
                # 300-359
                0x000a, 0x0096, 0x1388, 0x3a98, 0x0000, 0x0000, 0x1770, 0x08fc, 0x0e10, 0x0041,
                0x0064, 0x0002, 0x3a98, 0x0064, 0x0064, 0x047e, 0x0ac8, 0x0001, 0x0001, 0x0212,
                0x07a3, 0x13b0, 0x0000, 0x0000, 0x0000, 0x0000, 0x1374, 0x0028, 0x1392, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
                0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
            ]),

        # IR 0-59
        RegisterBlock(
            (0x11, 0x30, 0x31, 0x32), IR(0), (
                0x0001, 0x0000, 0x0000, 0x10b8, 0x0000, 0x0983, 0x0000, 0x7ec0, 0x0000, 0x0000,
                0x000f, 0x0000, 0x9fbc, 0x1391, 0x0005, 0x0acb, 0x25da, 0x0037, 0x0000, 0x0037,
                0x0000, 0x0000, 0x81e1, 0x0000, 0x0147, 0x007c, 0x006c, 0x0000, 0x2dd9, 0x0000,
                0x0000, 0x0000, 0x0000, 0x5ead, 0x0000, 0x004d, 0x004b, 0x0048, 0x0000, 0x0000,
                0x0000, 0x017c, 0x0147, 0x006f, 0x00af, 0x0000, 0xbcd6, 0x0000, 0x18ab, 0x0001,
                0x13f0, 0x02d7, 0x017e, 0x0981, 0x1390, 0x0175, 0x00dc, 0x0000, 0x002e, 0x0008,
            )),

        # first battery
        RegisterBlock(
            (0x32,), IR(60), (
                0x0c79, 0x0c7c, 0x0c7e, 0x0c7e, 0x0c76, 0x0c7b, 0x0c7c, 0x0c78, 0x0c7c, 0x0c7c,
                0x0c7c, 0x0c7e, 0x0c79, 0x0c7b, 0x0c78, 0x0c79, 0x00da, 0x00dd, 0x00df, 0x00d3,
                0xc7ab, 0x00e3, 0x0000, 0xc780, 0x0000, 0x4d91, 0x0000, 0x48a8, 0x0000, 0x0666,
                0x0000, 0x0e10, 0x0000, 0x0000, 0x0000, 0x0013, 0x00c9, 0x0010, 0x0bc7, 0x0000,
                0x0008, 0x0000, 0x48a8, 0x00de, 0x00da, 0x402c, 0x3e94, 0x0000, 0x0000, 0x0000,
                0x4446, 0x3232, 0x3332, 0x4730, 0x3334, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
            )),

        # null entries for missing battery slots, since the inverter is expected
        # to return a block of zeros for a missing register.
        # Note that rubikcube's app seems to ask for battery from
        # 0x30 and 0x31 as well as higher ones
        RegisterBlock(
            (0x30, 0x31, 0x33, 0x34, 0x35, 0x36, 0x37), IR(60), (0,) * 60),
    )



# socket handling:


class SocketHandler:
    """Abstract base class for handling sockets.
    An instance is attached to the selector as the
    key for each registered socket, and then ready()
    is invoked when the socket becomes readable.
    """

    socket: socket.socket

    def __init__(self, socket):
        self.socket = socket

    def ready(self):
        """Invoked when the socket indicates that it is readable."""
        raise NotImplementedError()

class InverterEmulator(SocketHandler):
    """Emulate just enough of an inverter to fool client."""

    # each instance needs its own framer
    framer: ServerFramer

    def __init__(self, socket):
        super().__init__(socket)
        self.framer = ServerFramer()

    def ready(self):
        data = self.socket.recv(1024)
        if data:
            # print('  received {!r}'.format(data))
            for request in self.framer.decode(data):
                response = myplant.process_request(request)
                print(request, " -> ", response)
                if response is not None:
                    self.socket.send(response.encode())
        else:
            # Interpret empty result as closed connection
            print('  closing')
            mysel.unregister(self.socket)
            self.socket.close()

class ServerSocketHandler(SocketHandler):
    """Accept new connections."""
    def ready(self):
        sock, addr = self.socket.accept()
        print('accept({})'.format(addr))
        sock.setblocking(False)
        mysel.register(sock, selectors.EVENT_READ, InverterEmulator(sock))

if __name__ == "__main__":

    # TODO: once we have more personalities, choose one from the command line
    myplant = HybridG3()

    # establish listener socket, and add it to the select list

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind(('', 8899))
    server.listen(5)

    mysel = selectors.DefaultSelector()
    mysel.register(server, selectors.EVENT_READ, ServerSocketHandler(server))

    # now just service socket activity forever
    while True:
        print('waiting for I/O')
        for key, mask in mysel.select(timeout=5):
            handler = key.data
            handler.ready()  # either accept new socket, or process request
