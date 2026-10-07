import { Request, Response, NextFunction } from 'express';
import { verifyToken } from '../utils/jwt.js';

declare global { namespace Express { interface Request { userId?: string } } }

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) return res.status(401).json({ message: 'Authentication required' });
  try {
    req.userId = verifyToken(header.slice(7)).sub;
    next();
  } catch {
    return res.status(401).json({ message: 'Invalid or expired token' });
  }
}
