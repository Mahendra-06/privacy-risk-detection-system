"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
require("dotenv/config");
exports.config = {
    port: Number(process.env.PORT ?? 4001),
    mongoUri: process.env.MONGO_URI ?? 'mongodb://127.0.0.1:27017/privacy_risk_detection_system',
    jwtSecret: process.env.JWT_SECRET ?? 'development-only-secret',
    mlServiceUrl: process.env.ML_SERVICE_URL ?? 'http://127.0.0.1:8001',
    corsOrigin: process.env.CORS_ORIGIN ?? 'http://localhost:5174'
};
