import jwt from 'jsonwebtoken';
import { config } from '../config.js';

export function signToken(userId: string) {
  return jwt.sign({ sub: userId }, config.jwtSecret, { expiresIn: '7d' });
}

export function verifyToken(token: string): { sub: string } {
  return jwt.verify(token, config.jwtSecret) as { sub: string };
}
