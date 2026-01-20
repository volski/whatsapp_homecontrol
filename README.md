# WhatsApp Control for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/volski/whatsapp-control.svg)](https://github.com/volski/whatsapp-control/releases)
[![License](https://img.shields.io/github/license/volski/whatsapp-control.svg)](LICENSE)

Control your Home Assistant through WhatsApp messages - no Business account needed!

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
4. Add: `https://github.com/volski/whatsapp-control`
5. Category: Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/whatsapp_control` to your `config/custom_components/` directory
2. Install system dependencies (see below)
3. Restart Home Assistant

## System Dependencies

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
whatsapp_control:
  group_name: "homecontrol"  # Your WhatsApp group name
  openai_api_key: !secret openai_key  # Optional: for voice transcription
```

## Setup Steps

1. Install the integration (via HACS or manually)
2. Install system dependencies (Chromium)
3. Add configuration to `configuration.yaml`
4. Restart Home Assistant
5. Check logs for QR code location
6. Scan QR code with WhatsApp (Menu → Linked Devices)
7. Create WhatsApp group named "homecontrol"
8. Start sending commands!

## Usage Examples

### Text Commands

Send to your WhatsApp group: