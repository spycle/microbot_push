"""MicroBot Client."""
import logging
import asyncio
from typing import Optional
from typing import Any
import async_timeout
import bleak
from bleak import BleakClient
from bleak import BleakScanner
from bleak import discover
from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import random, string
import configparser
from configparser import NoSectionError
import os
from os.path import expanduser
import binascii
from binascii import hexlify

_LOGGER: logging.Logger = logging.getLogger(__package__)
CONNECT_LOCK = asyncio.Lock()
DEFAULT_TIMEOUT = 20
DEFAULT_RETRY_COUNT = 10
DEFAULT_SCAN_TIMEOUT = 30

SVC1831 = '00001831-0000-1000-8000-00805f9b34fb'
CHR2A89 = '00002a89-0000-1000-8000-00805f9b34fb'

class MicroBotApiClient:

    def __init__(
        self, bdaddr: str, config: str
    ) -> None:
        """MicroBot Client."""
        self._bdaddr = bdaddr
        self._client = None
        if self._client == None:
            self.discover()
        self._scanner = BleakScanner()
        self._scanner.register_detection_callback(self.detection_callback)
        self._default_timeout = DEFAULT_TIMEOUT
        self._retry = 10
        self._token = None
        self._config = expanduser(config)
        self.__loadToken()
        self._depth = 50
        self._duration = 0
        self._mode = 0
        self._is_on = None

    @property
    def is_on(self):
        return self._is_on

    async def detection_callback(
            self,
            device: BLEDevice,
            advertisement_data: AdvertisementData,
        ) -> None:
            if device.address == self._bdaddr:
                self._client = BleakClient(device, timeout=20)
                _LOGGER.debug("MicroBot object: %s", self._client)
                await self._scanner.stop()

    async def discover(
        self, retry: int = DEFAULT_RETRY_COUNT, scan_timeout: int = DEFAULT_SCAN_TIMEOUT
    ) -> None:
        """Find switchbot device"""
        _LOGGER.debug("Running discovery")
        await self._scanner.start()
        await asyncio.sleep(scan_timeout)
        _LOGGER.debug("Stopped discovery")

        if devices is None:
            if retry < 1:
                _LOGGER.error(
                    "Scanning for MicroBot devices failed. Stop trying", exc_info=True
                )
                return self._adv_data

            _LOGGER.warning(
                "Error scanning for MicroBot devices. Retrying (remaining: %d)",
                retry,
            )
            await asyncio.sleep(DEFAULT_RETRY_TIMEOUT)
            return await self.discover(retry - 1, scan_timeout)

    async def notification_handler(self, handle: int, data: bytes) -> None:
        tmp = binascii.b2a_hex(data)[4:4+36]
        if b'0f0101' == tmp[:6] or b'0f0102' == tmp[:6]:
            bdaddr = tmp[6:6+12]
            bdaddr_rcvd = bdaddr.decode()
            _LOGGER.debug("ack with bdaddr: %s", bdaddr_rcvd) 
            await self.getToken()
        elif b'1fff' == tmp[0:4] and b'0000000000000000000000' != tmp[6:6+22] and b'00000000' == tmp[28:36]:
            token = tmp[4:4+32]
            self._token = token.decode()
            _LOGGER.debug("ack with token")
            await self._client.stop_notify(CHR2A89)
            self.__storeToken()
        else:
            _LOGGER.debug(f'Received response at {handle=}: {hexlify(data, ":")!r}')

    async def notification_handler2(self, handle: int, data: bytes) -> None:
        _LOGGER.debug(f'Received response at {handle=}: {hexlify(data, ":")!r}')

    async def is_connected(self, timeout=20):
        try:
            return await asyncio.wait_for(
                self._client.is_connected(),
                self._default_timeout if timeout is None else timeout)
            return True
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            _LOGGER.error(e)
        else:
            False

    async def _do_connect(self, timeout=20):
        x = await self.is_connected()
        if x == True:
            _LOGGER.debug("Already connected")
        else:
            async with CONNECT_LOCK:
                await self._client.connect(timeout=20)
            _LOGGER.debug("Connected!")

    async def _do_disconnect(self):
        if self.is_connected():
            await self._client.disconnect()

    async def connect(self, init=False, timeout=20):
        retry = self._retry
        while True:
            _LOGGER.debug("Connecting to %s", self._bdaddr)
            try:
                await asyncio.wait_for(
                    self._do_connect(),
                    self._default_timeout if timeout is None else timeout)
                await self.__setToken(init) 
                break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("Failed to connect: %s", e)
                    break
                retry = retry - 1
                _LOGGER.debug("Retrying connect")
                await asyncio.sleep(0.5)
                     
    async def disconnect(self, timeout=20):
        _LOGGER.debug("Disconnecting from %s", self._bdaddr)
        try:
            await asyncio.wait_for(
                self._do_disconnect(),
                self._default_timeout if timeout is None else timeout)
        except Exception as e:
            _LOGGER.error("error: %s", e)

    def __loadToken(self):
        _LOGGER.debug("Looking for token")
        config = configparser.ConfigParser()
        config.read(self._config)
        bdaddr = self._bdaddr.lower().replace(':', '')
        if config.has_option('tokens', bdaddr):
            self._token = config.get('tokens', bdaddr)
            _LOGGER.debug("Token found")

    def __storeToken(self):
        config = configparser.ConfigParser()
        config.read(self._config)
        if not config.has_section('tokens'):
            config.add_section('tokens')
        bdaddr = self._bdaddr.lower().replace(':', '')
        config.set('tokens', bdaddr, self._token)
        os.umask(0)
        with open(os.open(self._config, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as file:
            config.write(file)
        _LOGGER.debug("Token saved to file")

    def hasToken(self):
        if self._token == None:
            _LOGGER.debug("no token")
            return False
        else:
            _LOGGER.debug("Has token")
            return True

    async def __initToken(self):
        _LOGGER.debug("Generating token")
        try:
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"00010040e20100fa01000700000000000000")
            bar1 = list(hex1)
            hex2 = binascii.a2b_hex(id+"0fffffffffffffffffffffffffff"+self.__randomid(32))
            bar2 = list(hex2)
            _LOGGER.debug("Waiting for bdaddr notification")
            await self._client.start_notify(CHR2A89, self.notification_handler)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
        except Exception as e:
            _LOGGER.error("failed to init token: %s", e)

    async def __setToken(self, init):
        if init:
            _LOGGER.debug("init set to True")
            await self.__initToken()
        else:
            if self.hasToken():
                _LOGGER.debug("Setting token")
                try:
                    id = self.__randomid(16)
                    hex1 = binascii.a2b_hex(id+"00010000000000fa0000070000000000decd")
                    bar1 = list(hex1)
                    hex2 = binascii.a2b_hex(id+"0fff"+self._token)
                    bar2 = list(hex2)
                    await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
                    await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
                    _LOGGER.debug("Token set")
                except Exception as e:
                    _LOGGER.error("Failed to set token: %s", e)

    async def getToken(self):
        _LOGGER.debug("Getting token")
        try:
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"00010040e20101fa01000000000000000000")
            bar1 = list(hex1)
            _LOGGER.debug(bar1)
            hex2 = binascii.a2b_hex(id+"0fffffffffffffffffff0000000000000000")
            bar2 = list(hex2)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
            _LOGGER.warning('touch the button to get a token')
        except Exception as e:
            _LOGGER.error("failed to request token: %s", e)

    def setDepth(self, depth):
        self._depth = depth
        _LOGGER.debug("Depth: %s", depth)

    def setDuration(self, duration):
        self._duration = duration
        _LOGGER.debug("Duration: %s", duration)

    def setMode(self, mode):
        if 'normal' == mode:
            self._mode = 0
        elif 'invert' == mode:
            self._mode = 1
        elif 'toggle' == mode:
            self._mode = 2
        _LOGGER.debug("Mode: %s", mode)

    async def push_on(self):
        _LOGGER.debug("Attempting to push")
        x = await self.is_connected()
        if x == False:
            _LOGGER.debug("Lost connection...reconnecting")
            await self.connect(init=False)
        try:
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"000100000008020000000a0000000000decd")
            bar1 = list(hex1)
            hex2 = binascii.a2b_hex(id+"0fffffffffff000000000000000000000000")
            bar2 = list(hex2)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
            _LOGGER.debug("Pushed")
            self._is_on = True
        except Exception as e:
            _LOGGER.error("Failed to push: %s", e)
            self._is_on = False

    async def push_off(self):
        _LOGGER.debug("Attempting to push")
        x = await self.is_connected()
        if x == False:
            _LOGGER.debug("Lost connection...reconnecting")
            await self.connect(init=False)
        try:
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"000100000008020000000a0000000000decd")
            bar1 = list(hex1)
            hex2 = binascii.a2b_hex(id+"0fffffffffff000000000000000000000000")
            bar2 = list(hex2)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
            _LOGGER.debug("Pushed")
            self._is_on = False
        except Exception as e:
            _LOGGER.error("Failed to push: %s", e)
            self._is_on = True

    async def calibrate(self):
        _LOGGER.debug("Setting calibration")
        x = await self.is_connected()
        if x == False:
            _LOGGER.debug("Lost connection...reconnecting")
            await self._connect(init=False)
        try:
            id = self.__randomid(16) 
            hex1 = binascii.a2b_hex(id+"000100000008030001000a0000000000decd")
            bar1 = list(hex1)
            hex2 = binascii.a2b_hex(id+"0fff"+'{:02x}'.format(self._mode)+"000000"+"000000000000000000000000")
            bar2 = list(hex2)
            hex3 = binascii.a2b_hex(id+"000100000008040001000a0000000000decd")
            bar3 = list(hex3)
            hex4 = binascii.a2b_hex(id+"0fff"+'{:02x}'.format(self._depth)+"000000"+"000000000000000000000000")
            bar4 = list(hex4)
            hex5 = binascii.a2b_hex(id+"000100000008050001000a0000000000decd")
            bar5 = list(hex5)
            hex6 = binascii.a2b_hex(id+"0fff"+self._duration.to_bytes(4,"little").hex()+"000000000000000000000000")
            bar6 = list(hex6)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar3), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar4), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar5), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar6), response=True)
            _LOGGER.debug("Calibration set")
        except Exception as e:
            _LOGGER.error("Failed to calibrate: %s", e)

    def __randomstr(self, n):
       randstr = [random.choice(string.printable) for i in range(n)]
       return ''.join(randstr)

    def __randomid(self, bits):
       fmtstr = '{:'+'{:02d}'.format(int(bits/4))+'x}'
       return fmtstr.format(random.randrange(2**bits))
