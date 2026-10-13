import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import mongoose from 'mongoose';
import axios from 'axios';
import { config } from './config.js';
import authRoutes from './routes/auth.js';
import scanRoutes from './routes/scans.js';
import dashboardRoutes from './routes/dashboard.js';

const app = express();
app.use(helmet());
app.use(cors({ origin: config.corsOrigin }));
app.use(express.json({ limit: '1mb' }));
app.use(morgan('combined'));
app.use('/api', rateLimit({ windowMs: 60_000, limit: 120, standardHeaders: 'draft-7' }));
app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'privacy-risk-api' }));
app.use('/api/auth', authRoutes);
app.use('/api/scans', scanRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  if (axios.isAxiosError(err)) {
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
  if (err?.name === 'ZodError') return res.status(400).json({ message: 'Invalid request', issues: err.issues });
  if (err?.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ message: 'File exceeds 5 MB limit' });
  return res.status(500).json({ message: 'Internal server error' });
});

mongoose.connect(config.mongoUri).then(() => app.listen(config.port, () => console.log(`API listening on ${config.port}`))).catch(err => { console.error('MongoDB connection failed', err); process.exit(1); });
