import mongoose, { Schema, InferSchemaType } from 'mongoose';

const userSchema = new Schema({
  name: { type: String, required: true, trim: true, maxlength: 80 },
  email: { type: String, required: true, unique: true, lowercase: true, trim: true },
  passwordHash: { type: String, required: true },
  createdAt: { type: Date, default: Date.now }
});

export type User = InferSchemaType<typeof userSchema> & { _id: mongoose.Types.ObjectId };
export default mongoose.model('User', userSchema);
