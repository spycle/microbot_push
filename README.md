# MicroBot Push
The MicroBot Push integration allows you to control the [MicroBot Push](https://www.keymitt.com/products/microbot-push).

## Prerequisites

In order to use this integration, it is required to have working Bluetooth set up on the device running Home Assistant. A [MicroBot Hub](https://www.keymitt.com/products/microbot-hub) is not required for this integration.

If you have multiple devices of the same type, you need to get the BTLE MAC address of your device to tell your devices apart. You can find the address for your device using the following steps:

1. Open the Keymitt app.
2. Add New Devices -> Push -> OK.
3. In the Scanning screen the BTLE MAC will be shown as a string of 12 characters.
4. Write down the BTLE MAC address of your device.

Please note, device names configured in the MicroBot app are not transferred into Home Assistant.
    
Before installation the MicroBot Push will need to be in pairing mode. To reset; turn it off and on, wait for the LED to blink red, immediately press and hold the button for about 5 seconds until the LED starts blinking red rapidly, and let go. The LED should now be blinking blue indicating pairing mode.

## Installation

Installation is via HACS and then the Home Assistant Integration page. Devices will be automatically discovered.

## MicroBot Options

- `Retry count`: How many times to retry sending commands to your MicroBot device.
Note: In extreme cases, the MicroBot Push may take up to a minute to respond (depending on environment and how long the device has been asleep). Setting this too low may lead to connection errors. Setting a high value ensures that commands are received.

## Services

Calibration - set the depth, duration, and switch mode (normal|invert|toggle).
The Push will retain the settings locally so only needs running once.

Note: When running this service the MicroBot will push to the given depth to aid in calibration, but not necessarily for the selected duration. The setting is however stored locally on the device.

```yaml
service: microbot_push.calibrate
data:
  depth: 100
  duration: 10
  mode: 'normal'
```
  
Pair/Repair (Generate a token).
Required if the MicroBot has been reset.

```yaml
service: microbot_push.generate_token

```

### Error codes and troubleshooting

The MicroBot integration will automatically discover devices once the [Bluetooth](/integrations/bluetooth) integration is enabled and functional.

"No unconfigured devices found":
  Make sure the Push is powered on and in range. It may be beneficial to wake the device before pairing.

## Credits

https://github.com/kahiroka/microbot - the commands required to control the MicroBot

https://github.com/custom-components/integration_blueprint - the blueprint

https://github.com/home-assistant/core/tree/dev/homeassistant/components/switchbot - inspiration, and in some cases more than inspiration

