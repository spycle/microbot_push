# MicroBot Push
Home Assistant custom switch integration for controlling a Naran/Keymitt MicroBot Push.

Uses a fork of the Linux utility from https://github.com/kahiroka/microbot

## Setup
You will need to know your device's bdaddr/mac to configure. There are utilities available for this purpose or alternatively pair with the Keymitt app which will display the address in the pairing discovery screen displayed as 12 characters without the ':' (Do not complete the pairing process).
    
Before installation, reset the MicroBot Push by turning it off and on and waiting for the LED to blink red. Immediately press and hold the button on the push for about 5 seconds until the LED starts blinking red rapidly and let go. The LED should now be blinking blue indicating pairing mode.

Installation is via HACS and then the Home Assistant Integration page. The bdaddr/mac needs to be formatted XX:XX:XX:XX:XX:XX

Before use a one-time token needs to be generated to complete the pairing process (this will eventuallly be part of the Config Flow). Use the generate_token service from the Developer Tools tab. Press the button on the Push to wake it up (it's very sleepy) and wait for it to connect. The Push will eventually start cycling through 2 to 3 colours waiting for the button to be pressed. (when pairing with the app the colours were significant in that you had to press when the colour on the device matched the app. I've no idea if this is relevant but for me this was always purple) 

The token is stored as path-to-config-directory/.storage/microbot-xxxxxxxxxxxx.conf.

Note: The Push is a very sleepy device so it can take up to a minute to respond. I might be able to improve this with some regular polling

## Services

Not implemented yet. It might be possible to use the Keymitt app to calibrate but settings may be lost on reset?
~~Calibration - set the depth, duration, and switch mode (normal|invert|toggle).~~
~~The Push will retain the settings so only needs running once.~~

~~NB. when running this service the MicroBot will push to the given depth to aid in calibration, but not necessarily for the selected duration. The setting is however stored.~~

```yaml
service: microbot_push.calibrate
data:
  depth: 100
  duration: 10
  mode: 'normal'
```
  
Get a token from the Push

```yaml
service: microbot_push.generate_token

```
