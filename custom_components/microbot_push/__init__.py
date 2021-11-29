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
    
    def set_params(call):

        cp = configparser.ConfigParser()
        cp.read(conf)
        if not cp.has_section('tokens'):
            _LOGGER.warning('no token found')
            return
        else:
            raw = cp.options('tokens')
            string = raw[0]
            string = string.upper()
            bdaddr = ':'.join([string[i : i + 2] for i in range(0, len(string), 2)])

        socket_path = conf_dir+"/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())

        data = call.data.copy()
        
        depth = data["depth"]
        duration = data["duration"]
        mode = data["mode"]
        
        mbpp = MicroBotPush(bdaddr, conf, socket_path, newproto=True, is_server=False)
        mbpp.connect()
        mbpp.setDepth(depth)
        mbpp.setDuration(duration)
        mbpp.setMode(mode)
        mbpp.setParams()
        mbpp.disconnect()
        return

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
        
        mbps = MicroBotPush(bdaddr, conf, socket_path, newproto=True, is_server=True)
        mbps.connect()
        mbps.disconnect()
        mbps.runServer()
        return

    def request_token(call):

        data = call.data.copy()
        
        ble = data["bdaddr"]
        
        mbpt = MicroBotPush(ble, conf, 'socket_path', newproto=True, is_server=False)
        _LOGGER.info('update token')
        mbpt.connect(init=True)
        mbpt.getToken()
        mbpt.disconnect()
        return

        _LOGGER.info('called', data["bdaddr"])

    hass.services.register(DOMAIN, 'get_token', request_token)
    hass.services.register(DOMAIN, 'start_server', start_server)
    hass.services.register(DOMAIN, 'set_params', set_params)
#    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_server)
 
    return True
