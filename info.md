# WhatsApp Control Integration

Control your Home Assistant via WhatsApp messages!

## Features

- ✅ Control devices via text messages
- ✅ Voice message support (optional)
- ✅ No WhatsApp Business account needed
- ✅ Works with regular WhatsApp
- ✅ Pure Python - runs locally
- ✅ Send notifications to WhatsApp

## Setup

1. Install via HACS
2. Install system dependencies (see documentation)
3. Add to configuration.yaml:
```yaml
whatsapp_control:
  group_name: "homecontrol"
  openai_api_key: "sk-xxx"  # Optional
```

4. Restart Home Assistant
5. Scan QR code from logs
6. Create WhatsApp group named "homecontrol"
7. Start controlling your home!

## Usage

Send messages to your WhatsApp group:
- "Turn on living room light"
- "Set bedroom light to 50%"
- "What's the temperature?"
- "List devices"

## Documentation

Full documentation: [GitHub Repository](https://github.com/volski/whatsapp-control)