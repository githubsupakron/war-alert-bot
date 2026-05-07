"""
News Analyzer — Manual Keyword Classifier

First pass: weighted keyword matching with confidence scoring.
Manual mode uses these keyword scores directly. AI mode bypasses this module
for classification and lets CodeSmart choose danger, peace, or neutral.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# ── Built-in weighted keyword defaults ────────────────────────────────────────
# Custom keywords from settings get weight 1.0; built-ins use higher weights
# for terms that are unambiguously severe.

_DANGER_DEFAULTS: dict[str, float] = {
    "missile": 3, "missiles": 3,
    "airstrike": 3, "air strike": 3, "airstrikes": 3,
    "invasion": 3, "invade": 3, "invaded": 3,
    "nuclear threat": 3,
    "drone attack": 2,
    "attack": 2, "attacked": 2, "strikes": 2, "strike": 2, "struck": 2,
    "rocket": 2, "rockets": 2, "bomb": 2, "bombing": 2,
    "explosion": 2, "explode": 2, "blast": 2,
    "war": 2, "warfare": 2, "combat": 2, "battle": 2,
    "military operation": 2, "troops deployed": 2,
    "conflict erupts": 2, "fighting breaks": 2,
    "killed": 1, "casualties": 1, "dead": 1, "deaths": 1,
    "shoot down": 1, "shot down": 1, "fired at": 1,
    "escalation": 1, "escalate": 1,
    # Thai
    "โจมตี": 2, "ยิงถล่ม": 2, "ระเบิด": 2, "สงคราม": 2, "ขีปนาวุธ": 3,
    "บุกรุก": 2, "เสียชีวิต": 1, "ปะทะ": 2,
}

_PEACE_DEFAULTS: dict[str, float] = {
    "ceasefire": 3, "cease-fire": 3, "cease fire": 3,
    "peace agreement": 3, "peace deal": 3, "end of war": 3,
    "de-escalation": 3, "deescalation": 3,
    "armistice": 3,
    "treaty": 2, "accord": 2,
    "peace talks": 2, "negotiation": 2, "negotiations": 2, "negotiate": 2,
    "truce": 2, "withdraw": 2, "withdrawal": 2, "pullout": 2,
    "hostage deal": 2, "prisoner exchange": 2, "mediation": 2, "reconciliation": 2,
    "diplomacy": 1, "diplomatic": 1,
    # Thai
    "หยุดยิง": 3, "เจรจา": 2, "สันติภาพ": 2, "ถอนทหาร": 2, "ยุติสงคราม": 3,
}


def _parse_kwlist(csv: str) -> list[str]:
    return [k.strip() for k in csv.split(",") if k.strip()]


def _build_weights(defaults: dict[str, float], custom_csv: str) -> dict[str, float]:
    weights = dict(defaults)
    for kw in _parse_kwlist(custom_csv):
        if kw not in weights:
            weights[kw] = 1.0
    return weights


def keyword_classify(
    title: str,
    description: str,
    danger_kw_csv: str = "",
    peace_kw_csv: str = "",
    negative_kw_csv: str = "",
) -> dict:
    """
    Weighted keyword first-pass classifier.

    Returns a dict with:
      category, confidence, reason, market_impact, matched_keywords, negative_matches
    """
    text = (title + " " + (description or "")).lower()

    danger_weights = _build_weights(_DANGER_DEFAULTS, danger_kw_csv)
    peace_weights  = _build_weights(_PEACE_DEFAULTS,  peace_kw_csv)
    neg_keywords   = _parse_kwlist(negative_kw_csv)

    matched_danger: list[str] = []
    matched_peace:  list[str] = []
    neg_matches:    list[str] = []

    danger_score = 0.0
    for kw, w in danger_weights.items():
        if kw.lower() in text:
            matched_danger.append(kw)
            danger_score += w

    peace_score = 0.0
    for kw, w in peace_weights.items():
        if kw.lower() in text:
            matched_peace.append(kw)
            peace_score += w

    for kw in neg_keywords:
        if kw.lower() in text:
            neg_matches.append(kw)

    # Neutral: no signal on either side
    if danger_score == 0 and peace_score == 0:
        return {
            "category":        "neutral",
            "confidence":      0.0,
            "reason":          "No significant keywords matched",
            "market_impact":   "",
            "matched_keywords": [],
            "negative_matches": neg_matches,
        }

    if danger_score >= peace_score:
        category     = "danger"
        winner       = danger_score
        loser        = peace_score
        market_impact = "เหตุการณ์ความรุนแรงมักทำให้ทองคำพุ่งและหุ้นร่วงในระยะสั้น"
    else:
        category     = "peace"
        winner       = peace_score
        loser        = danger_score
        market_impact = "ข่าวสันติภาพมักทำให้ตลาดหุ้นฟื้นตัวและทองคำปรับลง"

    # Confidence: how dominant the winner is relative to both sides.
    # danger=5,peace=0 → 5/(5+1)≈0.83; danger=5,peace=3 → 5/(5+3)=0.625
    confidence = winner / (winner + max(1.0, loser))

    # Each negative keyword hit reduces confidence by 0.15
    if neg_matches:
        confidence = max(0.0, confidence - 0.15 * len(neg_matches))

    all_matched = matched_danger + matched_peace
    reason = (
        f"Keyword match: {category} score={winner:.1f}, opposing={loser:.1f}, "
        f"matched={all_matched}"
    )
    if neg_matches:
        reason += f", negative={neg_matches}"

    # Heavy negative context can force neutral
    if neg_matches and confidence < 0.1:
        return {
            "category":        "neutral",
            "confidence":      round(confidence, 3),
            "reason":          f"Negative keywords neutralized result: {neg_matches}",
            "market_impact":   "",
            "matched_keywords": all_matched,
            "negative_matches": neg_matches,
        }

    return {
        "category":        category,
        "confidence":      round(confidence, 3),
        "reason":          reason,
        "market_impact":   market_impact,
        "matched_keywords": all_matched,
        "negative_matches": neg_matches,
    }


def analyze_news(title: str, description: str) -> dict:
    """Backward-compatible wrapper — returns only category and market_impact."""
    result = keyword_classify(title, description)
    return {"category": result["category"], "market_impact": result["market_impact"]}


def build_alert_message(
    title_en: str,
    title_th: str,
    url: str,
    analysis: dict,
    published_at: str,
) -> str | None:
    logger.info("build_alert_message analysis=%s", analysis)
    category = analysis.get("category", "neutral")

    has_translation = title_th and title_th != title_en
    title_main = title_th if has_translation else title_en
    title_sub  = f"\n   🔤 {title_en}" if has_translation else ""

    summary_th            = analysis.get("summary_th", "")
    market_impact         = analysis.get("market_impact", "")
    gold_impact           = analysis.get("gold_impact", "")
    stock_impact          = analysis.get("stock_impact", "")
    usd_impact            = analysis.get("usd_impact", "")
    asia_impact           = analysis.get("asia_impact", "")
    crypto_currency_impact = analysis.get("crypto_currency_impact", "")

    summary_block = f"\n🧠 สรุปข่าว:\n  • {summary_th}\n" if summary_th else ""

    if category == "danger":
        gold_line   = gold_impact            or "📈 อาจพุ่งสูง (safe haven)"
        stock_line  = stock_impact           or "📉 อาจร่วงแรง (risk-off)"
        usd_line    = usd_impact             or "อาจแข็งค่า (flight to safety)"
        crypto_line = crypto_currency_impact or "⚡ อาจผันผวนสูง"
        return (
            f"🚨 WAR ALERT - ระวัง!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📰 {title_main}{title_sub}\n"
            f"{summary_block}\n"
            f"📊 ผลกระทบตลาดที่คาดการณ์:\n"
            f"  • ทองคำ: {gold_line}\n"
            f"  • หุ้น: {stock_line}\n"
            f"  • 💵 USD: {usd_line}\n"
            f"  • ₿ คริปโต: {crypto_line}\n\n"
            f"💡 {market_impact}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 {url}\n"
            f"🕐 {published_at}"
        )
    elif category == "peace":
        gold_line   = gold_impact            or "📉 อาจลดลง (ลด safe haven demand)"
        stock_line  = stock_impact           or "📈 อาจฟื้นตัว (risk-on)"
        asia_line   = asia_impact            or "อาจบวก"
        crypto_line = crypto_currency_impact or "📈 อาจฟื้นตัว (risk-on)"
        return (
            f"☮️ PEACE NEWS - ข่าวดี!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📰 {title_main}{title_sub}\n"
            f"{summary_block}\n"
            f"📊 ผลกระทบตลาดที่คาดการณ์:\n"
            f"  • ทองคำ: {gold_line}\n"
            f"  • หุ้น: {stock_line}\n"
            f"  • 🌏 ตลาดเอเชีย: {asia_line}\n"
            f"  • ₿ คริปโต: {crypto_line}\n\n"
            f"💡 {market_impact}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 {url}\n"
            f"🕐 {published_at}"
        )
    return None
