# The MIT License (MIT)
#
# Copyright (c) 2017 Dean Miller for Adafruit Industries.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import re
import logging



def get_default_bus():
    """Return the default bus number based on the device platform.  For a
    Raspberry Pi either bus 0 or 1 (based on the Pi revision) will be returned.
    For a Beaglebone Black the first user accessible bus, 1, will be returned.
    """
    if pi_revision() == 1:
        # Revision 1 Pi uses I2C bus 0.
        return 0
    else:
        # Revision 2 Pi uses I2C bus 1.
        return 1

def pi_revision():
    """Detect the revision number of a Raspberry Pi, useful for changing
    functionality like default I2C bus based on revision."""

    with open('/proc/cpuinfo', 'r') as infile:
        for line in infile:

            match = re.match('Revision\s+:\s+.*(\w{4})$', line, flags=re.IGNORECASE)
            if match and match.group(1) in ['0000', '0002', '0003']:
                # Return revision 1 if revision ends with 0000, 0002 or 0003.
                return 1
            elif match:
                # Assume revision 2 if revision ends with any other 4 chars.
                return 2
        # Couldn't find the revision, throw an exception.
        raise RuntimeError('Could not determine Raspberry Pi revision.')

def get_i2c_device(address, busnum=None, i2c_interface=None, **kwargs):
    """Return an I2C device for the specified address and on the specified bus.
    If busnum isn't specified, the default I2C bus for the platform will attempt
    to be detected.
    """
    if busnum is None:
        busnum = get_default_bus()
    return Device(address, busnum, i2c_interface, **kwargs)


class Device(object):
    """Class for communicating with an I2C device using the adafruit-pureio pure
    python smbus library, or other smbus compatible I2C interface. Allows reading
    and writing 8-bit, 16-bit, and byte array values to registers
    on the device."""
    def __init__(self, address, busnum, i2c_interface=None):
        """Create an instance of the I2C device at the specified address on the
        specified I2C bus number."""
        self._address = address
        if i2c_interface is None:
            # Use pure python I2C interface if none is specified.
            import smbus
            self._bus = smbus.SMBus(busnum)
        else:
            # Otherwise use the provided class to create an smbus interface.
            self._bus = i2c_interface(busnum)
        self._logger = logging.getLogger('Adafruit_I2C.Device.Bus.{0}.Address.{1:#0X}' \
                                .format(busnum, address))

    def writeRaw8(self, value):
        """Write an 8-bit value on the bus (without register)."""
        value = value & 0xFF
        self._bus.write_byte(self._address, value)
        self._logger.debug("Wrote 0x%02X",
                     value)

    def write8(self, register, value):
        """Write an 8-bit value to the specified register."""
        value = value & 0xFF
        self._bus.write_byte_data(self._address, register, value)
        self._logger.debug("Wrote 0x%02X to register 0x%02X",
                     value, register)

    def write16(self, register, value):
        """Write a 16-bit value to the specified register."""
        value = value & 0xFFFF
        self._bus.write_word_data(self._address, register, value)
        self._logger.debug("Wrote 0x%04X to register pair 0x%02X, 0x%02X",
                     value, register, register+1)

    def writeList(self, register, data):
        """Write bytes to the specified register."""
        self._bus.write_i2c_block_data(self._address, register, data)
        self._logger.debug("Wrote to register 0x%02X: %s",
                     register, data)

    def readList(self, register, length):
        """Read a length number of bytes from the specified register.  Results
        will be returned as a bytearray."""
        results = self._bus.read_i2c_block_data(self._address, register, length)
        self._logger.debug("Read the following from register 0x%02X: %s",
                     register, results)
        return results

    def readRaw8(self):
        """Read an 8-bit value on the bus (without register)."""
        result = self._bus.read_byte(self._address) & 0xFF
        self._logger.debug("Read 0x%02X",
                    result)
        return result

    def readU8(self, register):
        """Read an unsigned byte from the specified register."""
        result = self._bus.read_byte_data(self._address, register) & 0xFF
        self._logger.debug("Read 0x%02X from register 0x%02X",
                     result, register)
        return result

    def readS8(self, register):
        """Read a signed byte from the specified register."""
        result = self.readU8(register)
        if result > 127:
            result -= 256
        return result

    def readU16(self, register, little_endian=True):
        """Read an unsigned 16-bit value from the specified register, with the
        specified endianness (default little endian, or least significant byte
        first)."""
        result = self._bus.read_word_data(self._address,register) & 0xFFFF
        self._logger.debug("Read 0x%04X from register pair 0x%02X, 0x%02X",
                           result, register, register+1)
        # Swap bytes if using big endian because read_word_data assumes little
        # endian on ARM (little endian) systems.
        if not little_endian:
            result = ((result << 8) & 0xFF00) + (result >> 8)
        return result

    def readS16(self, register, little_endian=True):
        """Read a signed 16-bit value from the specified register, with the
        specified endianness (default little endian, or least significant byte
        first)."""
        result = self.readU16(register, little_endian)
        if result > 32767:
            result -= 65536
        return result

    def readU16LE(self, register):
        """Read an unsigned 16-bit value from the specified register, in little
        endian byte order."""
        return self.readU16(register, little_endian=True)

    def readU16BE(self, register):
        """Read an unsigned 16-bit value from the specified register, in big
        endian byte order."""
        return self.readU16(register, little_endian=False)

    def readS16LE(self, register):
        """Read a signed 16-bit value from the specified register, in little
        endian byte order."""
        return self.readS16(register, little_endian=True)

    def readS16BE(self, register):
        """Read a signed 16-bit value from the specified register, in big
        endian byte order."""
        return self.readS16(register, little_endian=False)

if __name__ == '__main__':
    v=get_default_bus()
    device=get_i2c_device(0x69,v)
    device.write8(0x0c,0x0c)
    result=device.readU8(0x0c)
    print result
