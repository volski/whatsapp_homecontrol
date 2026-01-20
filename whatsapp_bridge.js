#!/usr/bin/env node
/**
 * WhatsApp to Home Assistant Bridge
 * 
 * This bridge connects WhatsApp Web to Home Assistant via MQTT
 * No external URL exposure required - fully local communication
 * 
 * Setup:
 * 1. npm install whatsapp-web.js qrcode-terminal mqtt
 * 2. Configure MQTT broker in Home Assistant
 * 3. Update GROUP_NAME below
 * 4. Run: node whatsapp_bridge.js
 * 5. Scan QR code with WhatsApp
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const mqtt = require('mqtt');

// Configuration
const MQTT_BROKER = process.env.MQTT_BROKER || 'mqtt://192.168.20.32:1883';
const MQTT_USERNAME = process.env.MQTT_USERNAME || 'mqttuser';
const MQTT_PASSWORD = process.env.MQTT_PASSWORD || 'mqttpass';
const GROUP_NAME = process.env.GROUP_NAME || 'homecontrol';

// MQTT Topics
const TOPIC_MESSAGE_IN = 'whatsapp/message/in';
const TOPIC_MESSAGE_OUT = 'whatsapp/message/out';
const TOPIC_STATUS = 'whatsapp/status';

console.log('🚀 Starting WhatsApp to Home Assistant Bridge...');

// Connect to MQTT
const mqttOptions = {};
if (MQTT_USERNAME) {
    mqttOptions.username = MQTT_USERNAME;
    mqttOptions.password = MQTT_PASSWORD;
}

const mqttClient = mqtt.connect(MQTT_BROKER, mqttOptions);

mqttClient.on('connect', () => {
    console.log('✅ Connected to MQTT broker');
    mqttClient.subscribe(TOPIC_MESSAGE_OUT);
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ status: 'connecting' }));
});

mqttClient.on('error', (error) => {
    console.error('❌ MQTT Error:', error);
});

// Initialize WhatsApp Client
const waClient = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

waClient.on('qr', (qr) => {
    console.log('\n📱 Scan this QR code with WhatsApp:\n');
    qrcode.generate(qr, { small: true });
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ 
        status: 'qr_code', 
        qr: qr 
    }));
});

waClient.on('authenticated', () => {
    console.log('✅ WhatsApp authenticated');
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ status: 'authenticated' }));
});

waClient.on('ready', async () => {
    console.log('✅ WhatsApp client ready!');
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ 
        status: 'ready',
        timestamp: new Date().toISOString()
    }));
    
    // Find and log the control group
    const chats = await waClient.getChats();
    const controlGroup = chats.find(c => c.isGroup && c.name === GROUP_NAME);
    if (controlGroup) {
        console.log(`✅ Found control group: ${GROUP_NAME}`);
    } else {
        console.log(`⚠️  Control group "${GROUP_NAME}" not found. Please create it.`);
    }
});

waClient.on('disconnected', (reason) => {
    console.log('❌ WhatsApp disconnected:', reason);
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ 
        status: 'disconnected',
        reason: reason
    }));
});

// Forward WhatsApp messages to Home Assistant
waClient.on('message', async (msg) => {
    try {
        const chat = await msg.getChat();
        
        // Only process messages from the control group
        if (chat.isGroup && chat.name === GROUP_NAME) {
            const contact = await msg.getContact();
            const payload = {
                from: contact.pushname || contact.number,
                body: msg.body,
                timestamp: msg.timestamp,
                hasMedia: msg.hasMedia,
                type: msg.type,
                isForwarded: msg.isForwarded
            };
            
            console.log(`📨 Message from ${payload.from}: ${msg.body}`);
            mqttClient.publish(TOPIC_MESSAGE_IN, JSON.stringify(payload));
        }
    } catch (error) {
        console.error('Error processing message:', error);
    }
});

// Listen for commands from Home Assistant
mqttClient.on('message', async (topic, message) => {
    if (topic === TOPIC_MESSAGE_OUT) {
        try {
            const data = JSON.parse(message.toString());
            const chats = await waClient.getChats();
            const chat = chats.find(c => c.isGroup && c.name === GROUP_NAME);
            
            if (chat) {
                await chat.sendMessage(data.message || data.body || data.text);
                console.log(`📤 Sent to WhatsApp: ${data.message || data.body || data.text}`);
            } else {
                console.error(`❌ Group "${GROUP_NAME}" not found`);
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }
});

// Handle shutdown gracefully
process.on('SIGINT', async () => {
    console.log('\n👋 Shutting down...');
    mqttClient.publish(TOPIC_STATUS, JSON.stringify({ status: 'shutdown' }));
    await waClient.destroy();
    mqttClient.end();
    process.exit(0);
});

// Initialize WhatsApp client
console.log('🔄 Initializing WhatsApp client...');
waClient.initialize();
