import { Router } from 'express';
import mongoose from 'mongoose';
import Scan from '../models/Scan.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();
router.get('/summary', requireAuth, async (req, res, next) => {
  try {
    const userId = req.userId;
    const [total, groups, recent] = await Promise.all([
      Scan.countDocuments({ userId }),
      Scan.aggregate([{ $match: { userId: new mongoose.Types.ObjectId(userId) } }, { $group: { _id: '$riskLevel', count: { $sum: 1 } } }]),
      Scan.find({ userId }).sort({ createdAt: -1 }).limit(5).select('sourceType sourceName riskLevel riskScore createdAt')
    ]);
    const distribution = Object.fromEntries(groups.map((g: any) => [g._id, g.count]));
    return res.json({ totalScans: total, distribution, recent });
  } catch (e) { next(e); }
});
export default router;
