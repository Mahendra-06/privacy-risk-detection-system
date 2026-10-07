"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const zod_1 = require("zod");
const User_js_1 = __importDefault(require("../models/User.js"));
const jwt_js_1 = require("../utils/jwt.js");
const auth_js_1 = require("../middleware/auth.js");
const router = (0, express_1.Router)();
const credentials = zod_1.z.object({ name: zod_1.z.string().min(2).max(80).optional(), email: zod_1.z.string().email(), password: zod_1.z.string().min(8).max(128) });
router.post('/register', async (req, res, next) => {
    try {
        const data = credentials.parse(req.body);
        const exists = await User_js_1.default.findOne({ email: data.email.toLowerCase() });
        if (exists)
            return res.status(409).json({ message: 'Email already registered' });
        const user = await User_js_1.default.create({ name: data.name ?? data.email.split('@')[0], email: data.email, passwordHash: await bcryptjs_1.default.hash(data.password, 12) });
        return res.status(201).json({ token: (0, jwt_js_1.signToken)(user.id), user: { id: user.id, name: user.name, email: user.email } });
    }
    catch (e) {
        next(e);
    }
});
router.post('/login', async (req, res, next) => {
    try {
        const data = credentials.pick({ email: true, password: true }).parse(req.body);
        const user = await User_js_1.default.findOne({ email: data.email.toLowerCase() });
        if (!user || !(await bcryptjs_1.default.compare(data.password, user.passwordHash)))
            return res.status(401).json({ message: 'Invalid email or password' });
        return res.json({ token: (0, jwt_js_1.signToken)(user.id), user: { id: user.id, name: user.name, email: user.email } });
    }
    catch (e) {
        next(e);
    }
});
router.get('/me', auth_js_1.requireAuth, async (req, res, next) => {
    try {
        const user = await User_js_1.default.findById(req.userId).select('_id name email createdAt');
        if (!user)
            return res.status(404).json({ message: 'User not found' });
        return res.json({ id: user.id, name: user.name, email: user.email, createdAt: user.createdAt });
    }
    catch (e) {
        next(e);
    }
});
exports.default = router;
