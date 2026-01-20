# WhatsApp Control Integration

Control your Home Assistant via WhatsApp messages - **no URL exposure required!**

## Features

- ✅ Control devices via text messages
- ✅ **Fully local** - no external services needed
- ✅ **No URL exposure** - uses MQTT bridge
- ✅ Two-way messaging
- ✅ No WhatsApp Business account needed
- ✅ Works with regular WhatsApp
- ✅ Send notifications to WhatsApp

## Quick Setup (Local Bridge)

1. Install via HACS
2. Install the WhatsApp bridge (choose one):
   - **Docker** (easiest): `docker-compose up -d`
   - **Node.js**: `npm install && npm start`
3. Scan QR code when prompted
4. Create WhatsApp group named "homecontrol"
5. Configure MQTT in Home Assistant:

```yaml
mqtt:
  sensor:
    - name: "WhatsApp Message"
      state_topic: "whatsapp/message/in"
      value_template: "{{ value_json.body }}"
```

6. Send messages via MQTT:
```yaml
automation:
  - alias: "WhatsApp Notification"
    action:
      - service: mqtt.publish
        data:
          topic: "whatsapp/message/out"
          payload: '{"message": "Hello from Home Assistant!"}'
```

## Usage

Send messages to your WhatsApp group:
- "Turn on living room light"
- "Set bedroom light to 50%"
- "What's the temperature?"
- "List devices"

## Documentation

Full documentation: [GitHub Repository](https://github.com/volski/whatsapp_homecontrol)