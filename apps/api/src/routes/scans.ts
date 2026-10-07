import { Router } from 'express';
import axios from 'axios';
import multer from 'multer';
import { z } from 'zod';
import Scan from '../models/Scan.js';
import { requireAuth } from '../middleware/auth.js';
import { config } from '../config.js';

const router = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });
const redactionEnum = z.enum(['tagged', 'mask', 'synthetic', 'blackout']).optional().default('tagged');
const textSchema = z.object({ text: z.string().min(1).max(100_000), redactionMode: redactionEnum });
const urlSchema = z.object({ url: z.string().url().max(2048), redactionMode: redactionEnum });

async function analyze(payload: Record<string, unknown>) {
  const response = await axios.post(`${config.mlServiceUrl}/analyze`, payload, { timeout: 30_000 });
  return response.data;
}

async function persist(req: any, sourceType: 'text' | 'document' | 'url', sourceName: string, result: any, requestedMode: string = 'tagged') {
  const chosenMode = result.redactionMode || requestedMode;
  const variations = result.redactedVariations || { [chosenMode]: result.redactedText };
  return Scan.create({
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

router.post('/text', requireAuth, async (req, res, next) => {
  try {
    const { text, redactionMode } = textSchema.parse(req.body);
    const result = await analyze({ text, sourceType: 'text', redactionMode });
    const scan = await persist(req, 'text', 'Pasted text', result, redactionMode);
    return res.status(201).json({ scan, analysis: result });
  } catch (e) { next(e); }
});

router.post('/url', requireAuth, async (req, res, next) => {
  try {
    const { url, redactionMode } = urlSchema.parse(req.body);
    const result = await analyze({ text: url, sourceType: 'url', url, redactionMode });
    const scan = await persist(req, 'url', url, result, redactionMode);
    return res.status(201).json({ scan, analysis: result });
  } catch (e) { next(e); }
});

router.post('/document', requireAuth, upload.single('file'), async (req, res, next) => {
  try {
    if (!req.file) return res.status(400).json({ message: 'File is required' });
    const allowed = new Set(['text/plain', 'text/csv', 'application/json', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg', 'image/webp', 'image/bmp', 'image/tiff']);
    if (!allowed.has(req.file.mimetype)) return res.status(415).json({ message: 'Supported formats: TXT, CSV, JSON, PDF, DOCX, PNG, JPEG, WEBP, BMP, TIFF' });
    const rawMode = req.body.redactionMode;
    const redactionMode = ['tagged', 'mask', 'synthetic', 'blackout'].includes(rawMode) ? rawMode : 'tagged';
    const result = await analyze({ contentBase64: req.file.buffer.toString('base64'), filename: req.file.originalname, mimeType: req.file.mimetype, sourceType: 'document', redactionMode });
    const scan = await persist(req, 'document', req.file.originalname, result, redactionMode);
    return res.status(201).json({ scan, analysis: result });
  } catch (e) { next(e); }
});

router.get('/', requireAuth, async (req, res, next) => {
  try { return res.json(await Scan.find({ userId: req.userId }).sort({ createdAt: -1 }).limit(100)); } catch (e) { next(e); }
});

router.get('/:id', requireAuth, async (req, res, next) => {
  try {
    const scan = await Scan.findOne({ _id: req.params.id, userId: req.userId });
    if (!scan) return res.status(404).json({ message: 'Scan not found' });
    return res.json(scan);
  } catch (e) { next(e); }
});

export default router;
