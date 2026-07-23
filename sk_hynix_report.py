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


def signal(a):
    """규칙 기반 매수/매도 신호. +1 매수, -1 매도 가중."""
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
def render_html(news, a, sig, months):
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
            <div class="news-meta">{n['pubDate']}</div>
            <div class="news-desc">{n['desc']}</div>
            <a class="news-link" href="{n['link']}" target="_blank">기사 전문 보기 →</a>
          </div>
        </div>"""
    else:
        news_cards = '<div class="empty">뉴스를 불러오지 못했습니다.</div>'

    reasons_html = "".join(f'<li>{r}</li>' for r in sig["reasons"])

    today = datetime.date.today().strftime("%Y-%m-%d")
    # 어제 날짜 (뉴스 기준일 표시용)
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SK하이닉스 투자 레포트</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
         background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
         color:#e2e8f0; padding:24px; min-height:100vh; }}
  .wrap {{ max-width:1100px; margin:0 auto; }}
  header {{ text-align:center; margin-bottom:30px; }}
  header h1 {{ font-size:1.8rem; margin-bottom:6px; }}
  header .sub {{ color:#94a3b8; font-size:0.95rem; }}
  .action-box {{ text-align:center; background:{action_color}; color:white;
    border-radius:18px; padding:28px; margin-bottom:24px; box-shadow:0 10px 40px rgba(0,0,0,0.3); }}
  .action-box .label {{ font-size:1.1rem; opacity:0.9; }}
  .action-box .action {{ font-size:3rem; font-weight:800; margin:8px 0; }}
  .action-box .score {{ font-size:0.95rem; opacity:0.9; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:24px; }}
  @media (max-width:700px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  .card {{ background:#1e293b; border-radius:14px; padding:20px; }}
  .card h3 {{ color:#94a3b8; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  .price {{ font-size:2.4rem; font-weight:700; color:#38bdf8; }}
  .stat {{ display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #334155; font-size:0.93rem; }}
  .stat:last-child {{ border:0; }}
  .stat .v {{ font-weight:600; color:#f1f5f9; }}
  .pos {{ margin-top:10px; height:8px; background:#334155; border-radius:4px; overflow:hidden; }}
  .pos div {{ height:100%; background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);
    width:{a['pos']:.0f}%; border-radius:4px; }}
  .chart-card {{ background:#1e293b; border-radius:14px; padding:20px; margin-bottom:24px; }}
  .chart-card h3 {{ color:#94a3b8; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  canvas {{ max-height:360px; }}
  .news-list {{ display:flex; flex-direction:column; gap:12px; }}
  .news-card {{ display:flex; gap:14px; background:#1e293b; border-radius:12px; padding:16px; }}
  .news-num {{ background:#3b82f6; color:white; width:28px; height:28px; border-radius:50%;
    display:flex; align-items:center; justify-content:center; font-weight:700; flex-shrink:0; }}
  .news-title {{ font-weight:600; font-size:1rem; margin-bottom:4px; }}
  .news-meta {{ color:#64748b; font-size:0.82rem; margin-bottom:8px; }}
  .news-desc {{ color:#cbd5e1; font-size:0.9rem; line-height:1.5; }}
  .news-link {{ color:#3b82f6; font-size:0.85rem; text-decoration:none; }}
  .news-link:hover {{ text-decoration:underline; }}
  .sent-tag {{ color:white; font-size:0.72rem; padding:2px 8px; border-radius:8px;
    font-weight:600; margin-left:8px; vertical-align:middle; }}
  .sent-box {{ background:#1e293b; border-radius:14px; padding:20px; margin-bottom:24px; }}
  .sent-box h3 {{ color:#94a3b8; font-size:0.9rem; text-transform:uppercase; margin-bottom:14px; }}
  .sent-summary {{ display:flex; align-items:center; gap:16px; margin-bottom:14px; }}
  .sent-overall {{ font-size:1.4rem; font-weight:700; color:{overall_color}; }}
  .sent-bar {{ flex:1; height:14px; background:#334155; border-radius:7px; overflow:hidden; display:flex; }}
  .sent-bar .pos {{ height:100%; background:#27ae60; }}
  .sent-bar .neu {{ height:100%; background:#64748b; }}
  .sent-bar .neg {{ height:100%; background:#e74c3c; }}
  .sent-legend {{ display:flex; gap:16px; font-size:0.85rem; color:#cbd5e1; }}
  .sent-legend span {{ display:inline-flex; align-items:center; gap:5px; }}
  .sent-legend .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
  .reasons {{ background:#1e293b; border-radius:12px; padding:18px; margin-top:18px; }}
  .reasons h3 {{ color:#94a3b8; font-size:0.9rem; margin-bottom:10px; }}
  .reasons ul {{ padding-left:20px; }}
  .reasons li {{ margin:6px 0; color:#cbd5e1; font-size:0.92rem; }}
  .empty {{ color:#64748b; text-align:center; padding:30px; }}
  footer {{ text-align:center; color:#475569; font-size:0.8rem; margin-top:30px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>SK하이닉스(000660) 투자 레포트</h1>
    <div class="sub">기준일 {today} · 최근 {months}개월 데이터 · 기술 분석 + 뉴스 감성 분석</div>
  </header>

  <div class="action-box">
    <div class="label">종합 추천</div>
    <div class="action">{sig['label']}</div>
    <div class="score">신호 점수: {sig['score']:+d} (매수≥2 / 매도≤-2 / 관망 그 외)</div>
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
    <h3>뉴스 감성 분석 ({yesterday} 기준, Top {len(news)}건)</h3>
    <div class="sent-summary">
      <div>종합 감성:</div>
      <div class="sent-overall">{overall_sent} ({sent_score:+.2f})</div>
      <div class="sent-bar">
        <div class="pos" style="width:{pos_pct:.1f}%"></div>
        <div class="neu" style="width:{neu_pct:.1f}%"></div>
        <div class="neg" style="width:{neg_pct:.1f}%"></div>
      </div>
    </div>
    <div class="sent-legend">
      <span><span class="dot" style="background:#27ae60"></span>긍정 {pos_cnt}건 ({pos_pct:.0f}%)</span>
      <span><span class="dot" style="background:#64748b"></span>중립 {neu_cnt}건 ({neu_pct:.0f}%)</span>
      <span><span class="dot" style="background:#e74c3c"></span>부정 {neg_cnt}건 ({neg_pct:.0f}%)</span>
    </div>
  </div>

  <h3 style="color:#94a3b8;font-size:0.9rem;text-transform:uppercase;margin:24px 0 12px;">최신 뉴스 Top {len(news)} ({yesterday})</h3>
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
  c.height = 300;
  return c.getContext('2d');
}}
function drawLine(ctx, data, color, width, dash, w, h, min, range) {{
  if(range==0) range=1;
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.setLineDash(dash||[]);
  ctx.beginPath();
  let started=false;
  for(let i=0;i<data.length;i++) {{
    if(data[i]==null) continue;
    const x=10+(i/(data.length-1))*(w-20);
    const y=h-10-(data[i]-min)/range*(h-20);
    if(!started) {{ ctx.moveTo(x,y); started=true; }} else {{ ctx.lineTo(x,y); }}
  }}
  ctx.stroke(); ctx.setLineDash([]);
}}
function drawGrid(ctx, w, h, max, min, range, fmt) {{
  ctx.strokeStyle='#334155'; ctx.lineWidth=0.5;
  for(let i=0;i<=4;i++) {{
    const y=10+(i/4)*(h-20);
    ctx.beginPath(); ctx.moveTo(10,y); ctx.lineTo(w-10,y); ctx.stroke();
    ctx.fillStyle='#64748b'; ctx.font='10px sans-serif';
    ctx.fillText(fmt(max-(i/4)*range), 2, y-2);
  }}
}}
function drawPriceChart() {{
  const ctx=initCanvas('priceChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...closes), min=Math.min(...closes), range=max-min||1;
  drawGrid(ctx,w,h,max,min,range,v=>Math.round(v).toLocaleString());
  // BB 밴드 채우기
  ctx.fillStyle='rgba(148,163,184,0.08)'; ctx.beginPath(); let s=false;
  for(let i=0;i<bbUpper.length;i++) {{ if(bbUpper[i]==null) continue; const x=10+(i/(bbUpper.length-1))*(w-20); const y=h-10-(bbUpper[i]-min)/range*(h-20); if(!s){{ctx.moveTo(x,y);s=true}}else{{ctx.lineTo(x,y)}} }}
  for(let i=bbLower.length-1;i>=0;i--) {{ if(bbLower[i]==null) continue; const x=10+(i/(bbLower.length-1))*(w-20); const y=h-10-(bbLower[i]-min)/range*(h-20); ctx.lineTo(x,y); }}
  ctx.closePath(); ctx.fill();
  drawLine(ctx,bbUpper,'rgba(148,163,184,0.4)',1,[],w,h,min,range);
  drawLine(ctx,bbLower,'rgba(148,163,184,0.4)',1,[],w,h,min,range);
  drawLine(ctx,closes,'#38bdf8',2,[],w,h,min,range);
  drawLine(ctx,ma20,'#f59e0b',1.5,[5,5],w,h,min,range);
  drawLine(ctx,ma60,'#a78bfa',1.5,[5,5],w,h,min,range);
  // 범례
  ctx.font='11px sans-serif'; let lx=w-160;
  ctx.fillStyle='#38bdf8'; ctx.fillRect(lx,4,12,3); ctx.fillStyle='#e2e8f0'; ctx.fillText('\uc885\uac00',lx+16,8);
  ctx.fillStyle='#f59e0b'; ctx.fillRect(lx+50,4,12,3); ctx.fillText('MA20',lx+64,8);
  ctx.fillStyle='#a78bfa'; ctx.fillRect(lx+110,4,12,3); ctx.fillText('MA60',lx+124,8);
}}
function drawVolChart() {{
  const ctx=initCanvas('volChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...volumes);
  drawGrid(ctx,w,h,max,0,max,v=>Math.round(v/1000)+'K');
  const barW=Math.max(2,(w-20)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) {{ const bh=(volumes[i]/max)*(h-20); const x=10+i*(w-20)/volumes.length+1; ctx.fillStyle='#3b82f680'; ctx.fillRect(x,h-10-bh,barW,bh); }}
}}
function drawMACDChart() {{
  const ctx=initCanvas('macdChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const vals=macdLine.filter(v=>v!=null).concat(macdSignal.filter(v=>v!=null),macdHist.filter(v=>v!=null));
  const max=Math.max(...vals,0), min=Math.min(...vals,0), range=max-min||1;
  drawGrid(ctx,w,h,max,min,range,v=>Math.round(v).toLocaleString());
  // 제로 라인
  const zeroY=h-10-(0-min)/range*(h-20);
  ctx.strokeStyle='#475569'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(10,zeroY); ctx.lineTo(w-10,zeroY); ctx.stroke(); ctx.setLineDash([]);
  // 히스토그램
  const barW=Math.max(2,(w-20)/macdHist.length-2);
  for(let i=0;i<macdHist.length;i++) {{
    if(macdHist[i]==null) continue;
    const bh=Math.abs(macdHist[i]/range)*(h-20);
    const y=macdHist[i]>=0?zeroY-bh:zeroY;
    ctx.fillStyle=macdHist[i]>=0?'rgba(39,174,96,0.6)':'rgba(231,76,60,0.6)';
    ctx.fillRect(10+i*(w-20)/macdHist.length+1,y,barW,bh);
  }}
  drawLine(ctx,macdLine,'#38bdf8',1.5,[],w,h,min,range);
  drawLine(ctx,macdSignal,'#f59e0b',1.5,[5,5],w,h,min,range);
}}
function drawATRADXChart() {{
  const ctx=initCanvas('atrAdxChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const atrVals=atrData.filter(v=>v!=null), adxVals=adxData.filter(v=>v!=null);
  const atrMax=Math.max(...atrVals), adxMax=Math.max(...adxVals,1);
  ctx.strokeStyle='#334155'; ctx.lineWidth=0.5;
  for(let i=0;i<=4;i++) {{
    const y=10+(i/4)*(h-20);
    ctx.beginPath(); ctx.moveTo(10,y); ctx.lineTo(w-10,y); ctx.stroke();
    ctx.fillStyle='#e67e22'; ctx.font='10px sans-serif'; ctx.fillText(Math.round(atrMax*(1-i/4)),2,y-2);
  }}
  ctx.fillStyle='#e74c3c'; ctx.textAlign='right';
  for(let i=0;i<=4;i++) {{ const y=10+(i/4)*(h-20); ctx.fillText(Math.round(adxMax*i/4),w-2,y-2); }}
  ctx.textAlign='left';
  const atrMin=Math.min(...atrVals), adxMin=Math.min(...adxVals,0);
  drawLine(ctx,atrData,'#e67e22',1.5,[],w,h,atrMin,atrMin==atrMax?1:atrMax-atrMin);
  drawLine(ctx,adxData,'#e74c3c',1.5,[],w,h,adxMin,adxMin==adxMax?1:adxMax-adxMin);
}}
function drawKDJChart() {{
  const ctx=initCanvas('kdjChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  ctx.strokeStyle='#334155'; ctx.lineWidth=0.5;
  for(let i=0;i<[0,25,50,75,100].length;i++) {{
    const v=[0,25,50,75,100][i], y=h-10-(v/100)*(h-20);
    ctx.beginPath(); ctx.moveTo(10,y); ctx.lineTo(w-10,y); ctx.stroke();
    ctx.fillStyle='#64748b'; ctx.font='10px sans-serif'; ctx.fillText(v+'',2,y-2);
  }}
  drawLine(ctx,kData,'#38bdf8',1.5,[],w,h,0,100);
  drawLine(ctx,dData,'#f59e0b',1.5,[],w,h,0,100);
  drawLine(ctx,jData,'#a78bfa',1.5,[],w,h,0,100);
}}
function drawVolMaChart() {{
  const ctx=initCanvas('volMaChart'), w=ctx.canvas.width, h=ctx.canvas.height;
  const max=Math.max(...volumes,...volMa20.filter(v=>v!=null));
  drawGrid(ctx,w,h,max,0,max,v=>Math.round(v/1000)+'K');
  const barW=Math.max(2,(w-20)/volumes.length-2);
  for(let i=0;i<volumes.length;i++) {{ const bh=(volumes[i]/max)*(h-20); const x=10+i*(w-20)/volumes.length+1; ctx.fillStyle='#3b82f680'; ctx.fillRect(x,h-10-bh,barW,bh); }}
  drawLine(ctx,volMa20,'#f59e0b',1.5,[5,5],w,h,0,max);
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

    # 어제 날짜 (KST 기준). 매일 아침 09:00 실행이므로 전일 뉴스를 필터링.
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    # 주말(토/일)인 경우 금요일로 보정
    if yesterday.weekday() == 5:  # 토요일
        yesterday = yesterday - datetime.timedelta(days=1)
    elif yesterday.weekday() == 6:  # 일요일
        yesterday = yesterday - datetime.timedelta(days=2)

    print(f"[1/4] Google News 뉴스 검색: {QUERY} (기준일 {yesterday})")
    news = fetch_news_with_sentiment(yesterday)
    # 어제 뉴스가 부족하면 최신 뉴스로 보완
    if len(news) < NEWS_COUNT:
        print(f"  → {len(news)}건 (부족). 최신 뉴스로 보완.")
        extra = fetch_news_with_sentiment()
        seen = {n["link"] for n in news}
        for n in extra:
            if n["link"] not in seen:
                news.append(n)
                if len(news) >= NEWS_COUNT:
                    break
    print(f"  → 총 {len(news)}건")

    print(f"[2/4] Yahoo Finance 주가 데이터: {TICKER} (최근 {args.months}개월)")
    df = fetch_stock(args.months)
    print(f"  → {len(df)}일 데이터")

    print("[3/4] 기술 분석 계산")
    a = analyze(df)
    sig = signal(a)
    print(f"  → 추천: {sig['label']} (점수 {sig['score']:+d})")

    print("[4/4] HTML 레포트 생성")
    html = render_html(news, a, sig, args.months)
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
