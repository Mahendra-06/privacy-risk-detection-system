import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import mongoose from 'mongoose';
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
  console.error(err);
  if (err?.name === 'ZodError') return res.status(400).json({ message: 'Invalid request', issues: err.issues });
  if (err?.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ message: 'File exceeds 5 MB limit' });
  return res.status(500).json({ message: 'Internal server error' });
});

mongoose.connect(config.mongoUri).then(() => app.listen(config.port, () => console.log(`API listening on ${config.port}`))).catch(err => { console.error('MongoDB connection failed', err); process.exit(1); });
