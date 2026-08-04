"""SK 하이닉스 투자 레포트 생성기

Google News RSS + Yahoo Finance 주가 데이터를 결합해
기술 분석 기반 매수/매도 추천 HTML 레포트를 생성한다.

사용법:
    python sk_hynix_report.py              # 기본: 최근 3개월
    python sk_hynix_report.py --months 6   # 6개월 데이터

준비:
    외부 API 키 불필요 (Google News RSS + Yahoo Finance chart API 사용)
    pandas 필요 (pip install pandas)
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
from datetime import timezone, timedelta
import argparse
import base64
import ssl
import xml.etree.ElementTree as ET


# ===== 설정 =====
TICKER = "000660.KS"          # SK 하이닉스 (Yahoo Finance 심볼)
QUERY = "SK 하이닉스"
NEWS_COUNT = 10
import re  # 정규식 (뉴스 태그 제거/감성 분석)


def clean_text(s):
    return (
        s.replace("&quot;", '"').replace("&#39;", "'")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    )


# ===== 뉴스 감성 분석 (규칙 기반, 외부 API 불필요) =====
# 긍정/부정 단어 사전 (한국어 주식/반도체 맥락)
POSITIVE_WORDS = [
    "상승", "급등", "반등", "호조", "개선", "증가", "사상최고", "최대", "신기록",
    "성장", "흑자", "이익", "수주", "계약", "체결", "투자", "확대", "격상",
    "목표가", "상향", "추천", "매수", "긍정적", "기대", "호재", "랠리",
    "회복", "안정", "점프", "폭등", "사흐", "강세", "우상", "돌파",
]
NEGATIVE_WORDS = [
    "하락", "급락", "하한가", "하한", "조정", "감소", "부진", "적자", "적자전환",
    "우려", "위험", "리스크", "사상최저", "최저", "저점", "하향", "하향조정",
    "매도", "손절", "손실", "중단", "연기", "취소", "파업", "소송",
    "단 하", "약세", "폭락", "금락", "동결", "보합", "하회", "눌림",
    "과매수", "과열", "거품", "경고", "하대", "낙폭", "급감",
]


def analyze_sentiment(text):
    """규칙 기반 감성 분석: 긍정/부정 단어 카운트로 polarity 계산.
    반환: {'label': '긍정'/'부정'/'중립', 'score': -1.0 ~ 1.0, 'pos': n, 'neg': n}"""
    pos_hits = [w for w in POSITIVE_WORDS if w in text]
    neg_hits = [w for w in NEGATIVE_WORDS if w in text]
    pos = len(pos_hits)
    neg = len(neg_hits)
    total = pos + neg
    if total == 0:
        return {"label": "중립", "score": 0.0, "pos": 0, "neg": 0}
    score = (pos - neg) / total
    if score > 0.2:
        label = "긍정"
    elif score < -0.2:
        label = "부정"
    else:
        label = "중립"
    return {"label": label, "score": round(score, 2), "pos": pos, "neg": neg}


# ===== Google News RSS =====
KST = timezone(timedelta(hours=9))

def _parse_pubdate(pub_str):
    """RFC 822 형식 pubDate를 datetime.date로 파싱."""
    try:
        return datetime.datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %Z").date()
    except (ValueError, TypeError):
        try:
            # GMT 오프셋이 빠진 경우 대비
            return datetime.datetime.strptime(pub_str[:25], "%a, %d %b %Y %H:%M:%S").date()
        except Exception:
            return None

def _pubdate_to_kst_str(pub_str):
    """RFC 822 pubDate(GMT)를 KST 'YYYY-MM-DD HH:MM' 문자열로 변환."""
    try:
        dt = datetime.datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %Z")
    except (ValueError, TypeError):
        try:
            dt = datetime.datetime.strptime(pub_str[:25], "%a, %d %b %Y %H:%M:%S")
        except Exception:
            return pub_str
    # strptime이 %Z로 GMT를 파싱하면 tzinfo가 안 달릴 수 있어 명시적으로 UTC 가정
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=0)))
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def fetch_news(target_date=None):
    """Google News RSS에서 SK하이닉스 관련 뉴스를 가져온다.
    target_date(어제)가 주어지면 해당 날짜 뉴스만 필터링.
    API 키 불필요, GitHub Actions ubuntu에서 정상 동작."""
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(QUERY)}&hl=ko&gl=KR&ceid=KR:ko"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[뉴스 오류] {e}")
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"[뉴스 파싱 오류] {e}")
        return []
    items = root.findall(".//item")
    news = []
    for it in items:
        title = it.findtext("title", "") or ""
        link = it.findtext("link", "") or ""
        pub = it.findtext("pubDate", "") or ""
        desc = it.findtext("description", "") or ""
        desc = re.sub(r"<[^>]+>", "", desc)
        item_date = _parse_pubdate(pub)
        if target_date is not None and item_date is not None and item_date != target_date:
            continue
        news.append({
            "title": clean_text(title),
            "link": link,
            "pubDate": pub,
            "desc": clean_text(desc)[:200],
            "date": item_date,
        })
        if len(news) >= NEWS_COUNT:
            break
    return news


def fetch_news_with_sentiment(target_date=None):
    """뉴스 가져와서 각 기사별 감성 분석 추가."""
    news = fetch_news(target_date)
    for n in news:
        text = n["title"] + " " + n["desc"]
        n["sentiment"] = analyze_sentiment(text)
    return news


def fetch_news_with_sentiment_multi(target_dates):
    """여러 날짜(예: 금/토/일)의 뉴스를 모두 모은다. target_dates는 'YYYY-MM-DD' 문자열 집합."""
    all_news = fetch_news(None)  # 필터링 없이 전체 가져오기
    filtered = []
    for n in all_news:
        if n["date"] in target_dates:
            filtered.append(n)
    seen = {n["link"] for n in filtered}
    # 타겟 날짜 외 뉴스도 부족하면 포함(주말 뉴스가 적을 수 있음)
    if len(filtered) < 20:
        for n in all_news:
            if n["link"] not in seen:
                filtered.append(n)
                seen.add(n["link"])
    for n in filtered:
        text = n["title"] + " " + n["desc"]
        n["sentiment"] = analyze_sentiment(text)
    return filtered


# ===== 주가 데이터 (Yahoo Finance 직접 API 호출) =====
def fetch_stock(months):
    """Yahoo Finance의 chart API를 직접 호출해 일별 OHLCV 데이터를 가져온다.
    yfinance 의존성/SSL 인증서 문제를 우회하기 위해 urllib 사용."""
    end = int(datetime.datetime.now().timestamp())
    start = int((datetime.datetime.now() - datetime.timedelta(days=months * 30 + 5)).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}"
           f"?period1={start}&period2={end}&interval=1d")
    # SSL 검증 비활성화 (회사 방화벽 환경 대응)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Yahoo Finance 요청 실패: HTTP {e.code}")
    except Exception as e:
        raise RuntimeError(f"주가 데이터 조회 오류: {e}")

    result = data.get("chart", {}).get("result")
    if not result:
        raise RuntimeError("주가 데이터를 가져오지 못했습니다 (티커/네트워크 확인)")
    ts = result[0]["timestamp"]
    quote = result[0]["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(ts):
        d = datetime.datetime.utcfromtimestamp(t).date()
        rows.append({
            "Date": d,
            "Open": quote["open"][i],
            "High": quote["high"][i],
            "Low": quote["low"][i],
            "Close": quote["close"][i],
            "Volume": quote["volume"][i],
        })
    df = pd.DataFrame(rows).set_index("Date")
    df = df.dropna(subset=["Close"])
    return df


import pandas as pd  # noqa: E402




# ===== 기술 분석 =====
def analyze(df):
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    # 이동평균선
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    vol_ma20 = volume.rolling(20).mean()

    # RSI (14일)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 볼린저 밴드 (20일, 2σ)
    bb_std = close.rolling(20).std()
    bb_upper = ma20 + 2 * bb_std
    bb_lower = ma20 - 2 * bb_std
    bb_width = (bb_upper - bb_lower) / ma20 * 100

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    # ATR (14일)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    tr = pd.concat([(high - low), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr_pct = atr / close * 100

    # ADX (14일)
    plus_dm = (high.diff()).where((high.diff() > -low.diff()) & (high.diff() > 0), 0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0)
    atr_adx = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr_adx.replace(0, float('nan')))
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr_adx.replace(0, float('nan')))
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float('nan')) * 100
    adx = dx.rolling(14).mean()

    # KDJ (9, 3, 3)
    low9 = low.rolling(9).min()
    high9 = high.rolling(9).max()
    rsv = (close - low9) / (high9 - low9).replace(0, float('nan')) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d

    # 최근 가격
    cur = float(close.iloc[-1])
    cur_ma20 = float(ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else None
    cur_ma60 = float(ma60.iloc[-1]) if not pd.isna(ma60.iloc[-1]) else None
    cur_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
    cur_bb_upper = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None
    cur_bb_lower = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None
    cur_bb_width = float(bb_width.iloc[-1]) if not pd.isna(bb_width.iloc[-1]) else None
    cur_macd = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None
    cur_macd_sig = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None
    cur_macd_hist = float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else None
    cur_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    cur_atr_pct = float(atr_pct.iloc[-1]) if not pd.isna(atr_pct.iloc[-1]) else None
    cur_adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None
    cur_k = float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else None
    cur_d = float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else None
    cur_j = float(j.iloc[-1]) if not pd.isna(j.iloc[-1]) else None
    cur_vol_ratio = float(volume.iloc[-1] / vol_ma20.iloc[-1]) if not pd.isna(vol_ma20.iloc[-1]) and vol_ma20.iloc[-1] > 0 else None

    # BB 내 위치
    bb_pos = (cur - cur_bb_lower) / (cur_bb_upper - cur_bb_lower) * 100 if cur_bb_upper and cur_bb_lower and cur_bb_upper > cur_bb_lower else 50

    # 기간 내 최고/최저
    hi = float(close.max())
    lo = float(close.min())
    pos = (cur - lo) / (hi - lo) * 100 if hi > lo else 50

    return {
        "df": df, "close": close, "volume": volume,
        "ma20": ma20, "ma60": ma60, "rsi": rsi,
        "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_width": bb_width,
        "macd": macd, "macd_signal": macd_signal, "macd_hist": macd_hist,
        "atr": atr, "atr_pct": atr_pct, "adx": adx,
        "k": k, "d": d, "j": j, "vol_ma20": vol_ma20,
        "cur": cur, "cur_ma20": cur_ma20, "cur_ma60": cur_ma60, "cur_rsi": cur_rsi,
        "cur_bb_upper": cur_bb_upper, "cur_bb_lower": cur_bb_lower, "cur_bb_width": cur_bb_width,
        "bb_pos": bb_pos,
        "cur_macd": cur_macd, "cur_macd_sig": cur_macd_sig, "cur_macd_hist": cur_macd_hist,
        "cur_atr": cur_atr, "cur_atr_pct": cur_atr_pct, "cur_adx": cur_adx,
        "cur_k": cur_k, "cur_d": cur_d, "cur_j": cur_j, "cur_vol_ratio": cur_vol_ratio,
        "hi": hi, "lo": lo, "pos": pos,
    }


def signal(a, news=None):
    """규칙 기반 매수/매도 신호. +1 매수, -1 매도 가중.
    news가 주어지면 뉴스 감성 점수(평균, -1~+1) × 1.5를 점수에 반영."""
    score = 0
    reasons = []

    # 1) 골든/데드 크로스
    if a["cur_ma20"] and a["cur_ma60"]:
        if a["cur_ma20"] > a["cur_ma60"]:
            score += 1
            reasons.append("단기이평선이 장기이평선 위(골든크로스) - 상승 추세")
        else:
            score -= 1
            reasons.append("단기이평선이 장기이평선 아래(데드크로스) - 하락 추세")

    # 2) 현재가 vs MA20
    if a["cur_ma20"]:
        if a["cur"] > a["cur_ma20"]:
            score += 1
            reasons.append(f"현재가 {a['cur']:.0f}원이 MA20 {a['cur_ma20']:.0f}원 위 - 단기 강세")
        else:
            score -= 1
            reasons.append(f"현재가 {a['cur']:.0f}원이 MA20 {a['cur_ma20']:.0f}원 아래 - 단기 약세")

    # 3) RSI
    if a["cur_rsi"] is not None:
        if a["cur_rsi"] < 30:
            score += 2
            reasons.append(f"RSI {a['cur_rsi']:.1f} - 과매도 구간 (반등 가능)")
        elif a["cur_rsi"] > 70:
            score -= 2
            reasons.append(f"RSI {a['cur_rsi']:.1f} - 과매수 구간 (조정 가능)")
        else:
            reasons.append(f"RSI {a['cur_rsi']:.1f} - 중립 구간")

    # 4) 기간 내 위치
    if a["pos"] > 80:
        score -= 1
        reasons.append(f"최근 최고가 대비 {a['pos']:.0f}% 위치 - 고점 근접")
    elif a["pos"] < 20:
        score += 1
        reasons.append(f"최근 최저가 대비 {a['pos']:.0f}% 위치 - 저점 근접")

    # 5) 볼린저 밴드
    if a["bb_pos"] is not None:
        if a["bb_pos"] < 10:
            score += 2
            reasons.append(f"볼린저밴드 하단 근접 (위치 {a['bb_pos']:.0f}%) - 과매도/반등 가능")
        elif a["bb_pos"] > 90:
            score -= 2
            reasons.append(f"볼린저밴드 상단 근접 (위치 {a['bb_pos']:.0f}%) - 과매수/조정 가능")
        elif a["bb_pos"] < 20:
            score += 1
            reasons.append(f"볼린저밴드 하단 쪽 (위치 {a['bb_pos']:.0f}%) - 단기 약세")
        elif a["bb_pos"] > 80:
            score -= 1
            reasons.append(f"볼린저밴드 상단 쪽 (위치 {a['bb_pos']:.0f}%) - 단기 강세")
        else:
            reasons.append(f"볼린저밴드 중간 (위치 {a['bb_pos']:.0f}%) - 중립")

    # 6) MACD
    if a["cur_macd"] is not None and a["cur_macd_sig"] is not None:
        if a["cur_macd"] > a["cur_macd_sig"] and a["cur_macd_hist"] > 0:
            score += 1
            reasons.append(f"MACD 골든크로스 (히스토그램 {a['cur_macd_hist']:+.0f}) - 매수 신호")
        elif a["cur_macd"] < a["cur_macd_sig"] and a["cur_macd_hist"] < 0:
            score -= 1
            reasons.append(f"MACD 데드크로스 (히스토그램 {a['cur_macd_hist']:+.0f}) - 매도 신호")

    # 7) ATR
    if a["cur_atr_pct"] is not None:
        if a["cur_atr_pct"] > 5:
            reasons.append(f"ATR {a['cur_atr_pct']:.1f}% - 높은 변동성 (리스크 큼)")
        else:
            reasons.append(f"ATR {a['cur_atr_pct']:.1f}% - 낮은 변동성")

    # 8) ADX
    if a["cur_adx"] is not None:
        if a["cur_adx"] > 25:
            reasons.append(f"ADX {a['cur_adx']:.1f} - 강한 추세")
        else:
            reasons.append(f"ADX {a['cur_adx']:.1f} - 약한 추세 (횡보)")

    # 9) KDJ
    if a["cur_k"] is not None and a["cur_d"] is not None and a["cur_j"] is not None:
        reasons.append(f"K {a['cur_k']:.1f} / D {a['cur_d']:.1f} / J {a['cur_j']:.1f}")
        if a["cur_j"] < 0:
            score += 1
            reasons.append("KDJ J값 음수 - 과매도 구간")
        elif a["cur_j"] > 100:
            score -= 1
            reasons.append("KDJ J값 초과 - 과매수 구간")

    # 10) 거래량 비
    if a["cur_vol_ratio"] is not None:
        reasons.append(f"거래량비 {a['cur_vol_ratio']:.1f}x - {'평균 초과' if a['cur_vol_ratio'] > 1.5 else '평균 이하' if a['cur_vol_ratio'] < 0.5 else '평균 수준'}")

    # 11) 뉴스 감성 분석 (가중치 1.5)
    if news:
        s_scores = [n.get("sentiment", {}).get("score", 0.0) for n in news]
        if s_scores:
            avg_sent = sum(s_scores) / len(s_scores)
            news_score = round(avg_sent * 1.5)
            if news_score != 0:
                score += news_score
                sent_label = "긍정" if avg_sent > 0.2 else "부정" if avg_sent < -0.2 else "중립"
                reasons.append(f"뉴스 감성 {sent_label} (평균 {avg_sent:+.2f}, 가중 {news_score:+d}) - 감성 반영")

    if score >= 2:
        action = "BUY"
        label = "매수 추천"
    elif score <= -2:
        action = "SELL"
        label = "매도 추천"
    else:
        action = "HOLD"
        label = "관망 (보유 유지)"

    return {"action": action, "label": label, "score": score, "reasons": reasons}


# ===== HTML 렌더링 =====
def render_html(news, a, sig, months, news_label=None):
    # 차트용 데이터
    dates = [d.strftime("%Y-%m-%d") for d in a["close"].index]
    closes = [round(float(v), 0) for v in a["close"].values]
    ma20 = [None if pd.isna(v) else round(float(v), 0) for v in a["ma20"].values]
    ma60 = [None if pd.isna(v) else round(float(v), 0) for v in a["ma60"].values]
    volumes = [int(v) for v in a["volume"].values]
    bb_upper = [None if pd.isna(v) else round(float(v), 0) for v in a["bb_upper"].values]
    bb_lower = [None if pd.isna(v) else round(float(v), 0) for v in a["bb_lower"].values]
    macd_line = [None if pd.isna(v) else round(float(v), 0) for v in a["macd"].values]
    macd_sig = [None if pd.isna(v) else round(float(v), 0) for v in a["macd_signal"].values]
    macd_hist = [None if pd.isna(v) else round(float(v), 0) for v in a["macd_hist"].values]
    atr_data = [None if pd.isna(v) else round(float(v), 0) for v in a["atr"].values]
    adx_data = [None if pd.isna(v) else round(float(v), 1) for v in a["adx"].values]
    k_data = [None if pd.isna(v) else round(float(v), 1) for v in a["k"].values]
    d_data = [None if pd.isna(v) else round(float(v), 1) for v in a["d"].values]
    j_data = [None if pd.isna(v) else round(float(v), 1) for v in a["j"].values]
    vol_ma20 = [None if pd.isna(v) else int(v) for v in a["vol_ma20"].values]

    # 색상
    color_map = {"BUY": "#27ae60", "SELL": "#e74c3c", "HOLD": "#f39c12"}
    action_color = color_map[sig["action"]]

    # 뉴스 감성 분석 요약
    sentiment_colors = {"긍정": "#27ae60", "부정": "#e74c3c", "중립": "#94a3b8"}
    pos_cnt = sum(1 for n in news if n.get("sentiment", {}).get("label") == "긍정")
    neg_cnt = sum(1 for n in news if n.get("sentiment", {}).get("label") == "부정")
    neu_cnt = sum(1 for n in news if n.get("sentiment", {}).get("label") == "중립")
    total_news = len(news) or 1
    pos_pct = pos_cnt / total_news * 100
    neg_pct = neg_cnt / total_news * 100
    neu_pct = neu_cnt / total_news * 100
    # 종합 감성 (가중: 긍정 +1, 부정 -1, 중립 0)
    sent_score = (pos_cnt - neg_cnt) / total_news
    if sent_score > 0.2:
        overall_sent = "긍정"
        overall_color = "#27ae60"
    elif sent_score < -0.2:
        overall_sent = "부정"
        overall_color = "#e74c3c"
    else:
        overall_sent = "중립"
        overall_color = "#94a3b8"

    news_cards = ""
    if news:
        for i, n in enumerate(news, 1):
            s = n.get("sentiment", {"label": "중립", "score": 0.0})
            s_color = sentiment_colors.get(s["label"], "#94a3b8")
            s_score = s.get("score", 0.0)
            news_cards += f"""
        <div class="news-card">
          <div class="news-num">{i}</div>
          <div>
            <div class="news-title">{n['title']} <span class="sent-tag" style="background:{s_color}">{s['label']} ({s_score:+.1f})</span></div>
            <div class="news-meta">{_pubdate_to_kst_str(n['pubDate'])}</div>
            <div class="news-desc">{n['desc']}</div>
            <a class="news-link" href="{n['link']}" target="_blank">기사 전문 보기 →</a>
          </div>
        </div>"""
    else:
        news_cards = '<div class="empty">뉴스를 불러오지 못했습니다.</div>'

    reasons_html = "".join(f'<li>{r}</li>' for r in sig["reasons"])

    today = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    # 뉴스 라벨: 최신순 모드면 "최신 뉴스", 아니면 라벨 그대로
    news_label_display = "최신 뉴스" if (news_label is None or news_label == "최신순") else news_label
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>SK하이닉스 투자 레포트</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
         background:linear-gradient(135deg,#f8fafc 0%,#eef2f7 100%);
         color:#1e293b; padding:24px; min-height:100vh; }}
  .wrap {{ max-width:1100px; margin:0 auto; }}
  header {{ text-align:center; margin-bottom:30px; }}
  header h1 {{ font-size:1.8rem; margin-bottom:6px; color:#0f172a; }}
  header .sub {{ color:#64748b; font-size:0.95rem; }}
  .action-box {{ text-align:center; background:#ffffff; color:#1e293b;
    border:1px solid #e2e8f0; border-radius:18px; padding:24px 28px; margin-bottom:24px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04); display:flex; align-items:center; justify-content:center; gap:18px; }}
  .action-box .signal-dot {{ width:18px; height:18px; border-radius:50%; background:{action_color};
    box-shadow:0 0 0 4px {action_color}33; flex-shrink:0; }}
  .action-box .action-text {{ text-align:left; }}
  .action-box .label {{ font-size:0.85rem; color:#64748b; letter-spacing:0.02em; }}
  .action-box .action {{ font-size:1.6rem; font-weight:700; margin:2px 0; color:{action_color}; }}
  .action-box .score {{ font-size:0.85rem; color:#94a3b8; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:24px; }}
  @media (max-width:700px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  .card {{ background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
  .card h3 {{ color:#64748b; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  .price {{ font-size:2.4rem; font-weight:700; color:#2563eb; }}
  .stat {{ display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #e2e8f0; font-size:0.93rem; }}
  .stat:last-child {{ border:0; }}
  .stat .v {{ font-weight:600; color:#0f172a; }}
  .pos {{ margin-top:10px; height:8px; background:#e2e8f0; border-radius:4px; overflow:hidden; }}
  .pos div {{ height:100%; background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);
    width:{a['pos']:.0f}%; border-radius:4px; }}
  .chart-card {{ background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px;
    margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
  .chart-card h3 {{ color:#64748b; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  canvas {{ max-height:360px; }}
  .news-list {{ display:flex; flex-direction:column; gap:12px; }}
  .news-card {{ display:flex; gap:14px; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:16px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
  .news-num {{ background:#2563eb; color:white; width:28px; height:28px; border-radius:50%;
    display:flex; align-items:center; justify-content:center; font-weight:700; flex-shrink:0; }}
  .news-title {{ font-weight:600; font-size:1rem; margin-bottom:4px; color:#0f172a; }}
  .news-meta {{ color:#94a3b8; font-size:0.82rem; margin-bottom:8px; }}
  .news-desc {{ color:#475569; font-size:0.9rem; line-height:1.5; }}
  .news-link {{ color:#2563eb; font-size:0.85rem; text-decoration:none; }}
  .news-link:hover {{ text-decoration:underline; }}
  .sent-tag {{ color:white; font-size:0.72rem; padding:2px 8px; border-radius:8px;
    font-weight:600; margin-left:8px; vertical-align:middle; }}
  .sent-box {{ background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin-bottom:24px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
  .sent-box h3 {{ color:#64748b; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  .sent-summary {{ display:flex; align-items:center; gap:16px; margin-bottom:14px; }}
  .sent-overall {{ font-size:1.4rem; font-weight:700; color:{overall_color}; }}
  .sent-bar {{ flex:1; height:14px; background:#e2e8f0; border-radius:7px; overflow:hidden; display:flex; }}
  .sent-bar .spos {{ height:100%; background:#27ae60; }}
  .sent-bar .sneu {{ height:100%; background:#94a3b8; }}
  .sent-bar .sneg {{ height:100%; background:#e74c3c; }}
  .sent-legend {{ display:flex; gap:16px; font-size:0.85rem; color:#475569; }}
  .sent-legend span {{ display:inline-flex; align-items:center; gap:5px; }}
  .sent-legend .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
  .reasons {{ background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-top:18px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
  .reasons h3 {{ color:#64748b; font-size:0.9rem; margin-bottom:10px; }}
  .reasons ul {{ padding-left:20px; }}
  .reasons li {{ margin:6px 0; color:#334155; font-size:0.92rem; }}
  .empty {{ color:#94a3b8; text-align:center; padding:30px; }}
  footer {{ text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:30px; }}
  .refresh-hint {{ position:fixed; top:14px; right:14px; background:#ffffff; color:#475569;
    border:1px solid #e2e8f0; border-radius:8px; padding:8px 12px; font-size:0.75rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.08); z-index:9999; max-width:220px; line-height:1.4; }}
  .refresh-hint b {{ color:#d97706; }}
  @media (max-width:600px) {{ .refresh-hint {{ font-size:0.68rem; max-width:180px; top:8px; right:8px; }} }}
</style>
</head>
<body>
<div class="refresh-hint">이전 데이터가 보이면 <b>Ctrl+F5</b> (강제 새로고침)</div>
<div class="wrap">
  <header>
    <h1>SK하이닉스(000660) 투자 레포트</h1>
    <div class="sub">업데이트 {today} · 최근 {months}개월 데이터 · 기술 분석 + 뉴스 감성 분석</div>
  </header>

  <div class="action-box">
    <div class="signal-dot"></div>
    <div class="action-text">
      <div class="label">종합 추천</div>
      <div class="action">{sig['label']}</div>
      <div class="score">신호 점수: {sig['score']:+d} (매수≥2 / 매도≤-2 / 관망 그 외)</div>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <h3>현재 주가</h3>
      <div class="price">{a['cur']:,.0f} 원</div>
      <div class="stat"><span>기간 최고</span><span class="v">{a['hi']:,.0f} 원</span></div>
      <div class="stat"><span>기간 최저</span><span class="v">{a['lo']:,.0f} 원</span></div>
      <div class="stat"><span>현재 위치</span><span class="v">{a['pos']:.0f}%</span></div>
      <div class="pos"><div></div></div>
    </div>
    <div class="card">
      <h3>기술 지표</h3>
      <div class="stat"><span>MA20 (20일 이평선)</span><span class="v">{a['cur_ma20']:,.0f} 원</span></div>
      <div class="stat"><span>MA60 (60일 이평선)</span><span class="v">{a['cur_ma60']:,.0f} 원</span></div>
      <div class="stat"><span>RSI (14일)</span><span class="v">{a['cur_rsi']:.1f}</span></div>
      <div class="stat"><span>BB 상단 (20일, 2σ)</span><span class="v">{a['cur_bb_upper']:,.0f} 원</span></div>
      <div class="stat"><span>BB 하단 (20일, 2σ)</span><span class="v">{a['cur_bb_lower']:,.0f} 원</span></div>
      <div class="stat"><span>BB 폭 / 밴드 내 위치</span><span class="v">{a['cur_bb_width']:.1f}% / {a['bb_pos']:.0f}%</span></div>
      <div class="stat"><span>MACD / 시그널</span><span class="v">{a['cur_macd']:,.0f} / {a['cur_macd_sig']:,.0f}</span></div>
      <div class="stat"><span>MACD 히스토그램</span><span class="v">{a['cur_macd_hist']:+,.0f}</span></div>
      <div class="stat"><span>ATR (14일)</span><span class="v">{a['cur_atr']:,.0f}원 ({a['cur_atr_pct']:.1f}%)</span></div>
      <div class="stat"><span>ADX (14일)</span><span class="v">{a['cur_adx']:.1f}</span></div>
      <div class="stat"><span>KDJ</span><span class="v">K {a['cur_k']:.1f} / D {a['cur_d']:.1f} / J {a['cur_j']:.1f}</span></div>
      <div class="stat"><span>거래량비 (Vol MA20 대비)</span><span class="v">{a['cur_vol_ratio']:.1f}x</span></div>
      <div class="reasons">
        <h3>판단 근거</h3>
        <ul>{reasons_html}</ul>
      </div>
    </div>
  </div>

  <div class="chart-card">
    <h3>주가 차트 (종가 + 이동평균선 + 볼린저밴드)</h3>
    <canvas id="priceChart"></canvas>
  </div>

  <div class="chart-card">
    <h3>거래량</h3>
    <canvas id="volChart"></canvas>
  </div>

  <div class="chart-card">
    <h3>MACD (12, 26, 9)</h3>
    <canvas id="macdChart"></canvas>
  </div>

  <div class="chart-card">
    <h3>ATR (14일 변동성) & ADX (추세 강도)</h3>
    <canvas id="atrAdxChart"></canvas>
  </div>

  <div class="chart-card">
    <h3>KDJ (Stochastic Oscillator)</h3>
    <canvas id="kdjChart"></canvas>
  </div>

  <div class="chart-card">
    <h3>거래량 & 거래량 이평선 (MA20)</h3>
    <canvas id="volMaChart"></canvas>
  </div>

  <div class="sent-box">
    <h3>뉴스 감성 분석 ({news_label_display}, Top {len(news)}건)</h3>
    <div class="sent-summary">
      <div>종합 감성:</div>
      <div class="sent-overall">{overall_sent} ({sent_score:+.2f})</div>
      <div class="sent-bar">
        <div class="spos" style="width:{pos_pct:.1f}%"></div>
        <div class="sneu" style="width:{neu_pct:.1f}%"></div>
        <div class="sneg" style="width:{neg_pct:.1f}%"></div>
      </div>
    </div>
    <div class="sent-legend">
      <span><span class="dot" style="background:#27ae60"></span>긍정 {pos_cnt}건 ({pos_pct:.0f}%)</span>
      <span><span class="dot" style="background:#64748b"></span>중립 {neu_cnt}건 ({neu_pct:.0f}%)</span>
      <span><span class="dot" style="background:#e74c3c"></span>부정 {neg_cnt}건 ({neg_pct:.0f}%)</span>
    </div>
  </div>

  <h3 style="color:#94a3b8;font-size:0.9rem;text-transform:uppercase;margin:24px 0 12px;">최신 뉴스 Top {len(news)} ({news_label_display})</h3>
  <div class="news-list">{news_cards}</div>

  <footer>
    ⚠️ 본 레포트는 자동 생성된 참고용 자료이며, 실제 투자는 본인 판단으로 결정하세요.
    데이터: Yahoo Finance · Google News RSS
  </footer>
</div>

<script>
const dates = {json.dumps(dates)};
const closes = {json.dumps(closes)};
const ma20 = {json.dumps(ma20)};
const ma60 = {json.dumps(ma60)};
const volumes = {json.dumps(volumes)};
const bbUpper = {json.dumps(bb_upper)};
const bbLower = {json.dumps(bb_lower)};
const macdLine = {json.dumps(macd_line)};
const macdSignal = {json.dumps(macd_sig)};
const macdHist = {json.dumps(macd_hist)};
const atrData = {json.dumps(atr_data)};
const adxData = {json.dumps(adx_data)};
const kData = {json.dumps(k_data)};
const dData = {json.dumps(d_data)};
const jData = {json.dumps(j_data)};
const volMa20 = {json.dumps(vol_ma20)};

// ===== Canvas API 차트 그리기 =====
function initCanvas(elId) {{
  const c = document.getElementById(elId);
  c.width = c.parentElement.clientWidth - 40;
  c.height = 320;
  const ctx = c.getContext('2d');
  // 차트 전체 배경: 약간 회색톱 (라이트 테마에서 차트 영역 구분, 플롯/여백 동일 톤)
  ctx.fillStyle='#f1f5f9';
  ctx.fillRect(0,0,c.width,c.height);
  return ctx;
}}
// 차트 여백: 왼쪽(y축 라벨), 오른쪽, 위쪽, 아래쪽(x축 라벨)
// PAD_L=58 — Y축 라벨 "1,500,000" 등 7자리 숫자도 여유 확보
const PAD_L=58, PAD_R=14, PAD_T=14, PAD_B=26;
function plotW(w) {{ return w-PAD_L-PAD_R; }}
function plotH(h) {{ return h-PAD_T-PAD_B; }}
function drawLine(ctx, data, color, width, dash, w, h, min, range) {{
  if(range==0) range=1;
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.setLineDash(dash||[]);
  ctx.beginPath();
  let started=false;
  for(let i=0;i<data.length;i++) {{
    if(data[i]==null) continue;
    const x=PAD_L+(i/(data.length-1))*plotW(w);
    const y=(h-PAD_B)-(data[i]-min)/range*plotH(h);
    if(!started) {{ ctx.moveTo(x,y); started=true; }} else {{ ctx.lineTo(x,y); }}
  }}
  ctx.stroke(); ctx.setLineDash([]);
}}
function drawGrid(ctx, w, h, max, min, range, fmt) {{
  ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=0.5;
  ctx.fillStyle='#64748b'; ctx.font='10px sans-serif'; ctx.textAlign='right'; ctx.textBaseline='middle';
  for(let i=0;i<=4;i++) {{
    const y=PAD_T+(i/4)*plotH(h);
    ctx.beginPath(); ctx.moveTo(PAD_L,y); ctx.lineTo(w-PAD_R,y); ctx.stroke();
    // Y축 라벨: PAD_L-4 위치에서 우측 정렬 — 플롯 영역 침범 방지
    ctx.fillText(fmt(max-(i/4)*range), PAD_L-4, y);
  }}
  ctx.textAlign='left'; ctx.textBaseline='alphabetic';
}}
function drawXLabels(ctx, w, h) {{
  // x축 날짜 라벨 (5~6개 간격)
  ctx.fillStyle='#64748b'; ctx.font='10px sans-serif'; ctx.textAlign='center';
  const n=dates.length, step=Math.ceil(n/12);
  for(let i=0;i<n;i+=step) {{
    const x=PAD_L+(i/(n-1))*plotW(w);
    ctx.fillText(dates[i].slice(5), x, h-4);
  }}
  ctx.textAlign='left';
}}
function drawPriceChart() {{
  const ctx=initCanvas('priceChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...closes), min=Math.min(...closes), range=max-min||1;
  drawGrid(ctx,w,h,max,min,range,v=>Math.round(v).toLocaleString());
  // BB 밴드 채우기
  ctx.fillStyle='rgba(148,163,184,0.08)'; ctx.beginPath(); let s=false;
  for(let i=0;i<bbUpper.length;i++) {{ if(bbUpper[i]==null) continue; const x=PAD_L+(i/(bbUpper.length-1))*plotW(w); const y=(h-PAD_B)-(bbUpper[i]-min)/range*plotH(h); if(!s){{ctx.moveTo(x,y);s=true}}else{{ctx.lineTo(x,y)}} }}
  for(let i=bbLower.length-1;i>=0;i--) {{ if(bbLower[i]==null) continue; const x=PAD_L+(i/(bbLower.length-1))*plotW(w); const y=(h-PAD_B)-(bbLower[i]-min)/range*plotH(h); ctx.lineTo(x,y); }}
  ctx.closePath(); ctx.fill();
  drawLine(ctx,bbUpper,'rgba(148,163,184,0.4)',1,[],w,h,min,range);
  drawLine(ctx,bbLower,'rgba(148,163,184,0.4)',1,[],w,h,min,range);
  drawLine(ctx,closes,'#38bdf8',2,[],w,h,min,range);
  drawLine(ctx,ma20,'#f59e0b',1.5,[5,5],w,h,min,range);
  drawLine(ctx,ma60,'#a78bfa',1.5,[5,5],w,h,min,range);
  // 범례
  ctx.font='11px sans-serif'; let lx=w-PAD_R-160;
  ctx.fillStyle='#38bdf8'; ctx.fillRect(lx,4,12,3); ctx.fillStyle='#475569'; ctx.fillText('\uc885\uac00',lx+16,8);
  ctx.fillStyle='#f59e0b'; ctx.fillRect(lx+50,4,12,3); ctx.fillText('MA20',lx+64,8);
  ctx.fillStyle='#a78bfa'; ctx.fillRect(lx+110,4,12,3); ctx.fillText('MA60',lx+124,8);
  drawXLabels(ctx, w, h);
}}
function drawVolChart() {{
  const ctx=initCanvas('volChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...volumes);
  drawGrid(ctx,w,h,max,0,max,v=>Math.round(v/1000)+'K');
  const barW=Math.max(2,plotW(w)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) {{ const bh=(volumes[i]/max)*plotH(h); const x=PAD_L+i*plotW(w)/volumes.length+1; ctx.fillStyle='#3b82f680'; ctx.fillRect(x,(h-PAD_B)-bh,barW,bh); }}
  drawXLabels(ctx, w, h);
}}
function drawMACDChart() {{
  const ctx=initCanvas('macdChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const vals=macdLine.filter(v=>v!=null).concat(macdSignal.filter(v=>v!=null),macdHist.filter(v=>v!=null));
  const max=Math.max(...vals,0), min=Math.min(...vals,0), range=max-min||1;
  drawGrid(ctx,w,h,max,min,range,v=>Math.round(v).toLocaleString());
  // 제로 라인
  const zeroY=(h-PAD_B)-(0-min)/range*plotH(h);
  ctx.strokeStyle='#475569'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(PAD_L,zeroY); ctx.lineTo(w-PAD_R,zeroY); ctx.stroke(); ctx.setLineDash([]);
  // 히스토그램
  const barW=Math.max(2,plotW(w)/macdHist.length-2);
  for(let i=0;i<macdHist.length;i++) {{
    if(macdHist[i]==null) continue;
    const bh=Math.abs(macdHist[i]/range)*plotH(h);
    const y=macdHist[i]>=0?zeroY-bh:zeroY;
    ctx.fillStyle=macdHist[i]>=0?'rgba(39,174,96,0.6)':'rgba(231,76,60,0.6)';
    ctx.fillRect(PAD_L+i*plotW(w)/macdHist.length+1,y,barW,bh);
  }}
  drawLine(ctx,macdLine,'#38bdf8',1.5,[],w,h,min,range);
  drawLine(ctx,macdSignal,'#f59e0b',1.5,[5,5],w,h,min,range);
  drawXLabels(ctx, w, h);
}}
function drawATRADXChart() {{
  const ctx=initCanvas('atrAdxChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const atrVals=atrData.filter(v=>v!=null), adxVals=adxData.filter(v=>v!=null);
  const atrMax=Math.max(...atrVals), adxMax=Math.max(...adxVals,1);
  ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=0.5;
  ctx.font='10px sans-serif'; ctx.textBaseline='middle';
  // 좌측 Y축 (ATR) — 우측 정렬, PAD_L-4 위치
  ctx.fillStyle='#e67e22'; ctx.textAlign='right';
  for(let i=0;i<=4;i++) {{
    const y=PAD_T+(i/4)*plotH(h);
    ctx.beginPath(); ctx.moveTo(PAD_L,y); ctx.lineTo(w-PAD_R,y); ctx.stroke();
    ctx.fillText(Math.round(atrMax*(1-i/4)), PAD_L-4, y);
  }}
  // 우측 Y축 (ADX) — 좌측 정렬, w-PAD_R+4 위치
  ctx.fillStyle='#e74c3c'; ctx.textAlign='left';
  for(let i=0;i<=4;i++) {{ const y=PAD_T+(i/4)*plotH(h); ctx.fillText(Math.round(adxMax*i/4), w-PAD_R+4, y); }}
  ctx.textAlign='left'; ctx.textBaseline='alphabetic';
  const atrMin=Math.min(...atrVals), adxMin=Math.min(...adxVals,0);
  drawLine(ctx,atrData,'#e67e22',1.5,[],w,h,atrMin,atrMin==atrMax?1:atrMax-atrMin);
  drawLine(ctx,adxData,'#e74c3c',1.5,[],w,h,adxMin,adxMin==adxMax?1:adxMax-adxMin);
  drawXLabels(ctx, w, h);
}}
function drawKDJChart() {{
  const ctx=initCanvas('kdjChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  ctx.strokeStyle='#cbd5e1'; ctx.lineWidth=0.5;
  ctx.fillStyle='#64748b'; ctx.font='10px sans-serif'; ctx.textAlign='right'; ctx.textBaseline='middle';
  for(let i=0;i<[0,25,50,75,100].length;i++) {{
    const v=[0,25,50,75,100][i], y=(h-PAD_B)-(v/100)*plotH(h);
    ctx.beginPath(); ctx.moveTo(PAD_L,y); ctx.lineTo(w-PAD_R,y); ctx.stroke();
    ctx.fillText(v+'', PAD_L-4, y);
  }}
  ctx.textAlign='left'; ctx.textBaseline='alphabetic';
  drawLine(ctx,kData,'#38bdf8',1.5,[],w,h,0,100);
  drawLine(ctx,dData,'#f59e0b',1.5,[],w,h,0,100);
  drawLine(ctx,jData,'#a78bfa',1.5,[],w,h,0,100);
  drawXLabels(ctx, w, h);
}}
function drawVolMaChart() {{
  const ctx=initCanvas('volMaChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...volumes,...volMa20.filter(v=>v!=null));
  drawGrid(ctx,w,h,max,0,max,v=>Math.round(v/1000)+'K');
  const barW=Math.max(2,plotW(w)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) {{ const bh=(volumes[i]/max)*plotH(h); const x=PAD_L+i*plotW(w)/volumes.length+1; ctx.fillStyle='#3b82f680'; ctx.fillRect(x,(h-PAD_B)-bh,barW,bh); }}
  drawLine(ctx,volMa20,'#f59e0b',1.5,[5,5],w,h,0,max);
  drawXLabels(ctx, w, h);
}}
function drawAll() {{ drawPriceChart(); drawVolChart(); drawMACDChart(); drawATRADXChart(); drawKDJChart(); drawVolMaChart(); }}
window.addEventListener('load', drawAll);
window.addEventListener('resize', drawAll);
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="SK하이닉스 투자 레포트 생성")
    parser.add_argument("--months", type=int, default=3, help="분석 기간 (개월, 기본 3)")
    args = parser.parse_args()

    # 최신 뉴스 모드: 날짜 필터링 없이 Google News RSS 순서(최신순)로 상위 N건 가져오기
    print(f"[1/4] Google News 뉴스 검색: {QUERY} (최신순 상위 {NEWS_COUNT}건)")
    news = fetch_news_with_sentiment()  # target_date=None → 필터링 없이 최신순
    print(f"  → 총 {len(news)}건")

    print(f"[2/4] Yahoo Finance 주가 데이터: {TICKER} (최근 {args.months}개월)")
    df = fetch_stock(args.months)
    print(f"  → {len(df)}일 데이터")

    print("[3/4] 기술 분석 계산")
    a = analyze(df)
    sig = signal(a, news)
    print(f"  → 추천: {sig['label']} (점수 {sig['score']:+d})")

    print("[4/4] HTML 레포트 생성")
    html = render_html(news, a, sig, args.months, news_label="최신순")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {out_path}")

    # 요약 출력
    print("\n" + "=" * 50)
    print(f"추천: {sig['label']}  (점수 {sig['score']:+d})")
    print(f"현재가: {a['cur']:,.0f}원  RSI: {a['cur_rsi']:.1f}")
    if news:
        pos = sum(1 for n in news if n["sentiment"]["label"] == "긍정")
        neg = sum(1 for n in news if n["sentiment"]["label"] == "부정")
        neu = sum(1 for n in news if n["sentiment"]["label"] == "중립")
        print(f"뉴스 감성: 긍정 {pos} / 중립 {neu} / 부정 {neg} (총 {len(news)}건)")
    print("=" * 50)
    print(f"\n레포트 파일: {out_path}")


if __name__ == "__main__":
    main()
