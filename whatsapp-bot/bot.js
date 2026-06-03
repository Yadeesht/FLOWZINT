const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const fs = require('fs');
const path = require('path');
const os = require('os');

// Resolve local Chrome executable path on Windows to avoid Puppeteer download failures
let executablePath = '';
if (process.platform === 'win32') {
    const possiblePaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        path.join(os.homedir(), 'AppData\\Local\\Google\\Chrome\\Application\\chrome.exe')
    ];
    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            executablePath = p;
            break;
        }
    }
    if (executablePath) {
        console.log(`[WhatsApp Bot] Found local Google Chrome at: ${executablePath}`);
    } else {
        console.log('[WhatsApp Bot] Warning: Local Google Chrome executable not found. Running default.');
    }
}

// Initialize WhatsApp Web Client
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './whatsapp_session' // Persistent session directory
    }),
    puppeteer: {
        headless: true,
        executablePath: executablePath || undefined,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            '--disable-blink-features=AutomationControlled'
        ]
    }
});

// Display QR Code or request Pairing Code
client.on('qr', async (qr) => {
    const botPhone = process.env.BOT_PHONE;
    if (botPhone) {
        const cleanPhone = botPhone.replace(/\D/g, '');
        console.log(`\n[WhatsApp Bot] Attempting to generate pairing code for phone: +${cleanPhone}...`);
        try {
            const pairingCode = await client.requestPairingCode(cleanPhone);
            console.log('\n======================================================');
            console.log(`🔑 YOUR WHATSAPP PAIRING CODE:  ${pairingCode}`);
            console.log('======================================================\n');
            console.log('Instructions:');
            console.log('1. Open WhatsApp on your phone.');
            console.log('2. Go to Linked Devices -> Link a Device.');
            console.log('3. Select "Link with phone number instead".');
            console.log('4. Enter the code shown above.\n');
        } catch (err) {
            console.error('[WhatsApp Bot] Pairing code generation failed. Falling back to QR code:', err);
            console.log('\n--- SCAN THE QR CODE BELOW WITH WHATSAPP LINKED DEVICES ---');
            qrcode.generate(qr, { small: true });
        }
    } else {
        console.log('\n--- SCAN THE QR CODE BELOW WITH WHATSAPP LINKED DEVICES ---');
        qrcode.generate(qr, { small: true });
        console.log('\n💡 Tip: To pair using a phone number instead of a QR code,');
        console.log('run the bot with BOT_PHONE=91XXXXXXXXXX (your bot\'s phone number with country code).');
    }
});

client.on('ready', () => {
    console.log('WhatsApp Bot successfully linked and running!');
});

// Listen for incoming WhatsApp messages and route them to our FastAPI backend chatbot
client.on('message', async (msg) => {
    // Only process private chats (ignore groups)
    if (msg.from.endsWith('@c.us')) {
        const rawPhone = msg.from.split('@')[0];
        const senderFormatted = `whatsapp:+${rawPhone}`;
        
        try {
            const contact = await msg.getContact();
            const profileName = contact.pushname || 'WhatsApp Student';
            
            console.log(`[WhatsApp Incoming] Reply from ${profileName} (${rawPhone}): ${msg.body}`);

            // Construct x-www-form-urlencoded payload expected by FastAPI webhook
            const params = new URLSearchParams();
            params.append('From', senderFormatted);
            params.append('Body', msg.body);
            params.append('ProfileName', profileName);

            const response = await fetch(`${BACKEND_URL}/api/whatsapp/incoming`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: params
            });

            if (!response.ok) {
                console.error(`[Webhook Error] Failed to route to chatbot. Status: ${response.status}`);
            }
        } catch (err) {
            console.error('[Webhook Dispatch Error]', err);
        }
    }
});

// Outbound API Endpoint for FastAPI backend to send messages
app.post('/send', async (req, res) => {
    const { phone, message } = req.body;

    if (!phone || !message) {
        return res.status(400).json({ error: 'Missing phone or message in payload' });
    }

    try {
        // Clean phone number format for whatsapp-web.js (must end with @c.us)
        let cleanPhone = phone.replace(/\D/g, ''); // strip non-digits
        if (cleanPhone.length === 10) {
            cleanPhone = `91${cleanPhone}`; // default to Indian country code
        }
        
        const chatId = `${cleanPhone}@c.us`;
        
        console.log(`[WhatsApp Outbound] Sending message to ${chatId}...`);
        await client.sendMessage(chatId, message);
        
        res.json({ success: true, message: `Message sent to ${cleanPhone}` });
    } catch (err) {
        console.error('[WhatsApp Send Failure]', err);
        res.status(500).json({ error: 'Failed to send WhatsApp message', details: err.message });
    }
});

// Start Express Server
app.listen(PORT, () => {
    console.log(`WhatsApp Gateway API listening on port ${PORT}`);
});

// Initialize client
client.initialize();
