"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const mongoose_1 = __importDefault(require("mongoose"));
const Scan_js_1 = __importDefault(require("../models/Scan.js"));
const auth_js_1 = require("../middleware/auth.js");
const router = (0, express_1.Router)();
router.get('/summary', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        const userId = req.userId;
        const [total, groups, recent] = await Promise.all([
            Scan_js_1.default.countDocuments({ userId }),
            Scan_js_1.default.aggregate([{ $match: { userId: new mongoose_1.default.Types.ObjectId(userId) } }, { $group: { _id: '$riskLevel', count: { $sum: 1 } } }]),
            Scan_js_1.default.find({ userId }).sort({ createdAt: -1 }).limit(5).select('sourceType sourceName riskLevel riskScore createdAt')
        ]);
        const distribution = Object.fromEntries(groups.map((g) => [g._id, g.count]));
        return res.json({ totalScans: total, distribution, recent });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
