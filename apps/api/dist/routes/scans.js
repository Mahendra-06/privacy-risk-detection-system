"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const axios_1 = __importDefault(require("axios"));
const multer_1 = __importDefault(require("multer"));
const zod_1 = require("zod");
const Scan_js_1 = __importDefault(require("../models/Scan.js"));
const auth_js_1 = require("../middleware/auth.js");
const config_js_1 = require("../config.js");
const router = (0, express_1.Router)();
const upload = (0, multer_1.default)({ storage: multer_1.default.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });
const redactionEnum = zod_1.z.enum(['tagged', 'mask', 'synthetic', 'blackout']).optional().default('tagged');
const textSchema = zod_1.z.object({ text: zod_1.z.string().min(1).max(100_000), redactionMode: redactionEnum });
const urlSchema = zod_1.z.object({ url: zod_1.z.string().url().max(2048), redactionMode: redactionEnum });
async function analyze(payload) {
    const response = await axios_1.default.post(`${config_js_1.config.mlServiceUrl}/analyze`, payload, { timeout: 30_000 });
    return response.data;
}
async function persist(req, sourceType, sourceName, result, requestedMode = 'tagged') {
    const chosenMode = result.redactionMode || requestedMode;
    const variations = result.redactedVariations || { [chosenMode]: result.redactedText };
    return Scan_js_1.default.create({
        userId: req.userId,
        sourceType,
        sourceName,
        riskLevel: result.riskLevel,
        riskScore: result.riskScore,
        findings: result.findings,
        factors: result.factors,
        recommendations: result.recommendations,
        redactedPreview: result.redactedText,
        redactionMode: chosenMode,
        redactedVariations: variations,
        featureSummary: result.featureSummary
    });
}
router.post('/text', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        const { text, redactionMode } = textSchema.parse(req.body);
        const result = await analyze({ text, sourceType: 'text', redactionMode });
        const scan = await persist(req, 'text', 'Pasted text', result, redactionMode);
        return res.status(201).json({ scan, analysis: result });
    }
    catch (e) {
        next(e);
    }
});
router.post('/url', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        const { url, redactionMode } = urlSchema.parse(req.body);
        const result = await analyze({ text: url, sourceType: 'url', url, redactionMode });
        const scan = await persist(req, 'url', url, result, redactionMode);
        return res.status(201).json({ scan, analysis: result });
    }
    catch (e) {
        next(e);
    }
});
router.post('/document', auth_js_1.requireAuth, upload.single('file'), async (req, res, next) => {
    try {
        if (!req.file)
            return res.status(400).json({ message: 'File is required' });
        const allowed = new Set(['text/plain', 'text/csv', 'application/json', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg', 'image/webp', 'image/bmp', 'image/tiff']);
        if (!allowed.has(req.file.mimetype))
            return res.status(415).json({ message: 'Supported formats: TXT, CSV, JSON, PDF, DOCX, PNG, JPEG, WEBP, BMP, TIFF' });
        const rawMode = req.body.redactionMode;
        const redactionMode = ['tagged', 'mask', 'synthetic', 'blackout'].includes(rawMode) ? rawMode : 'tagged';
        const result = await analyze({ contentBase64: req.file.buffer.toString('base64'), filename: req.file.originalname, mimeType: req.file.mimetype, sourceType: 'document', redactionMode });
        const scan = await persist(req, 'document', req.file.originalname, result, redactionMode);
        return res.status(201).json({ scan, analysis: result });
    }
    catch (e) {
        next(e);
    }
});
router.get('/', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        return res.json(await Scan_js_1.default.find({ userId: req.userId }).sort({ createdAt: -1 }).limit(100));
    }
    catch (e) {
        next(e);
    }
});
router.get('/:id', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        const scan = await Scan_js_1.default.findOne({ _id: req.params.id, userId: req.userId });
        if (!scan)
            return res.status(404).json({ message: 'Scan not found' });
        return res.json(scan);
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
