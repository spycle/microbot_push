from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import EVENT_HOMEASSISTANT_START
import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
import configparser
from configparser import NoSectionError
import re

from . import microbot
from .microbot import MicroBotPush

DOMAIN = "microbot_push"
_LOGGER = logging.getLogger(__name__)

CONF_BDADDR = "bdaddr"
DEFAULT_NAME = "MicroBotPush"

def setup(hass, config):

    conf_dir = hass.config.path()
    conf = conf_dir+'/microbot.conf'

    def stop_server(call):

        cp = configparser.ConfigParser()
        cp.read(conf)
        if not cp.has_section('tokens'):
            _LOGGER.warning('cannot start server as no token')
            return
        else:
            raw = cp.options('tokens')
            string = raw[0]
            string = string.upper()
            bdaddr = ':'.join([string[i : i + 2] for i in range(0, len(string), 2)])

        socket_path = conf_dir+"/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())
        
        mbps = MicroBotPush(bdaddr, conf, 'newproto', 'client', socket_path, 50, 0, 'normal')
        mbps.disconnect()
    
    def start_server(call):

        cp = configparser.ConfigParser()
        cp.read(conf)
        if not cp.has_section('tokens'):
            _LOGGER.warning('cannot start server as no token')
            return
        else:
            raw = cp.options('tokens')
            string = raw[0]
            string = string.upper()
            bdaddr = ':'.join([string[i : i + 2] for i in range(0, len(string), 2)])

        socket_path = conf_dir+"/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())
        
        mbps = MicroBotPush(bdaddr, conf, 'newproto', 'server', socket_path, 50, 0, 'normal')
        mbps.connect()
        mbps.disconnect()
        mbps.runServer()
        return

    def request_token(call):

        data = call.data.copy()
        
        ble = data["bdaddr"]
        
        mbpt = MicroBotPush(ble, conf, 'newproto', 'is_server', 'socket_path', 50, 0, 'normal')
        _LOGGER.info('update token')
        mbpt.connect(init=True)
        mbpt.getToken()
        mbpt.disconnect()
        return

        _LOGGER.info('called', data["bdaddr"])

    hass.services.register(DOMAIN, 'get_token', request_token)
    hass.services.register(DOMAIN, 'start_server', start_server)
    hass.services.register(DOMAIN, 'stop_server', stop_server)
#    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_server)
 
    return True
