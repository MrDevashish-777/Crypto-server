import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Schema as MongooseSchema, Types } from 'mongoose';

export type SignalDocument = HydratedDocument<Signal>;

export class TakeProfit {
  @Prop({ required: true })
  tp1: number;

  @Prop({ required: true })
  tp2: number;

  @Prop({ required: true })
  tp3: number;
}

@Schema({ collection: 'signals' })
export class Signal {
  @Prop({ type: String, required: true, index: true })
  asset: string;

  @Prop({ type: String, required: true, enum: ['BUY', 'SELL'] })
  signal_type: 'BUY' | 'SELL';

  @Prop({ type: [Number], required: true })
  entry_range: number[];

  @Prop({ type: Number, required: true })
  stop_loss: number;

  @Prop({ type: Object, required: true })
  take_profit: { tp1: number; tp2: number; tp3: number };

  @Prop({ type: String, required: true, index: true })
  timeframe: string;

  @Prop({ type: Number, required: true })
  confidence: number;

  @Prop({ type: String, required: true })
  strategy: string;

  @Prop({ type: String, required: true })
  reason: string;

  @Prop({ type: String, required: true })
  validity: string;

  @Prop({ type: Date, required: true, index: true })
  created_at: Date;

  @Prop({ type: String, required: true, index: true, default: 'active' })
  status: 'active' | 'hit_tp' | 'hit_sl' | 'expired';

  @Prop({ type: String, required: true })
  risk_reward_ratio: string;

  // Internal fields for dedup/expiry. Not required by clients.
  @Prop({ type: Date })
  expires_at?: Date;

  @Prop({ type: String, required: false })
  dedup_key?: string;

  _id: Types.ObjectId;
}

export const SignalSchema = SchemaFactory.createForClass(Signal);

// Unique constraint to support "one signal per asset per cycle" via idempotency key.
SignalSchema.index({ dedup_key: 1 }, { unique: true, sparse: true });

// Fast filtering for GET /signals (active signals by asset/timeframe).
SignalSchema.index({ asset: 1, timeframe: 1, status: 1, expires_at: 1 });
SignalSchema.index({ status: 1, expires_at: 1, created_at: -1 });

