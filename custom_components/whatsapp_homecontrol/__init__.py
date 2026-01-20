"""
WhatsApp Web Integration for Home Assistant - Pure Python
Single component that does everything!

File: custom_components/whatsapp_control/__init__.py
"""

import asyncio
import logging
import os
import tempfile
from datetime import timedelta
from typing import Optional
import base64

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

# Import whatsapp-web.py library
try:
    from whatsapp import WhatsApp
except ImportError:
    WhatsApp = None

_LOGGER = logging.getLogger(__name__)

DOMAIN = "whatsapp_control"
CONF_GROUP_NAME = "group_name"
CONF_PHONE = "phone"
CONF_OPENAI_KEY = "openai_api_key"

DEFAULT_GROUP_NAME = "homecontrol"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_GROUP_NAME, default=DEFAULT_GROUP_NAME): cv.string,
                vol.Optional(CONF_PHONE): cv.string,
                vol.Optional(CONF_OPENAI_KEY): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the WhatsApp Control component."""

    if WhatsApp is None:
        _LOGGER.error(
            "whatsapp-web.py library not found. "
            "Install with: pip install whatsapp-web.py"
        )
        return False

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    group_name = conf[CONF_GROUP_NAME]
    phone = conf.get(CONF_PHONE)
    openai_key = conf.get(CONF_OPENAI_KEY)

    handler = WhatsAppHandler(hass, group_name, phone, openai_key)
    hass.data[DOMAIN] = handler

    # Initialize WhatsApp connection
    await handler.async_setup()

    # Register services
    async def handle_send_message(call: ServiceCall):
        """Handle send message service."""
        message = call.data.get("message")
        await handler.send_message(message)

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)

    _LOGGER.info("WhatsApp Control initialized successfully")
    return True


class WhatsAppHandler:
    """Handle WhatsApp messages and Home Assistant commands."""

    def __init__(self, hass: HomeAssistant, group_name: str, phone: str = None, openai_key: str = None):
        self.hass = hass
        self.group_name = group_name
        self.phone = phone
        self.openai_key = openai_key
        self.wa_client = None
        self.group_id = None
        self.session_path = os.path.join(hass.config.path(), "whatsapp_session")

    async def async_setup(self):
        """Set up WhatsApp connection."""
        try:
            # Create session directory
            os.makedirs(self.session_path, exist_ok=True)

            # Initialize WhatsApp client in executor
            await self.hass.async_add_executor_job(self._setup_whatsapp)

            _LOGGER.info("WhatsApp client initialized successfully")
        except Exception as e:
            _LOGGER.error(f"Failed to initialize WhatsApp: {e}")
            raise

    def _setup_whatsapp(self):
        """Setup WhatsApp client (blocking)."""
        from whatsapp import WhatsApp

        # Initialize client
        self.wa_client = WhatsApp(
            session=self.session_path,
            phone=self.phone
        )

        # Set up QR code callback
        def on_qr(qr_code):
            _LOGGER.info("Scan QR code to authenticate WhatsApp:")
            _LOGGER.info(f"QR Code: {qr_code}")
            # You can also save QR as image for easier scanning
            self._save_qr_code(qr_code)

        # Set up message callback
        def on_message(message):
            self.hass.add_job(self._handle_message_sync(message))

        self.wa_client.on_qr = on_qr
        self.wa_client.on_message = on_message

        # Start client
        self.wa_client.start()

        # Find group
        self._find_group()

    def _save_qr_code(self, qr_data):
        """Save QR code as image."""
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(qr_data)
            qr.make()

            qr_path = os.path.join(self.hass.config.path(), "www", "whatsapp_qr.png")
            img = qr.make_image()
            img.save(qr_path)

            _LOGGER.info(f"QR Code saved to: {qr_path}")
            _LOGGER.info("Access it at: http://homeassistant.local:8123/local/whatsapp_qr.png")
        except Exception as e:
            _LOGGER.error(f"Could not save QR code: {e}")

    def _find_group(self):
        """Find the control group."""
        try:
            chats = self.wa_client.get_chats()
            for chat in chats:
                if chat.is_group and chat.name.lower() == self.group_name.lower():
                    self.group_id = chat.id
                    _LOGGER.info(f"Found group: {chat.name}")
                    # Send ready message
                    self.wa_client.send_message(
                        self.group_id,
                        "🤖 Home Control Bot is online and ready!"
                    )
                    return

            _LOGGER.warning(f"Group '{self.group_name}' not found")
        except Exception as e:
            _LOGGER.error(f"Error finding group: {e}")

    async def _handle_message_sync(self, message):
        """Handle incoming message (sync to async bridge)."""
        await self.handle_message(message)

    async def handle_message(self, message):
        """Process incoming WhatsApp message."""
        try:
            # Only process messages from our control group
            if not message.chat.is_group:
                return

            if message.chat.name.lower() != self.group_name.lower():
                return

            _LOGGER.info(f"Message from {message.sender.name}: {message.text or '[MEDIA]'}")

            # Handle text messages
            if message.text:
                response = await self.process_command(message.text)
                await self.send_message(response)

            # Handle voice messages
            elif message.is_voice:
                await self.handle_voice_message(message)

        except Exception as e:
            _LOGGER.error(f"Error handling message: {e}")
            await self.send_message(f"❌ Error: {str(e)}")

    async def handle_voice_message(self, message):
        """Handle voice message."""
        try:
            await self.send_message("🎤 Processing voice message...")

            # Download voice message
            media_data = await self.hass.async_add_executor_job(
                message.download_media
            )

            if not media_data:
                await self.send_message("❌ Could not download voice message")
                return

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
                f.write(media_data)
                temp_path = f.name

            # Transcribe
            transcription = await self.transcribe_audio(temp_path)

            # Clean up
            os.unlink(temp_path)

            if transcription:
                await self.send_message(f"🎤 Heard: {transcription}")
                response = await self.process_command(transcription)
                await self.send_message(response)
            else:
                await self.send_message("❌ Could not transcribe voice message")

        except Exception as e:
            _LOGGER.error(f"Error handling voice: {e}")
            await self.send_message(f"❌ Voice error: {str(e)}")

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper."""
        if not self.openai_key:
            _LOGGER.warning("OpenAI API key not configured for voice transcription")
            return None

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()

                form = aiohttp.FormData()
                form.add_field('file', audio_data, filename='audio.ogg')
                form.add_field('model', 'whisper-1')
                form.add_field('language', 'en')

                headers = {
                    'Authorization': f'Bearer {self.openai_key}'
                }

                async with session.post(
                    'https://api.openai.com/v1/audio/transcriptions',
                    data=form,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('text')
                    else:
                        _LOGGER.error(f"Transcription failed: {response.status}")
                        return None

        except Exception as e:
            _LOGGER.error(f"Transcription error: {e}")
            return None

    async def process_command(self, command_text: str) -> str:
        """Parse and execute Home Assistant command."""
        cmd = command_text.lower().strip()

        try:
            # Turn on
            if "turn on" in cmd or "switch on" in cmd:
                entity = self.extract_entity(cmd, ["turn on", "switch on"])
                return await self.turn_on(entity)

            # Turn off
            elif "turn off" in cmd or "switch off" in cmd:
                entity = self.extract_entity(cmd, ["turn off", "switch off"])
                return await self.turn_off(entity)

            # Set value
            elif "set" in cmd and "to" in cmd:
                return await self.set_value(cmd)

            # Status
            elif "status" in cmd or "state" in cmd:
                entity = self.extract_entity(cmd, ["status", "state", "of"])
                return await self.get_status(entity)

            # List devices
            elif "list" in cmd or "show all" in cmd:
                return await self.list_devices()

            # Temperature
            elif "temperature" in cmd or "temp" in cmd:
                return await self.get_temperature()

            # Scene
            elif "scene" in cmd or "activate" in cmd:
                scene = self.extract_entity(cmd, ["scene", "activate"])
                return await self.activate_scene(scene)

            # Automation
            elif "automation" in cmd or "trigger" in cmd:
                automation = self.extract_entity(cmd, ["automation", "trigger"])
                return await self.trigger_automation(automation)

            # Help
            else:
                return self.get_help()

        except Exception as e:
            _LOGGER.error(f"Command processing error: {e}")
            return f"❌ Error: {str(e)}"

    def extract_entity(self, text: str, keywords: list) -> str:
        """Extract entity name from command text."""
        for keyword in keywords:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    entity = parts[1].strip()
                    entity = entity.replace("the", "").strip()
                    return entity
        return text

    async def turn_on(self, entity_name: str) -> str:
        """Turn on an entity."""
        entity_id = await self.find_entity_id(entity_name)
        if not entity_id:
            return f"❌ Device '{entity_name}' not found"

        await self.hass.services.async_call(
            "homeassistant",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True
        )

        return f"✅ Turned on {entity_name}"

    async def turn_off(self, entity_name: str) -> str:
        """Turn off an entity."""
        entity_id = await self.find_entity_id(entity_name)
        if not entity_id:
            return f"❌ Device '{entity_name}' not found"

        await self.hass.services.async_call(
            "homeassistant",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True
        )

        return f"✅ Turned off {entity_name}"

    async def set_value(self, command: str) -> str:
        """Set entity to a specific value."""
        parts = command.split("to")
        if len(parts) != 2:
            return "❌ Invalid format. Use: set [device] to [value]"

        entity_name = parts[0].replace("set", "").strip()
        value = parts[1].strip()

        entity_id = await self.find_entity_id(entity_name)
        if not entity_id:
            return f"❌ Device '{entity_name}' not found"

        domain = entity_id.split(".")[0]

        # Handle lights
        if domain == "light":
            try:
                brightness = int(value.replace("%", ""))
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": entity_id, "brightness_pct": brightness},
                    blocking=True
                )
                return f"✅ Set {entity_name} to {brightness}%"
            except ValueError:
                return "❌ Invalid brightness value"

        # Handle climate
        elif domain == "climate":
            try:
                temp = float(value.replace("°", "").replace("c", "").replace("f", ""))
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": temp},
                    blocking=True
                )
                return f"✅ Set {entity_name} to {temp}°"
            except ValueError:
                return "❌ Invalid temperature value"

        # Handle covers
        elif domain == "cover":
            try:
                position = int(value.replace("%", ""))
                await self.hass.services.async_call(
                    "cover",
                    "set_cover_position",
                    {"entity_id": entity_id, "position": position},
                    blocking=True
                )
                return f"✅ Set {entity_name} to {position}%"
            except ValueError:
                return "❌ Invalid position value"

        return "❌ Cannot set value for this device type"

    async def get_status(self, entity_name: str) -> str:
        """Get entity status."""
        entity_id = await self.find_entity_id(entity_name)
        if not entity_id:
            return f"❌ Device '{entity_name}' not found"

        state = self.hass.states.get(entity_id)
        if not state:
            return f"❌ Could not get status for {entity_name}"

        attrs = state.attributes
        status = f"📊 *{attrs.get('friendly_name', entity_name)}*\n"
        status += f"State: {state.state}\n"

        # Add relevant attributes
        if "temperature" in attrs:
            status += f"Temperature: {attrs['temperature']}°\n"
        if "current_temperature" in attrs:
            status += f"Current: {attrs['current_temperature']}°\n"
        if "humidity" in attrs:
            status += f"Humidity: {attrs['humidity']}%\n"
        if "brightness" in attrs:
            brightness_pct = int((attrs["brightness"] / 255) * 100)
            status += f"Brightness: {brightness_pct}%\n"
        if "battery_level" in attrs:
            status += f"Battery: {attrs['battery_level']}%\n"

        return status

    async def list_devices(self) -> str:
        """List available entities grouped by domain."""
        states = self.hass.states.async_all()
        devices = {}

        relevant_domains = [
            "light", "switch", "climate", "sensor",
            "binary_sensor", "fan", "cover", "lock",
            "media_player", "camera"
        ]

        for state in states:
            domain = state.entity_id.split(".")[0]
            if domain in relevant_domains:
                if domain not in devices:
                    devices[domain] = []
                name = state.attributes.get("friendly_name", state.entity_id)
                devices[domain].append(name)

        if not devices:
            return "❌ No devices found"

        result = "📱 *Available Devices*\n\n"
        for domain, entities in sorted(devices.items()):
            result += f"*{domain.upper().replace('_', ' ')}*\n"
            for entity in sorted(entities)[:5]:
                result += f"  • {entity}\n"
            if len(entities) > 5:
                result += f"  ... and {len(entities) - 5} more\n"
            result += "\n"

        return result

    async def get_temperature(self) -> str:
        """Get temperature from all sensors."""
        states = self.hass.states.async_all()
        temps = []

        for state in states:
            # Check sensors with temperature
            if state.entity_id.startswith("sensor."):
                if state.attributes.get("device_class") == "temperature":
                    name = state.attributes.get("friendly_name", state.entity_id)
                    unit = state.attributes.get("unit_of_measurement", "")
                    temps.append(f"{name}: {state.state}{unit}")

            # Check climate entities
            elif state.entity_id.startswith("climate."):
                if "current_temperature" in state.attributes:
                    name = state.attributes.get("friendly_name", state.entity_id)
                    temp = state.attributes["current_temperature"]
                    temps.append(f"{name}: {temp}°")

        if temps:
            return "🌡️ *Temperatures*\n" + "\n".join(temps)
        else:
            return "❌ No temperature sensors found"

    async def activate_scene(self, scene_name: str) -> str:
        """Activate a scene."""
        entity_id = await self.find_entity_id(scene_name, domain="scene")
        if not entity_id:
            return f"❌ Scene '{scene_name}' not found"

        await self.hass.services.async_call(
            "scene",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True
        )

        return f"✅ Activated scene: {scene_name}"

    async def trigger_automation(self, automation_name: str) -> str:
        """Trigger an automation."""
        entity_id = await self.find_entity_id(automation_name, domain="automation")
        if not entity_id:
            return f"❌ Automation '{automation_name}' not found"

        await self.hass.services.async_call(
            "automation",
            "trigger",
            {"entity_id": entity_id},
            blocking=True
        )

        return f"✅ Triggered automation: {automation_name}"

    async def find_entity_id(self, entity_name: str, domain: str = None) -> Optional[str]:
        """Find entity ID by friendly name or partial match."""
        states = self.hass.states.async_all()
        name_lower = entity_name.lower()

        # Filter by domain if specified
        if domain:
            states = [s for s in states if s.entity_id.startswith(f"{domain}.")]

        # Try exact friendly name match
        for state in states:
            friendly_name = state.attributes.get("friendly_name", "").lower()
            if friendly_name == name_lower:
                return state.entity_id

        # Try partial match
        for state in states:
            friendly_name = state.attributes.get("friendly_name", "").lower()
            entity_id = state.entity_id.lower()

            if name_lower in friendly_name or name_lower in entity_id:
                return state.entity_id

        return None

    async def send_message(self, message: str):
        """Send message to WhatsApp group."""
        if not self.group_id:
            _LOGGER.error("Group not found, cannot send message")
            return

        try:
            await self.hass.async_add_executor_job(
                self.wa_client.send_message,
                self.group_id,
                message
            )
        except Exception as e:
            _LOGGER.error(f"Error sending message: {e}")

    def get_help(self) -> str:
        """Get help message."""
        return """🤖 *WhatsApp Home Control*

*Basic Commands:*
• Turn on [device]
• Turn off [device]  
• Set [device] to [value]
• Status of [device]

*Information:*
• List devices
• Temperature

*Advanced:*
• Activate [scene]
• Trigger [automation]

*Examples:*
• "Turn on living room light"
• "Set bedroom light to 50%"
• "Status of thermostat"
• "Activate movie scene"

Send voice messages too! 🎤"""