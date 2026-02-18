import '@testing-library/jest-dom'

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

// Polyfill fetch for Node.js test environment
global.fetch = require('node-fetch')
global.WebSocket = require('ws')