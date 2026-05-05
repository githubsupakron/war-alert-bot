"""
News Analyzer — Keyword Matching (ฟรี 100% ไม่ต้องใช้ AI API)
"""

DANGER_KEYWORDS = [
    "attack", "attacked", "strikes", "strike", "struck",
    "missile", "missiles", "rocket", "rockets", "bomb", "bombing",
    "explosion", "explode", "blast",
    "invasion", "invade", "invaded",
    "war", "warfare", "combat", "battle",
    "airstrike", "air strike", "airstrikes",
    "military operation", "troops deployed",
    "killed", "casualties", "dead", "deaths",
    "shoot down", "shot down", "fired at",
    "nuclear threat", "drone attack",
    "escalation", "escalate",
    "conflict erupts", "fighting breaks",
    "โจมตี", "ยิงถล่ม", "ระเบิด", "สงคราม", "ขีปนาวุธ",
    "บุกรุก", "เสียชีวิต", "ปะทะ",
]

PEACE_KEYWORDS = [
    "ceasefire", "cease-fire", "cease fire",
    "peace talks", "peace deal", "peace agreement",
    "negotiation", "negotiations", "negotiate",
    "truce", "armistice", "treaty", "accord",
    "diplomacy", "diplomatic",
    "withdraw", "withdrawal", "pullout",
    "de-escalation", "deescalation",
    "hostage deal", "prisoner exchange",
    "mediation", "end of war", "reconciliation",
    "หยุดยิง", "เจรจา", "สันติภาพ", "ถอนทหาร", "ยุติสงคราม",
]


def analyze_news(title: str, description: str) -> dict:
    text = (title + " " + (description or "")).lower()
    danger_score = sum(1 for kw in DANGER_KEYWORDS if kw.lower() in text)
    peace_score  = sum(1 for kw in PEACE_KEYWORDS  if kw.lower() in text)

    if danger_score > 0 and danger_score >= peace_score:
        return {
            "category": "danger",
            "market_impact": "เหตุการณ์ความรุนแรงมักทำให้ทองคำพุ่งและหุ้นร่วงในระยะสั้น",
        }
    elif peace_score > 0 and peace_score > danger_score:
        return {
            "category": "peace",
            "market_impact": "ข่าวสันติภาพมักทำให้ตลาดหุ้นฟื้นตัวและทองคำปรับลง",
        }
    return {"category": "neutral", "market_impact": ""}


def build_alert_message(
    title_en: str,
    title_th: str,
    url: str,
    analysis: dict,
    published_at: str,
) -> str | None:
    category = analysis.get("category", "neutral")

    # Show TH title prominently; show EN subtitle only if different
    has_translation = title_th and title_th != title_en
    title_main = title_th if has_translation else title_en
    title_sub = f"\n   🔤 {title_en}" if has_translation else ""

    if category == "danger":
        return (
            f"🚨 WAR ALERT - ระวัง!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📰 {title_main}{title_sub}\n\n"
            f"📊 ผลกระทบตลาดที่คาดการณ์:\n"
            f"  • ทองคำ: 📈 อาจพุ่งสูง (safe haven)\n"
            f"  • หุ้น: 📉 อาจร่วงแรง (risk-off)\n"
            f"  • 💵 USD: อาจแข็งค่า (flight to safety)\n\n"
            f"💡 {analysis.get('market_impact', '')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 {url}\n"
            f"🕐 {published_at}"
        )
    elif category == "peace":
        return (
            f"☮️ PEACE NEWS - ข่าวดี!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📰 {title_main}{title_sub}\n\n"
            f"📊 ผลกระทบตลาดที่คาดการณ์:\n"
            f"  • ทองคำ: 📉 อาจลดลง (ลด safe haven demand)\n"
            f"  • หุ้น: 📈 อาจฟื้นตัว (risk-on)\n"
            f"  • 🌏 ตลาดเอเชีย: อาจบวก\n\n"
            f"💡 {analysis.get('market_impact', '')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 {url}\n"
            f"🕐 {published_at}"
        )
    return None
