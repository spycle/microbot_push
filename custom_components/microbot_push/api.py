"""MicroBot Client."""
import logging
import asyncio
from typing import Optional
import async_timeout
import bleak
from bleak import BleakClient
from bleak import BleakScanner
from bleak import discover
from bleak import BleakError
from .const import DEFAULT_TIMEOUT
from time import sleep
import random, string
import configparser
from configparser import NoSectionError
import os
from os.path import expanduser
import binascii
from binascii import hexlify
#import threading

_LOGGER: logging.Logger = logging.getLogger(__package__)

SVC1831 = '00001831-0000-1000-8000-00805f9b34fb'
CHR2A89 = '00002a89-0000-1000-8000-00805f9b34fb'

class MicroBotApiClient:

    def __init__(
        self, bdaddr: str, config: str
    ) -> None:
        """MicroBot Client."""
        self._bdaddr = bdaddr
        self._client = BleakClient(self._bdaddr, timeout=None)
        self._default_timeout = DEFAULT_TIMEOUT
        self._retry = 10
        self._token = None
        self._config = expanduser(config)
        self.__loadToken()
        self._depth = 50
        self._duration = 0
        self._mode = 0
#        self._event = threading.Event()

    async def notification_handler(self, handle: int, data: bytes) -> None:
        _LOGGER.debug(f'Received response at {handle=}: {hexlify(data, ":")!r}')
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

        # Anything else is unexpected for now.
        else:
            _LOGGER.debug("Unexpected response")

    async def is_connected(self, timeout=None):
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

    async def _do_connect(self, timeout=10):
        await self._client.connect()
        _LOGGER.debug("Connected!")

    async def _do_disconnect(self):
        if self.is_connected():
            await self._client.disconnect()

    async def discover(self, timeout=60):
        devices = await discover()

    async def connect(self, init=False):
        """MicroBot is very sleepy. This helps keep it in context"""
        task_1 = asyncio.create_task(self.discover())    
        task_2 = asyncio.create_task(self._connect(init))  
        _LOGGER.debug("Scanning for 60s")
        scan = await task_1
        con = await task_2  

    async def _connect(self, init, timeout=10):
#        if self.is_connected():
#            return
        _LOGGER.debug("Finding device")
        retry = self._retry
        while True:
            try:
                self._device = await BleakScanner.find_device_by_address(self._bdaddr, timeout=10)
                if not self._device:
                    raise BleakError(f"A device with address {self._bdaddr} could not be found.")
                else:
                    _LOGGER.debug("Found device %s", self._bdaddr)
                    break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("error: %s", e) 
                    break  
                retry = retry - 1
                _LOGGER.debug("Retrying find device")
                sleep(1) 
        retry = self._retry
        while True:
            _LOGGER.debug("Connecting to %s", self._bdaddr)  
            try:
                await asyncio.wait_for(
                    self._do_connect(),
                    self._default_timeout if timeout is None else timeout)
                break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("Failed to connect: %s", e)
                    break
                retry = retry - 1
                _LOGGER.debug("Retrying connect")
                sleep(1)
        try:
            _LOGGER.debug("Attempting to pair") 
            await self._client.pair()
            _LOGGER.debug("Paired")
        except Exception as e:
            _LOGGER.error("Pair failed %s", e)
        await self.__setToken(init)              

    async def services(self, timeout=10):
        _LOGGER.debug("looking for services")
#        async with BleakClient(self._bdaddr) as client:
        for service in self._client.services:
            _LOGGER.debug(f"[Service] {service}")
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await self._client.read_gatt_char(char.uuid))
                        _LOGGER.debug(
                            f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
                        )
                    except Exception as e:
                        _LOGGER.error(
                            f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {e}"
                        )

            else:
                value = None
                _LOGGER.debug(
                    f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
                )

                for descriptor in char.descriptors:
                    try:
                        value = bytes(
                            await self._client.read_gatt_descriptor(descriptor.handle)
                        )
                        _LOGGER.debug(f"\t\t[Descriptor] {descriptor}) | Value: {value}")
                    except Exception as e:
                        _LOGGER.error(f"\t\t[Descriptor] {descriptor}) | Value: {e}")
            
    async def disconnect(self, timeout=None):
        _LOGGER.debug("Disconnecting from %s", self._bdaddr)
        try:
            await asyncio.wait_for(
                self._do_disconnect(),
                self._default_timeout if timeout is None else timeout)
        except Exception as e:
            _LOGGER.error("error: %s", e)

    async def async_get_data(self) -> dict:
        """Get data from the MicroBot."""
        _LOGGER.debug("Refresh")
        retry = self._retry
        while True:
            try:
                self._device = await BleakScanner.find_device_by_address(self._bdaddr, timeout=60)
                if not self._device:
                    raise BleakError(f"A device with address {self._bdaddr} could not be found.")
                else:
                    _LOGGER.debug("Found device %s", self._bdaddr)
                    break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("error: %s", e) 
                    break  
                retry = retry - 1
                _LOGGER.debug("Retrying find device")
                sleep(1) 

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
                    _LOGGER.error("failed to set token: %s", e)

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

    async def push(self):
        _LOGGER.debug("Attempting to push")
        retry = self._retry
        while True:
            try:
                id = self.__randomid(16)
                hex1 = binascii.a2b_hex(id+"000100000008020000000a0000000000decd")
                bar1 = list(hex1)
                hex2 = binascii.a2b_hex(id+"0fffffffffff000000000000000000000000")
                bar2 = list(hex2)
                await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
                await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
                _LOGGER.debug("Pushed")
                break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("failed to push: %s", e)
                    break
                retry = retry - 1
                _LOGGER.debug("Retrying push")
                sleep(1)

    async def calibrate(self):
        _LOGGER.debug("Setting calibration")
        retry = self._retry
        while True:
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
                break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("Failed to calibrate: %s", e)
                    break
                retry = retry - 1
                _LOGGER.debug("Retrying calibration")
                sleep(1)

    def __randomstr(self, n):
       randstr = [random.choice(string.printable) for i in range(n)]
       return ''.join(randstr)

    def __randomid(self, bits):
       fmtstr = '{:'+'{:02d}'.format(int(bits/4))+'x}'
       return fmtstr.format(random.randrange(2**bits))
