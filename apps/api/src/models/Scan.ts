import mongoose, { Schema, InferSchemaType } from 'mongoose';

const findingSchema = new Schema({
  type: String,
  valueMasked: String,
  start: Number,
  end: Number,
  confidence: Number,
  severity: String
}, { _id: false });

const scanSchema = new Schema({
  userId: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
  sourceType: { type: String, enum: ['text', 'document', 'url'], required: true },
  sourceName: { type: String, default: '' },
  riskLevel: { type: String, enum: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], required: true },
  riskScore: { type: Number, required: true },
  findings: { type: [findingSchema], default: [] },
  factors: { type: [String], default: [] },
  recommendations: { type: [String], default: [] },
  redactedPreview: { type: String, default: '' },
  redactionMode: { type: String, enum: ['tagged', 'mask', 'synthetic', 'blackout'], default: 'tagged' },
  redactedVariations: {
    tagged: { type: String, default: '' },
    mask: { type: String, default: '' },
    synthetic: { type: String, default: '' },
    blackout: { type: String, default: '' }
  },
  featureSummary: { type: Schema.Types.Mixed, default: {} },
  createdAt: { type: Date, default: Date.now, index: true }
});

export type Scan = InferSchemaType<typeof scanSchema> & { _id: mongoose.Types.ObjectId };
export default mongoose.model('Scan', scanSchema);
