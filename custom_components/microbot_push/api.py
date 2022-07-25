"""MicroBot Client."""
import logging
import asyncio
from typing import Optional
import aiohttp
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
import threading

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
#        self._event = threading.Event()

    async def notification_handler(self, handle: int, data: bytes) -> None:
        _LOGGER.info(f'Received response at {handle=}: {hexlify(data, ":")!r}')
#            _LOGGER.info("Raw data: %s", data)
#            lst = list(data)
#            _LOGGER.info("List: %s", lst)
        tmp = binascii.b2a_hex(data)[4:4+36]
#            _LOGGER.info("b2a data: %s", tmp)
        if b'0f0101' == tmp[:6] or b'0f0102' == tmp[:6]:
            bdaddr = tmp[6:6+12]
            bdaddr_rcvd = bdaddr.decode()
            _LOGGER.info("ack with bdaddr: %s", bdaddr_rcvd)
#            await self._client.stop_notify(CHR2A89)
            await self.getToken()
        elif b'1fff' == tmp[0:4] and b'0000000000000000000000' != tmp[6:6+22] and b'00000000' == tmp[28:36]:
            token = tmp[4:4+32]
#            _LOGGER.info("Token raw: %s", token)
            self._token = token.decode()
            _LOGGER.info("ack with token %s", self._token)
            await self._client.stop_notify(CHR2A89)
            self.__storeToken()

        # Anything else is unexpected.
        else:
            _LOGGER.info("Unexpected response")

        # Notify the writer
#        self._event.set()

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
        _LOGGER.info("Connected!")

    async def _do_disconnect(self):
        if self.is_connected():
            await self._client.disconnect()

    async def discover(self, timeout=60):
        devices = await discover()

    async def connect(self, init=False):
        """MicroBot is very sleepy. This helps keep it in context"""
        task_1 = asyncio.create_task(self.discover())    
        task_2 = asyncio.create_task(self._connect(init))  
        _LOGGER.info("Scanning for 60s")
        scan = await task_1
        con = await task_2  

    async def _connect(self, init, timeout=10):
#        if self.is_connected():
#            return
        _LOGGER.info("Finding device")
        retry = self._retry
        while True:
            try:
                self._device = await BleakScanner.find_device_by_address(self._bdaddr, timeout=10)
                if not self._device:
                    raise BleakError(f"A device with address {self._bdaddr} could not be found.")
                else:
                    _LOGGER.info("Found device %s", self._bdaddr)
                    break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("error: %s", e) 
                    break  
                retry = retry - 1
                _LOGGER.info("Retrying find device")
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
                _LOGGER.info("Retrying connect")
                sleep(1)
        try:
            _LOGGER.info("Attempting to pair") 
#            await self._client.unpair()
            await self._client.pair()
            _LOGGER.info("Paired")
        except Exception as e:
            _LOGGER.error("Pair failed %s", e)
        await self.__setToken(init)              

    async def services(self, timeout=10):
        _LOGGER.info("looking for services")
#        async with BleakClient(self._bdaddr) as client:
        for service in self._client.services:
            _LOGGER.info(f"[Service] {service}")
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await self._client.read_gatt_char(char.uuid))
                        _LOGGER.info(
                            f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
                        )
                    except Exception as e:
                        _LOGGER.error(
                            f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {e}"
                        )

            else:
                value = None
                _LOGGER.info(
                    f"\t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
                )

                for descriptor in char.descriptors:
                    try:
                        value = bytes(
                            await self._client.read_gatt_descriptor(descriptor.handle)
                        )
                        _LOGGER.info(f"\t\t[Descriptor] {descriptor}) | Value: {value}")
                    except Exception as e:
                        _LOGGER.error(f"\t\t[Descriptor] {descriptor}) | Value: {e}")
            
    async def disconnect(self, timeout=None):
        _LOGGER.debug("Disconnecting from %s", self._bdaddr)
#        try:
#            _LOGGER.info("attempting to unpair")  
#            await self._client.unpair()
#        except Exception as e:
#            _LOGGER.error("Unpair failed %s", e)
#        await self._client.stop_notify(CHR2A89)
        try:
#            await self._client.unpair()
            await asyncio.wait_for(
                self._do_disconnect(),
                self._default_timeout if timeout is None else timeout)
        except Exception as e:
            _LOGGER.error("error: %s", e)

    async def async_get_data(self) -> dict:
        """Get data from the MicroBot."""
        _LOGGER.info("Refresh")
        retry = self._retry
        while True:
            try:
                self._device = await BleakScanner.find_device_by_address(self._bdaddr, timeout=60)
                if not self._device:
                    raise BleakError(f"A device with address {self._bdaddr} could not be found.")
                else:
                    _LOGGER.info("Found device %s", self._bdaddr)
                    break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("error: %s", e) 
                    break  
                retry = retry - 1
                _LOGGER.info("Retrying find device")
                sleep(1) 

    async def async_set_title(self, value: str) -> None:
        """Get data from the MicroBot."""
        url = "https://jsonplaceholder.typicode.com/posts/1"
        await self.api_wrapper("patch", url, data={"title": value}, headers=HEADERS)

    def __loadToken(self):
        _LOGGER.info("Looking for token")
        config = configparser.ConfigParser()
        config.read(self._config)
        bdaddr = self._bdaddr.lower().replace(':', '')
        if config.has_option('tokens', bdaddr):
            self._token = config.get('tokens', bdaddr)
            _LOGGER.info("Token: %s", self._token)

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
        _LOGGER.info("Token saved to file")

    def hasToken(self):
        if self._token == None:
            _LOGGER.info("no token")
            return False
        else:
            _LOGGER.info("Has token")
            return True

    async def __initToken(self):
        _LOGGER.info("Generating token")
        try:
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"00010040e20100fa01000700000000000000")
            bar1 = list(hex1)
#            _LOGGER.info(bar1)
            hex2 = binascii.a2b_hex(id+"0fffffffffffffffffffffffffff"+self.__randomid(32))
            bar2 = list(hex2)
            _LOGGER.info("Waiting for bdaddr notification")
            await self._client.start_notify(CHR2A89, self.notification_handler)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
#                s = self.p.getServiceByUUID(MicroBotPush.UUID.SVC1831)
#                c = s.getCharacteristics(MicroBotPush.UUID.CHR2A89)[0]
#                self.p.writeCharacteristic(c.getHandle()+1, b'\x01\x00', True)
#                c.write(binascii.a2b_hex(id+"00010040e20100fa01000700000000000000"), True)
#                c.write(binascii.a2b_hex(id+"0fffffffffffffffffffffffffff"+self.__randomid(32)), True)
        except Exception as e:
            _LOGGER.error("failed to init token: %s", e)

    async def __setToken(self, init):
        if init:
            _LOGGER.info("init set to True")
            await self.__initToken()
        else:
            if self.hasToken():
                _LOGGER.info("Setting token")
                try:
#                        s = self.p.getServiceByUUID(MicroBotPush.UUID.SVC1831)
#                        c = s.getCharacteristics(MicroBotPush.UUID.CHR2A89)[0]
#                        self.p.writeCharacteristic(c.getHandle()+1, b'\x01\x00', True)
#                        s = self.p.getServiceByUUID(MicroBotPush.UUID.SVC1831)
#                        c = s.getCharacteristics(MicroBotPush.UUID.CHR2A89)[0]
                    id = self.__randomid(16)
#                        c.write(binascii.a2b_hex(id+"00010000000000fa0000070000000000decd"), True)
#                        c.write(binascii.a2b_hex(id+"0fff"+self.token), True)
#                await self._client.write_gatt_char(24, bytearray([0x01, 0x00]), response=True)
#                    _LOGGER.info("Waiting for bdaddr notification")
#                    await self._client.start_notify(CHR2A89, self.notification_handler)
                    hex1 = binascii.a2b_hex(id+"00010000000000fa0000070000000000decd")
                    bar1 = list(hex1)
#                    _LOGGER.info(bar1)
                    hex2 = binascii.a2b_hex(id+"0fff"+self._token)
                    bar2 = list(hex2)
#                    _LOGGER.info(bar2)
                    await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
                    await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
                    _LOGGER.info("Token set")
#                    await self._client.stop_notify(CHR2A89)
                except Exception as e:
                    _LOGGER.error("failed to set token: %s", e)
                await self.push()
                await self.disconnect()

    async def getToken(self):
#        self._event.clear()
        _LOGGER.info("Getting token")
        try:
#            if self.newproto:
#                s = self.p.getServiceByUUID(MicroBotPush.UUID.SVC1831)
#                c = s.getCharacteristics(MicroBotPush.UUID.CHR2A89)[0]
#                self.p.writeCharacteristic(c.getHandle()+1, b'\x01\x00', True)
            id = self.__randomid(16)
            hex1 = binascii.a2b_hex(id+"00010040e20101fa01000000000000000000")
            bar1 = list(hex1)
            _LOGGER.info(bar1)
            hex2 = binascii.a2b_hex(id+"0fffffffffffffffffff0000000000000000")
            bar2 = list(hex2)
#            _LOGGER.info("Waiting for token notification")
#            await self._client.start_notify(CHR2A89, self.notification_handler)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
#                c.write(binascii.a2b_hex(id+"00010040e20101fa01000000000000000000"), True)
            await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
#                c.write(binascii.a2b_hex(id+"0fffffffffffffffffff0000000000000000"), True)
            _LOGGER.warning('touch the button to get a token')
#            await self._client.write_gatt_descriptor(24, bytearray([0x01, 0x00]))
#        except Exception as e:
 #           _LOGGER.error("failed to request token %s", e)
#        try:
#            async with BleakClient(self._bdaddr, timeout=10) as self._device:
#            _LOGGER.info("Waiting for notification")
#            self._event.wait(timeout=20)
#            await self._client.start_notify(CHR2A89, self.notification_handler)
#            await self.services
#            await self._client.stop_notify(CHR2A89)
        except Exception as e:
            _LOGGER.error("failed to request token: %s", e)

    async def push(self):
        _LOGGER.info("Attempting to push")
        retry = self._retry
        while True:
            try:
                id = self.__randomid(16)
#                    c.write(binascii.a2b_hex(id+"000100000008020000000a0000000000decd"), True)
#                    c.write(binascii.a2b_hex(id+"0fffffffffff000000000000000000000000"), True)
                hex1 = binascii.a2b_hex(id+"000100000008020000000a0000000000decd")
                bar1 = list(hex1)
                hex2 = binascii.a2b_hex(id+"0fffffffffff000000000000000000000000")
                bar2 = list(hex2)
                await self._client.write_gatt_char(CHR2A89, bytearray(bar1), response=True)
                await self._client.write_gatt_char(CHR2A89, bytearray(bar2), response=True)
                _LOGGER.info("Pushed")
                break
            except Exception as e:
                if retry == 0:
                    _LOGGER.error("failed to push: %s", e)
                    break
                retry = retry - 1
                _LOGGER.info("Retrying push")
                sleep(1)

    def __randomstr(self, n):
       randstr = [random.choice(string.printable) for i in range(n)]
       return ''.join(randstr)

    def __randomid(self, bits):
       fmtstr = '{:'+'{:02d}'.format(int(bits/4))+'x}'
       return fmtstr.format(random.randrange(2**bits))

