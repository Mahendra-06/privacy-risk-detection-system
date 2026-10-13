"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const helmet_1 = __importDefault(require("helmet"));
const morgan_1 = __importDefault(require("morgan"));
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const mongoose_1 = __importDefault(require("mongoose"));
const axios_1 = __importDefault(require("axios"));
const config_js_1 = require("./config.js");
const auth_js_1 = __importDefault(require("./routes/auth.js"));
const scans_js_1 = __importDefault(require("./routes/scans.js"));
const dashboard_js_1 = __importDefault(require("./routes/dashboard.js"));
const app = (0, express_1.default)();
app.use((0, helmet_1.default)());
app.use((0, cors_1.default)({ origin: config_js_1.config.corsOrigin }));
app.use(express_1.default.json({ limit: '1mb' }));
app.use((0, morgan_1.default)('combined'));
app.use('/api', (0, express_rate_limit_1.default)({ windowMs: 60_000, limit: 120, standardHeaders: 'draft-7' }));
app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'privacy-risk-api' }));
app.use('/api/auth', auth_js_1.default);
app.use('/api/scans', scans_js_1.default);
app.use('/api/dashboard', dashboard_js_1.default);
app.use((err, _req, res, _next) => {
    if (axios_1.default.isAxiosError(err)) {
        const upstreamStatus = err.response?.status;
        const status = upstreamStatus && [400, 413, 415, 422, 503, 504].includes(upstreamStatus)
            ? upstreamStatus : (err.code === 'ECONNABORTED' ? 504 : 502);
        const detail = err.response?.data?.detail;
        const message = upstreamStatus === status && typeof detail === 'string'
            ? detail : (status === 504 ? 'Analysis timed out. Try a smaller document.' : 'Analysis service is unavailable. Please try again.');
        // Axios errors contain the uploaded document in config.data; never log them whole.
        console.error('Analysis request failed', { status, upstreamStatus, code: err.code });
        return res.status(status).json({ message });
    }
    console.error(err);
    if (err?.name === 'ZodError')
        return res.status(400).json({ message: 'Invalid request', issues: err.issues });
    if (err?.code === 'LIMIT_FILE_SIZE')
        return res.status(413).json({ message: 'File exceeds 5 MB limit' });
    return res.status(500).json({ message: 'Internal server error' });
});
mongoose_1.default.connect(config_js_1.config.mongoUri).then(() => app.listen(config_js_1.config.port, () => console.log(`API listening on ${config_js_1.config.port}`))).catch(err => { console.error('MongoDB connection failed', err); process.exit(1); });
