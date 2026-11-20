const express = require('express');
const cors = require('cors');
const path = require('path');
const { generateSecret, generateOTP, verifyOTP, DEFAULT_TIME_STEP, _GRAPH } = require('./walk_otp');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// For this standalone demo, we keep the secret in memory
// In production, this would be retrieved from a database during login
const serverSecretKey = generateSecret();
const usedCounters = new Set();

console.log('✅ Server initialized with new secret key.');

// Endpoint to fetch the graph structure for visualization
app.get('/api/graph', (req, res) => {
    res.json({ graph: _GRAPH });
});

// Endpoint for the React client (and visualizer) to fetch the LIVE OTP
app.get('/api/otp/current', (req, res) => {
    const tNow = Math.floor(Date.now() / 1000);
    const tRem = DEFAULT_TIME_STEP - (tNow % DEFAULT_TIME_STEP);
    
    const { otp, counter, path } = generateOTP(serverSecretKey);
    
    res.json({
        otp,
        counter,
        timeRemaining: tRem,
        timeStep: DEFAULT_TIME_STEP,
        path
    });
});

// Endpoint for the React client to verify a submitted OTP
// This mimics the 'Login Portal' side of the demo
app.post('/api/otp/verify', (req, res) => {
    const { otp } = req.body;
    
    if (!otp || typeof otp !== 'string' || otp.length !== 6) {
        return res.status(400).json({ valid: false, message: 'Please provide a valid 6-digit OTP.' });
    }
    
    const { valid, matchedCounter } = verifyOTP(serverSecretKey, otp, 1);
    
    if (!valid) {
        return res.json({ valid: false, message: 'OTP is invalid or expired.' });
    }
    
    if (usedCounters.has(matchedCounter)) {
        return res.json({ valid: false, message: 'Replay Attack Detected! This OTP was already used.' });
    }
    
    // Mark as used
    usedCounters.add(matchedCounter);
    
    res.json({ 
        valid: true, 
        message: `Verification Successful! (Matched in time window T=${matchedCounter})` 
    });
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`🚀 Node.js Walk-OTP Server running on http://localhost:${PORT}`);
});
