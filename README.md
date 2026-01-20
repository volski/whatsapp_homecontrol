# WhatsApp Control for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/volski/whatsapp_homecontrol.svg)](https://github.com/volski/whatsapp_homecontrol/releases)
[![License](https://img.shields.io/github/license/volski/whatsapp_homecontrol.svg)](LICENSE)

Control your Home Assistant through WhatsApp messages - no Business account needed!

## ⚠️ Important Notice

**This integration provides the framework for WhatsApp control but requires you to choose and configure a WhatsApp backend.** The original `webwhatsapi` library is incompatible with Python 3.13+ and has been removed.

**Choose one of these backends:**
1. **CallMeBot API** (Recommended - Free, no installation)
2. **Twilio WhatsApp API** (Paid service, very reliable)
3. **Custom Webhook** (Advanced users)

See [WhatsApp Backend Setup](#whatsapp-backend-setup) below for details.

## Features

- 🎤 **Text & Voice Commands** - Control via text or voice messages
- 🏠 **Full Device Control** - Lights, switches, climate, and more
- 🔔 **Notifications** - Send alerts to WhatsApp from automations
- 🔒 **Local & Secure** - Runs entirely on your Home Assistant
- 💰 **Free** - No API costs (optional: OpenAI for voice)
- 📱 **Regular WhatsApp** - Use your personal account

## Quick Start

### Prerequisites

- Home Assistant 2023.1.0 or newer
- Chromium/Chrome browser
- WhatsApp account

### Installation via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in top right → "Custom repositories"
4. Add: `https://github.com/volski/whatsapp_homecontrol`
5. Category: Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/whatsapp_homecontrol` to your `config/custom_components/` directory
2. Install system dependencies (see below)
3. Restart Home Assistant

## WhatsApp Backend Setup

Since `webwhatsapi` is incompatible with Python 3.13+, choose one of these alternatives:

### Option 1: Local WhatsApp Web Bridge (Recommended - No URL Exposure)

**Pros:** Fully local, no external services, two-way messaging, no URL exposure  
**Cons:** Requires Node.js, slightly more complex setup

Run a local bridge service that connects WhatsApp Web to Home Assistant via MQTT or REST API.

**Using whatsapp-web.js with MQTT:**

1. Install Node.js on your Home Assistant server or a local machine
2. Create a bridge service:

```bash
# Install dependencies
npm install whatsapp-web.js qrcode-terminal mqtt

# Create bridge.js
cat > bridge.js << 'EOF'
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const mqtt = require('mqtt');

const mqttClient = mqtt.connect('mqtt://localhost:1883');
const waClient = new Client({
    authStrategy: new LocalAuth()
});

waClient.on('qr', (qr) => {
    qrcode.generate(qr, {small: true});
});

waClient.on('ready', () => {
    console.log('WhatsApp client ready!');
});

// Forward WhatsApp messages to MQTT
waClient.on('message', async (msg) => {
    const chat = await msg.getChat();
    if (chat.name === 'homecontrol') {  // Your group name
        mqttClient.publish('whatsapp/message', JSON.stringify({
            from: msg.author || msg.from,
            body: msg.body,
            timestamp: msg.timestamp
        }));
    }
});

// Listen for commands from Home Assistant via MQTT
mqttClient.on('message', async (topic, message) => {
    if (topic === 'whatsapp/send') {
        const data = JSON.parse(message.toString());
        const chats = await waClient.getChats();
        const chat = chats.find(c => c.name === 'homecontrol');
        if (chat) {
            await chat.sendMessage(data.message);
        }
    }
});

mqttClient.subscribe('whatsapp/send');
waClient.initialize();
EOF

# Run the bridge
node bridge.js
```

3. Configure Home Assistant MQTT:
```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "WhatsApp Message"
      state_topic: "whatsapp/message"
      value_template: "{{ value_json.body }}"

# Send messages via MQTT
automation:
  - alias: "Send WhatsApp Notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: mqtt.publish
        data:
          topic: "whatsapp/send"
          payload: '{"message": "Front door opened!"}'
```

**Benefits:**
- ✅ No external URL exposure
- ✅ Fully local communication
- ✅ Two-way messaging
- ✅ No third-party services

### Option 2: Docker WhatsApp Bridge (Easiest Local Solution)

Use a pre-built Docker container that bridges WhatsApp to Home Assistant:

```bash
docker run -d \
  --name whatsapp-bridge \
  --network host \
  -v ./whatsapp-data:/app/data \
  -e MQTT_HOST=localhost \
  -e MQTT_PORT=1883 \
  -e GROUP_NAME=homecontrol \
  your-whatsapp-bridge-image
```

### Option 3: CallMeBot API (Simple but External)

**Pros:** Free, no installation, simple setup  
**Cons:** Send-only, uses external service, phone number exposed to CallMeBot

⚠️ **Note:** This option sends data to an external service.

1. Register at https://www.callmebot.com/blog/free-api-whatsapp-messages/
2. Add to `configuration.yaml`:
```yaml
rest_command:
  whatsapp_send:
    url: "https://api.callmebot.com/whatsapp.php?phone={{ phone }}&text={{ message }}&apikey={{ apikey }}"
    method: GET
```

### Option 4: Twilio WhatsApp API

**Pros:** Very reliable, two-way messaging, official API  
**Cons:** Paid service, requires external webhook (can use Nabu Casa for secure tunnel)

1. Sign up at https://www.twilio.com/whatsapp
2. Use Nabu Casa Cloud for secure webhook (no port forwarding needed)
3. Configure Twilio webhook to your Nabu Casa URL

## System Dependencies

**Note:** Selenium/Chromium dependencies are only needed if you implement a custom WhatsApp Web solution.

### Home Assistant OS/Supervised
```bash
docker exec homeassistant bash -c "
  apt-get update && 
  apt-get install -y chromium chromium-driver
"
```

### Home Assistant Container
```bash
docker exec -it homeassistant bash
apt-get update
apt-get install -y chromium chromium-driver
```

### Home Assistant Core
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver
```

## Configuration

Add to your `configuration.yaml`:
```yaml
whatsapp_homecontrol:
  group_name: "homecontrol"  # Your WhatsApp group name
  openai_api_key: !secret openai_key  # Optional: for voice transcription
```

## Setup Steps

1. **Choose your WhatsApp backend** (see [WhatsApp Backend Setup](#whatsapp-backend-setup))
2. Install the integration (via HACS or manually)
3. Configure your chosen backend (CallMeBot, Twilio, etc.)
4. Add configuration to `configuration.yaml`
5. Restart Home Assistant
6. Test sending messages through your backend
7. Configure automations to respond to WhatsApp messages

**For CallMeBot (simplest):**
- No additional setup needed beyond API key registration
- Use `rest_command` service to send messages
- Receiving messages requires webhook setup (optional)

## Usage Examples

### Text Commands

Send to your WhatsApp group: