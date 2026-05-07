from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./war_alert.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class NewsItem(Base):
    __tablename__ = "news_items"

    id            = Column(Integer, primary_key=True, index=True)
    title         = Column(Text, nullable=False)
    title_th      = Column(Text)                          # Thai translation
    description   = Column(Text)
    url           = Column(String(500))
    source        = Column(String(200))
    published_at  = Column(DateTime)
    category      = Column(String(20), default="neutral") # danger / peace / neutral
    alert_message = Column(Text)
    line_sent     = Column(Boolean, default=False)
    facebook_sent = Column(Boolean, default=False)        # Facebook page post
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Classifier audit fields
    classification_confidence = Column(Float, default=0.0)
    classification_reason     = Column(Text, default="")
    llm_used                  = Column(Boolean, default=False)
    llm_fallback              = Column(Boolean, default=False)


class Setting(Base):
    __tablename__ = "settings"

    key   = Column(String(100), primary_key=True)
    value = Column(Text)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_column(db, sql: str):
    """Run an ALTER TABLE safely — ignore if column already exists."""
    try:
        db.execute(text(sql))
        db.commit()
    except Exception:
        db.rollback()


def init_db():
    Base.metadata.create_all(bind=engine)

    # Safe migrations for new columns
    db = SessionLocal()
    try:
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN title_th TEXT")
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN facebook_sent BOOLEAN DEFAULT 0")
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN classification_confidence REAL DEFAULT 0.0")
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN classification_reason TEXT DEFAULT ''")
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN llm_used BOOLEAN DEFAULT 0")
        _migrate_column(db, "ALTER TABLE news_items ADD COLUMN llm_fallback BOOLEAN DEFAULT 0")
    finally:
        db.close()

    # Default settings
    db = SessionLocal()
    try:
        defaults = {
            "auto_fetch":            "false",
            "fetch_interval_value":  "30",
            "fetch_interval_unit":   "minutes",
            "keywords":              "Iran attack,Israel strike,US military,war erupts,missile launch,ceasefire,peace talks,negotiation",
            "danger_keywords":       "attack,strike,missile,bomb,war,invasion,explosion,shoot,fire,killed,casualties",
            "peace_keywords":        "ceasefire,negotiation,peace talks,agreement,treaty,withdraw,diplomacy,truce",
            "max_news_age_hours":    "6",
            # Alert channels (LINE on by default, Facebook off until configured)
            "line_enabled":          "true",
            "facebook_enabled":      "false",
            # Classifier
            "classifier_mode":            "keyword",  # "keyword" or "ai"
            "negative_keywords":          "",
        }
        for key, value in defaults.items():
            if not db.query(Setting).filter(Setting.key == key).first():
                db.add(Setting(key=key, value=value))
        db.commit()
    finally:
        db.close()
