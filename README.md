# MicroBot Push
Home Assistant custom integration switch for controlling a MicroBot Push.

Makes use of the Linux utility from https://github.com/kahiroka/microbot

NB. This is very much a work in progress and isn't working 100% reliably.
I have no idea if this will work with newer devices sold by Keymitt

## Example configuration.yaml

```yaml
switch:
  - platform: microbot_push
    name: (optional)
    bdaddr: 'XX:XX:XX:XX:XX:XX' (Bluetooth address)
```

## Setup
You will need to know your device's bdaddr. This can be done using hcitool from a Linux device.

    $ sudo hcitool lescan | grep mibp
    XX:XX:XX:XX:XX:XX mibp
    
Alternatively the Keymitt app will display the bdaddr in the pairing discovery screen (displayed as 12 characters without the ':' )
    
Next you will need to generate a token from the device;

First reset the MicroBot Push. Turn it off then turn it on. When the LED starts blinking red, touch immediately the capacitive button on top and hold for about 5 seconds until the LED starts blinking red rapidly. Initialization. Wait until the LED blinks blue. Once the LED blinks blue, the reset is completed and your MicroBot Push is ready to be paired again.

Use the get_token service from the Developer Tools tab and input the bdaddr before pressing Call Service. The MicroBot will start cycling through various colours waiting for the button to be pressed. (when pairing with the app the colours were significant in that you had to press when the colour on the device matched the app. I've no idea if this is relevant but for me this was always purple) 

The token is stored in path-to-config-directory/microbot-xxxxxxxxxxxx.conf.

## Services

Set the depth, duration, and mode (normal|invert|toggle).
The Push will retain the settings so only needs running once.

NB. when running this service the MicroBot will push to the given depth to aid in calibration, but not necessarily for the selected duration. The setting is however stored. 

```yaml
service: microbot_push.set_params
data:
  bdaddr: 'XX:XX:XX:XX:XX:XX'
  depth: 100
  duration: 10
  mode: 'normal'
```
  
Get a token from the Push

```yaml
service: microbot_push.get_token
data:
  bdaddr: 'XX:XX:XX:XX:XX:XX'
```

A reconnect is required for each push command. This can result in a long delay of up to 30 seconds in response time. If this is an issue then try the server mode which attempts to maintain connection. Turn on by using the start_server service in Developer Tools.
The socket file will be stored in path-to-config-directory/microbot-xxxxxxxxxxxx

```yaml
- alias: Start Microbot Server
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: microbot_push.start_server
      data:
        bdaddr: 'XX:XX:XX:XX:XX:XX'
```

