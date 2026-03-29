"""
Database Models - SQLAlchemy ORM models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Signal(Base):
    """Generated trading signal model"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True)
    timeframe = Column(String(10), index=True)
    signal_type = Column(String(10))  # BUY, SELL, HOLD
    entry_price = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    confidence = Column(Float)
    strategy_name = Column(String(100))
    indicators_used = Column(JSON)
    indicator_values = Column(JSON)
    generated_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class TradeExecution(Base):
    """Executed trade model"""
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer)
    symbol = Column(String(20), index=True)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float)
    position_type = Column(String(10))  # LONG, SHORT
    status = Column(String(20))  # OPEN, CLOSED, LIQUIDATED
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    entry_at = Column(DateTime, index=True)
    exit_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetric(Base):
    """Performance tracking model"""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True)
    timeframe = Column(String(10))
    strategy = Column(String(100))
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Configuration(Base):
    """Application configuration model"""
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LLMTrainingSample(Base):
    """Samples collected for training local Transformer models"""
    __tablename__ = "llm_training_samples"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True)
    input_text = Column(Text)
    label = Column(Integer)  # 0: Bearish, 1: Neutral, 2: Bullish
    llm_provider = Column(String(50))
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
