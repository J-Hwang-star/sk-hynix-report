"""SK 하이닉스 투자 레포트 생성기

네이버 뉴스 + Yahoo Finance 주가 데이터를 결합해
기술 분석 기반 매수/매도 추천 HTML 레포트를 생성한다.

사용법:
    python sk_hynix_report.py              # 기본: 최근 3개월
    python sk_hynix_report.py --months 6   # 6개월 데이터

준비:
    네이버 API 키 필요 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)
    - naver_news_sk_hynix.py 참고
    - yfinance 는 자동 설치됨 (pip install yfinance)
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


# ===== 설정 =====
TICKER = "000660.KS"          # SK 하이닉스 (Yahoo Finance 심볼)
QUERY = "SK 하이닉스"
NEWS_COUNT = 5

# .env 로드 (네이버 키)
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value

load_env_file()
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")


def clean_text(s):
    return (
        s.replace("&quot;", '"').replace("&#39;", "'")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    )


# ===== 네이버 뉴스 =====
def fetch_news():
    # 1) 네이버 API 키가 있으면 공식 API 사용
    if CLIENT_ID and CLIENT_SECRET:
        url = "https://openapi.naver.com/v1/search/news.json"
        params = urllib.parse.urlencode(
            {"query": QUERY, "display": NEWS_COUNT, "start": 1, "sort": "date"}
        )
        req = urllib.request.Request(f"{url}?{params}")
        req.add_header("X-Naver-Client-Id", CLIENT_ID)
        req.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [
                {
                    "title": clean_text(it.get("title", "")),
                    "link": it.get("link", ""),
                    "pubDate": it.get("pubDate", ""),
                    "desc": clean_text(it.get("description", "")),
                }
                for it in data.get("items", [])
            ]
        except Exception as e:
            print(f"[뉴스 API 오류] {e} - RSS로 폴백")

    # 2) API 키가 없거나 실패 시 네이버 뉴스 RSS 사용 (키 불필요)
    return fetch_news_rss()


def fetch_news_rss():
    """Google News RSS에서 Top N을 파싱한다. API 키 불필요.
    네이버 뉴스 RSS는 GitHub Actions 우분투에서 DNS가 막히는 문제가 있어
    Google News RSS로 대체한다. SK하이닉스 관련 한국어 뉴스를 가져온다."""
    import xml.etree.ElementTree as ET
    import ssl
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(QUERY)
        + "&hl=ko&gl=KR&ceid=KR:ko"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[뉴스 RSS 오류] {e}")
        return []

    items = []
    try:
        root = ET.fromstring(xml_data)
        for it in root.findall(".//item")[:NEWS_COUNT]:
            title = clean_text(it.findtext("title", default=""))
            # Google News는 title 끝에 " - 언론사명" 이 붙음 - 분리
            source = ""
            if " - " in title:
                title, source = title.rsplit(" - ", 1)
            pub = it.findtext("pubDate", default="")
            # 날짜 간단히 포맷
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub)
                pub = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
            items.append({
                "title": title,
                "link": it.findtext("link", default=""),
                "pubDate": pub,
                "desc": f"출처: {source}" if source else "",
            })
    except Exception as e:
        print(f"[뉴스 RSS 파싱 오류] {e}")
    return items


# ===== 주가 데이터 (Yahoo Finance 직접 API 호출) =====
def fetch_stock(months):
    """Yahoo Finance의 chart API를 직접 호출해 일별 OHLCV 데이터를 가져온다.
    yfinance 의존성/SSL 인증서 문제를 우회하기 위해 urllib 사용."""
    import ssl
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

    # RSI (14일)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 볼린저 밴드 (20일, 표준편차 2배)
    std20 = close.rolling(20).std()
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20
    bb_width = (bb_upper - bb_lower) / ma20 * 100  # 밴드 폭(%)

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    # 최근 가격
    cur = float(close.iloc[-1])
    cur_ma20 = float(ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else None
    cur_ma60 = float(ma60.iloc[-1]) if not pd.isna(ma60.iloc[-1]) else None
    cur_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
    cur_bb_upper = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None
    cur_bb_lower = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None
    cur_bb_width = float(bb_width.iloc[-1]) if not pd.isna(bb_width.iloc[-1]) else None
    # 현재가의 밴드 내 위치 (0=하단, 100=상단)
    if cur_bb_upper and cur_bb_lower and cur_bb_upper > cur_bb_lower:
        bb_pos = (cur - cur_bb_lower) / (cur_bb_upper - cur_bb_lower) * 100
    else:
        bb_pos = 50
    cur_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None
    cur_macd_sig = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None
    cur_macd_hist = float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else None
    # MACD 히스토그램 추세 (최근 3일)
    macd_hist_trend = 0
    if len(macd_hist) >= 3 and not pd.isna(macd_hist.iloc[-1]) and not pd.isna(macd_hist.iloc[-3]):
        macd_hist_trend = float(macd_hist.iloc[-1]) - float(macd_hist.iloc[-3])

    # ATR (Average True Range, 14일)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    cur_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    atr_pct = (cur_atr / cur * 100) if cur_atr and cur else None

    # ADX (Average Directional Index, 14일)
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    rtr = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / rtr)
    minus_di = 100 * (minus_dm.rolling(14).mean() / rtr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(14).mean()
    cur_adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None

    # 거래량 이평선 (Vol MA20)
    vol_ma20 = volume.rolling(20).mean()
    cur_vol_ma20 = float(vol_ma20.iloc[-1]) if not pd.isna(vol_ma20.iloc[-1]) else None
    vol_ratio = (volume.iloc[-1] / cur_vol_ma20) if cur_vol_ma20 and cur_vol_ma20 > 0 else 1.0

    # KDJ (Stochastic Indicator, 14일)
    low_14 = low.rolling(14).min()
    high_14 = high.rolling(14).max()
    k_pct = 100 * (cur - low_14) / (high_14 - low_14) if (high_14.iloc[-1] - low_14.iloc[-1]) > 0 else 50
    d_k = k_pct.rolling(3).mean()
    j_val = 3 * k_pct - 2 * d_k
    cur_k = float(k_pct.iloc[-1]) if not pd.isna(k_pct.iloc[-1]) else 50
    cur_d = float(d_k.iloc[-1]) if not pd.isna(d_k.iloc[-1]) else 50
    cur_j = float(j_val.iloc[-1]) if not pd.isna(j_val.iloc[-1]) else 50

    # 기간 내 최고/최저
    hi = float(close.max())
    lo = float(close.min())
    pos = (cur - lo) / (hi - lo) * 100 if hi > lo else 50

    return {
        "df": df, "close": close, "volume": volume,
        "ma20": ma20, "ma60": ma60, "rsi": rsi,
        "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_width": bb_width,
        "macd": macd_line, "macd_signal": macd_signal, "macd_hist": macd_hist,
        "tr": tr, "adx": adx, "k_pct": k_pct, "d_k": d_k, "j_val": j_val,
        "vol_ma20": vol_ma20,
        "cur": cur, "cur_ma20": cur_ma20, "cur_ma60": cur_ma60, "cur_rsi": cur_rsi,
        "cur_bb_upper": cur_bb_upper, "cur_bb_lower": cur_bb_lower,
        "cur_bb_width": cur_bb_width, "bb_pos": bb_pos,
        "cur_macd": cur_macd, "cur_macd_sig": cur_macd_sig,
        "cur_macd_hist": cur_macd_hist, "macd_hist_trend": macd_hist_trend,
        "cur_atr": cur_atr, "atr_pct": atr_pct,
        "cur_adx": cur_adx,
        "cur_vol_ma20": cur_vol_ma20, "vol_ratio": vol_ratio,
        "cur_k": cur_k, "cur_d": cur_d, "cur_j": cur_j,
        "hi": hi, "lo": lo, "pos": pos,
    }


def signal(a, sent=None):
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
    if a["cur_bb_upper"] and a["cur_bb_lower"]:
        bbp = a["bb_pos"]
        if bbp < 10:
            score += 2
            reasons.append(f"볼린저밴드 하단 접근 (위치 {bbp:.0f}%) - 과매수/반등 가능")
        elif bbp > 90:
            score -= 2
            reasons.append(f"볼린저밴드 상단 접근 (위치 {bbp:.0f}%) - 과매수/조정 가능")
        elif bbp < 20:
            score += 1
            reasons.append(f"볼린저밴드 하단 근접 (위치 {bbp:.0f}%) - 단기 약세")
        elif bbp > 80:
            score -= 1
            reasons.append(f"볼린저밴드 상단 근접 (위치 {bbp:.0f}%) - 단기 강세")
        else:
            reasons.append(f"볼린저밴드 중간 구간 (위치 {bbp:.0f}%) - 밴드 내 정상")
        # 밴드 폭 (변동성)
        if a["cur_bb_width"] is not None:
            if a["cur_bb_width"] < 5:
                reasons.append(f"밴드 폭 {a['cur_bb_width']:.1f}% - 변동성 축소 (큰 움직임 임박)")
            elif a["cur_bb_width"] > 20:
                reasons.append(f"밴드 폭 {a['cur_bb_width']:.1f}% - 변동성 확대")

    # 6) MACD
    if a["cur_macd"] is not None and a["cur_macd_sig"] is not None:
        if a["cur_macd"] > a["cur_macd_sig"] and a["cur_macd_hist"] > 0:
            # 골든크로스 (MACD가 시그널 위로)
            prev_hist = a.get("macd_hist_trend", 0)
            if prev_hist < 0:
                score += 2
                reasons.append(f"MACD 골든크로스 발생 (히스토그램 {a['cur_macd_hist']:+.1f}) - 강한 매수 신호")
            else:
                score += 1
                reasons.append(f"MACD 시그널 상향 (히스토그램 {a['cur_macd_hist']:+.1f}) - 상승 모멘텀")
        elif a["cur_macd"] < a["cur_macd_sig"] and a["cur_macd_hist"] < 0:
            prev_hist = a.get("macd_hist_trend", 0)
            if prev_hist > 0:
                score -= 2
                reasons.append(f"MACD 데드크로스 발생 (히스토그램 {a['cur_macd_hist']:+.1f}) - 강한 매도 신호")
            else:
                score -= 1
                reasons.append(f"MACD 시그널 하향 (히스토그램 {a['cur_macd_hist']:+.1f}) - 하락 모멘텀")
        else:
            reasons.append(f"MACD 중립 (히스토그램 {a['cur_macd_hist']:+.1f}) - 모멘텀 약화")

    # 7) ATR (변동성)
    if a["atr_pct"] is not None:
        if a["atr_pct"] > 5:
            reasons.append(f"ATR {a['atr_pct']:.1f}% - 높은 변동성 (리스크 큼)")
        elif a["atr_pct"] < 2:
            reasons.append(f"ATR {a['atr_pct']:.1f}% - 낮은 변동성 (안정적)")
        else:
            reasons.append(f"ATR {a['atr_pct']:.1f}% - 적정 변동성")

    # 8) ADX (추세 강도)
    if a["cur_adx"] is not None:
        if a["cur_adx"] > 50:
            score += 1
            reasons.append(f"ADX {a['cur_adx']:.1f} - 강한 추세장 (트렌드 추종 유리)")
        elif a["cur_adx"] > 25:
            reasons.append(f"ADX {a['cur_adx']:.1f} - 보통 추세 강도")
        elif a["cur_adx"] > 10:
            reasons.append(f"ADX {a['cur_adx']:.1f} - 약한 추세장 (횡보)")
        else:
            reasons.append(f"ADX {a['cur_adx']:.1f} - 매우 약한 추세 (매수 신호 약함)")

    # 9) KDJ (Stochastic)
    if a["cur_k"] is not None and a["cur_j"] is not None:
        if a["cur_j"] < 0:
            score += 1
            reasons.append(f"J값 {a['cur_j']:.1f} - 과매도 권역 (반등 가능성)")
        elif a["cur_j"] > 100:
            score -= 1
            reasons.append(f"J값 {a['cur_j']:.1f} - 과매수 권역 (조정 가능성)")
        else:
            reasons.append(f"K {a['cur_k']:.1f} / D {a['cur_d']:.1f} / J {a['cur_j']:.1f} - 중립 권역")

    # 10) 거래량비 (Vol MA20 대비)
    if a["vol_ratio"] is not None:
        if a["vol_ratio"] > 2.0:
            reasons.append(f"거래량비 {a['vol_ratio']:.1f}x - 급증 거래량 (움직임 주목)")
        elif a["vol_ratio"] > 1.2:
            reasons.append(f"거래량비 {a['vol_ratio']:.1f}x - 평균 이상 거래량")
        else:
            reasons.append(f"거래량비 {a['vol_ratio']:.1f}x - 평균 이하 거래량")

    # 11) 뉴스 감성 분석
    if sent:
        s = sent["score"]
        if s >= 2:
            score += 2
            reasons.append(f"뉴스 감성 {s:+d} (긍정 {sent['pos']}건/부정 {sent['neg']}건) - 강한 긍정")
        elif s == 1:
            score += 1
            reasons.append(f"뉴스 감성 {s:+d} (긍정 {sent['pos']}건/부정 {sent['neg']}건) - 긍정 우세")
        elif s <= -2:
            score -= 2
            reasons.append(f"뉴스 감성 {s:+d} (긍정 {sent['pos']}건/부정 {sent['neg']}건) - 강한 부정")
        elif s == -1:
            score -= 1
            reasons.append(f"뉴스 감성 {s:+d} (긍정 {sent['pos']}건/부정 {sent['neg']}건) - 부정 우세")
        else:
            reasons.append(f"뉴스 감성 {s:+d} (긍정 {sent['pos']}건/부정 {sent['neg']}건) - 중립")

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


# ===== 뉴스 감성 분석 =====
# 긍정/부정 키워드 사전 (한국어 주식/반도체 관련)
POSITIVE_WORDS = [
    "상승", "급등", "오름", "긍정", "호조", "신고가", "최고", "최대", "증가",
    "성장", "개선", "회복", "수익", "이익", "흑자", "실적", "개혁", "기대",
    "혁신", "돌파", "강세", "상향", "목표가", "매수", "추천", "대량", "수주",
    "계약", "투자", "확대", "점유율", "증산", "협력", "성공", "완성", "안정",
    "개막", "기대감", "반등", "급상승", "사상최고", "사상 최고", "사줘",
]
NEGATIVE_WORDS = [
    "하락", "급락", "내림", "부정", "적자", "감소", "부진", "우려", "리스크",
    "하향", "손실", "위기", "충격", "약세", "폭락", "급감", "하회", "미달",
    "지연", "연기", "취소", "중단", "중지", "문제", "사고", "소송", "벌금",
    "제재", "조사", "악화", "하락세", "약화", "취약", "경고", "하향조정",
    "목표가 하향", "손실", "적전", "글로벌", "공급과잉", "재고",
]


def classify_sentiment(text):
    """텍스트에서 긍정/부정 키워드를 세어 감성 점수 반환.
    +1 (긍정), -1 (부정), 0 (중립)."""
    if not text:
        return 0
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def analyze_sentiment(news):
    """뉴스 전체 감성 분석. 각 항목에 sentiment 추가하고 종합 점수 반환."""
    total_pos = 0
    total_neg = 0
    total_neu = 0
    for n in news:
        # 제목과 설명을 합쳐 분석
        text = (n.get("title", "") + " " + n.get("desc", ""))
        s = classify_sentiment(text)
        n["sentiment"] = s  # 각 뉴스에 감성 추가
        if s > 0:
            total_pos += 1
        elif s < 0:
            total_neg += 1
        else:
            total_neu += 1
    score = total_pos - total_neg
    return {
        "score": score,
        "pos": total_pos,
        "neg": total_neg,
        "neu": total_neu,
    }


# ===== HTML 렌더링 =====
def render_html(news, a, sig, months, sent=None):
    # 차트용 데이터
    dates = [d.strftime("%Y-%m-%d") for d in a["close"].index]
    closes = [round(float(v), 0) for v in a["close"].values]
    ma20 = [None if pd.isna(v) else round(float(v), 0) for v in a["ma20"].values]
    ma60 = [None if pd.isna(v) else round(float(v), 0) for v in a["ma60"].values]
    volumes = [int(v) for v in a["volume"].values]
    bb_upper = [None if pd.isna(v) else round(float(v), 0) for v in a["bb_upper"].values]
    bb_lower = [None if pd.isna(v) else round(float(v), 0) for v in a["bb_lower"].values]
    macd_line = [None if pd.isna(v) else round(float(v), 0) for v in a["macd"].values]
    macd_signal = [None if pd.isna(v) else round(float(v), 0) for v in a["macd_signal"].values]
    macd_hist = [None if pd.isna(v) else round(float(v), 0) for v in a["macd_hist"].values]
    # ATR
    atr_vals = [None if pd.isna(v) else round(float(v), 0) for v in a["tr"].values]
    # ADX
    adx_vals = [None if pd.isna(v) else round(float(v), 1) for v in a["adx"].values]
    # KDJ
    k_vals = [None if pd.isna(v) else round(float(v), 1) for v in a["k_pct"].values]
    d_vals = [None if pd.isna(v) else round(float(v), 1) for v in a["d_k"].values]
    j_vals = [None if pd.isna(v) else round(float(v), 1) for v in a["j_val"].values]
    # Vol MA20
    vol_ma20_vals = [None if pd.isna(v) else round(float(v), 0) for v in a["vol_ma20"].values]

    # 색상
    color_map = {"BUY": "#27ae60", "SELL": "#e74c3c", "HOLD": "#f39c12"}
    action_color = color_map[sig["action"]]

    # 감성 분석 카드
    sentiment_html = ""
    if sent:
        s = sent["score"]
        if s > 0:
            sent_color, sent_label = "#27ae60", "긍정 우세"
        elif s < 0:
            sent_color, sent_label = "#e74c3c", "부정 우세"
        else:
            sent_color, sent_label = "#f39c12", "중립"
        sentiment_html = f"""
    <div class="card sentiment-card" id="sentimentCard" style="border-left:4px solid {sent_color};">
      <h3>뉴스 감성 분석</h3>
      <div class="sent-score" id="sentScore" style="color:{sent_color};">{s:+d} <span class="sent-label" id="sentLabel">{sent_label}</span></div>
      <div class="sent-bar" id="sentBar">
        <div class="sent-pos" style="width:{sent['pos']/max(len(news),1)*100:.0f}%; background:#27ae60;">긍정 <span id="sentPos">{sent['pos']}</span></div>
        <div class="sent-neu" style="width:{sent['neu']/max(len(news),1)*100:.0f}%; background:#f39c12;">중립 <span id="sentNeu">{sent['neu']}</span></div>
        <div class="sent-neg" style="width:{sent['neg']/max(len(news),1)*100:.0f}%; background:#e74c3c;">부정 <span id="sentNeg">{sent['neg']}</span></div>
      </div>
      <div class="sent-desc" id="sentDesc">최근 뉴스 {len(news)}건 기준. 긍정-부정 점수가 매수/매도 신호에 반영됩니다.</div>
    </div>"""

    news_cards = ""
    if news:
        for i, n in enumerate(news, 1):
            # 감성 배지
            s = n.get("sentiment", 0)
            if s > 0:
                badge = '<span class="badge pos">긍정</span>'
            elif s < 0:
                badge = '<span class="badge neg">부정</span>'
            else:
                badge = '<span class="badge neu">중립</span>'
            news_cards += f"""
        <div class="news-card">
          <div class="news-num">{i}</div>
          <div>
            <div class="news-title">{n['title']} {badge}</div>
            <div class="news-meta">{n['pubDate']}</div>
            <div class="news-desc">{n['desc']}</div>
            <a class="news-link" href="{n['link']}" target="_blank">기사 전문 보기 →</a>
          </div>
        </div>"""
    else:
        news_cards = '<div class="empty">뉴스를 불러오지 못했습니다.</div>'

    reasons_html = "".join(f'<li>{r}</li>' for r in sig["reasons"])

    today = datetime.date.today().strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SK하이닉스 투자 레포트</title>
<canvas id="priceChart"></canvas>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
         background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
         color:#e2e8f0; padding:24px; min-height:100vh; }}
  .wrap {{ max-width:1100px; margin:0 auto; }}
  header {{ position:relative; text-align:center; margin-bottom:30px; }}
  header h1 {{ font-size:1.8rem; margin-bottom:6px; }}
  header .sub {{ color:#94a3b8; font-size:0.95rem; }}
  .refresh-btn {{ position:absolute; right:0; top:0; background:#3b82f6; color:white;
    border:none; padding:10px 18px; border-radius:10px; font-size:0.95rem; font-weight:600;
    cursor:pointer; display:flex; align-items:center; gap:6px; transition:background 0.2s; }}
  .refresh-btn:hover {{ background:#2563eb; }}
  .refresh-btn:disabled {{ opacity:0.6; cursor:wait; }}
  .refresh-btn .icon {{ display:inline-block; transition:transform 0.6s; }}
  .refresh-btn.loading .icon {{ transform:rotate(360deg); }}
  @media (max-width:700px) {{ .refresh-btn {{ position:static; margin-bottom:16px; }} }}
  .toast {{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
    background:#10b981; color:white; padding:12px 24px; border-radius:10px; font-size:0.9rem;
    box-shadow:0 8px 24px rgba(0,0,0,0.3); opacity:0; transition:opacity 0.3s; pointer-events:none; z-index:1000; }}
  .toast.show {{ opacity:1; }}
  .toast.error {{ background:#ef4444; }}
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
  .reasons {{ background:#1e293b; border-radius:12px; padding:18px; margin-top:18px; }}
  .reasons h3 {{ color:#94a3b8; font-size:0.9rem; margin-bottom:10px; }}
  .reasons ul {{ padding-left:20px; }}
  .reasons li {{ margin:6px 0; color:#cbd5e1; font-size:0.92rem; }}
  .empty {{ color:#64748b; text-align:center; padding:30px; }}
  footer {{ text-align:center; color:#475569; font-size:0.8rem; margin-top:30px; }}
  .sentiment-card {{ grid-column: span 2; }}
  .sent-score {{ font-size:2rem; font-weight:700; margin-bottom:12px; }}
  .sent-label {{ font-size:0.95rem; font-weight:500; opacity:0.85; }}
  .sent-bar {{ display:flex; height:24px; border-radius:6px; overflow:hidden; margin:8px 0; }}
  .sent-bar > div {{ display:flex; align-items:center; justify-content:center;
    color:white; font-size:0.78rem; font-weight:600; min-width:0; padding:0 6px; }}
  .sent-desc {{ color:#94a3b8; font-size:0.82rem; margin-top:8px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:6px;
    font-size:0.72rem; font-weight:600; margin-left:8px; vertical-align:middle;
    min-width:44px; height:22px; line-height:18px; text-align:center; white-space:nowrap; box-sizing:border-box; }}
  .badge.pos {{ background:#27ae60; color:white; }}
  .badge.neg {{ background:#e74c3c; color:white; }}
  .badge.neu {{ background:#64748b; color:white; }}
  @media (max-width:700px) {{ .sentiment-card {{ grid-column: span 1; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <button id="refreshBtn" class="refresh-btn" onclick="refreshData()">
      <span class="icon">↻</span> 새로고침
    </button>
    <h1>SK하이닉스(066570) 투자 레포트</h1>
    <div class="sub" id="subText">기준일 {today} · 최근 {months}개월 데이터 · 기술 분석 기반</div>
  </header>

  <div class="action-box" id="actionBox" style="background:{action_color};">
    <div class="label">종합 추천</div>
    <div class="action" id="actionLabel">{sig['label']}</div>
    <div class="score" id="actionScore">신호 점수: {sig['score']:+d} (BUY≥2 / SELL≤-2 / HOLD 그 외)</div>
  </div>

  <div class="grid2">
    <div class="card">
      <h3>현재 주가</h3>
      <div class="price" id="priceText">{a['cur']:,.0f} 원</div>
      <div class="stat"><span>기간 최고</span><span class="v" id="hiText">{a['hi']:,.0f} 원</span></div>
      <div class="stat"><span>기간 최저</span><span class="v" id="loText">{a['lo']:,.0f} 원</span></div>
      <div class="stat"><span>현재 위치</span><span class="v" id="posText">{a['pos']:.0f}%</span></div>
      <div class="pos"><div id="posBar" style="width:{a['pos']:.0f}%;"></div></div>
    </div>
    <div class="card">
      <h3>기술 지표</h3>
      <div class="stat"><span>MA20 (20일 이평선)</span><span class="v" id="ma20Text">{a['cur_ma20']:,.0f} 원</span></div>
      <div class="stat"><span>MA60 (60일 이평선)</span><span class="v" id="ma60Text">{a['cur_ma60']:,.0f} 원</span></div>
      <div class="stat"><span>RSI (14일)</span><span class="v" id="rsiText">{a['cur_rsi']:.1f}</span></div>
      <div class="stat"><span>BB 상단 (20일, 2σ)</span><span class="v" id="bbUpperText">{a['cur_bb_upper']:,.0f} 원</span></div>
      <div class="stat"><span>BB 하단 (20일, 2σ)</span><span class="v" id="bbLowerText">{a['cur_bb_lower']:,.0f} 원</span></div>
      <div class="stat"><span>BB 폭 / 밴드 내 위치</span><span class="v" id="bbWidthText">{a['cur_bb_width']:.1f}% / {a['bb_pos']:.0f}%</span></div>
      <div class="stat"><span>MACD / 시그널</span><span class="v" id="macdText">{a['cur_macd']:.0f} / {a['cur_macd_sig']:.0f}</span></div>
      <div class="stat"><span>MACD 히스토그램</span><span class="v" id="macdHistText">{a['cur_macd_hist']:+.0f}</span></div>
      <div class="stat"><span>ATR (14일)</span><span class="v" id="atrText">{a['cur_atr']:,.0f}원 ({a['atr_pct']:.1f}%)</span></div>
      <div class="stat"><span>ADX (14일)</span><span class="v" id="adxText">{a['cur_adx']:.1f}</span></div>
      <div class="stat"><span>KDJ</span><span class="v" id="kdjText">K {a['cur_k']:.1f} / D {a['cur_d']:.1f} / J {a['cur_j']:.1f}</span></div>
      <div class="stat"><span>거래량비 (Vol MA20 대비)</span><span class="v" id="volRatioText">{a['vol_ratio']:.1f}x</span></div>
      <div class="reasons">
        <h3>판단 근거</h3>
        <ul id="reasonsList">{reasons_html}</ul>
      </div>
    </div>
  </div>

  {sentiment_html}

  <div class="chart-card">
    <h3>주가 차트 (종가 + 이동평균선)</h3>
    <div id="priceChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <div class="chart-card">
    <h3>거래량</h3>
    <div id="volChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <div class="chart-card">
    <h3>MACD (12, 26, 9)</h3>
    <div id="macdChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <div class="chart-card">
    <h3>ATR (14일 변동성) & ADX (추세 강도)</h3>
    <div id="atrAdxChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <div class="chart-card">
    <h3>KDJ (Stochastic Oscillator)</h3>
    <div id="kdjChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <div class="chart-card">
    <h3>거래량 & 거래량 이평선 (MA20)</h3>
    <div id="volMaChart" style="width:100%;height:300px;position:relative;"></div>
  </div>

  <h3 style="color:#94a3b8;font-size:0.9rem;text-transform:uppercase;margin:24px 0 12px;" id="newsHeader">최신 뉴스 Top {len(news)}</h3>
  <div class="news-list" id="newsList">{news_cards}</div>

  <footer>
    ⚠️ 본 레포트는 자동 생성된 참고용 자료이며, 실제 투자는 본인 판단으로 결정하세요.
    데이터: Yahoo Finance · 네이버 뉴스
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
const macdSignal = {json.dumps(macd_signal)};
const macdHist = {json.dumps(macd_hist)};
const atrData = {json.dumps(atr_vals)};
const adxData = {json.dumps(adx_vals)};
const kData = {json.dumps(k_vals)};
const dData = {json.dumps(d_vals)};
const jData = {json.dumps(j_vals)};
const volMa20 = {json.dumps(vol_ma20_vals)};
const MONTHS = {months};

// ===== Canvas API 차트 그리기 =====
function drawLineChart(containerId, datasets, yMin, yMax, xLabel) {{
  const container = document.getElementById(containerId);
  if (!container) return;
  const W = container.clientWidth || 1000;
  const H = container.clientHeight || 300;
  const M = {{ top: 20, right: 20, bottom: 40, left: 70 }};
  const cW = W - M.left - M.right;
  const cH = H - M.top - M.bottom;

  container.innerHTML = '<canvas id="' + containerId + '_canvas" width="' + W + '" height="' + H + '" style="width:100%;height:100%"></canvas>';
  const canvas = container.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#334155';
  ctx.lineWidth = 1;

  // Y 축 그리드
  for (let i = 0; i <= 5; i++) {{
    const y = M.top + (cH * i / 5);
    ctx.beginPath();
    ctx.moveTo(M.left, y);
    ctx.lineTo(M.left + cW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    const val = yMax - (yMax - yMin) * i / 5;
    ctx.fillText(Math.round(val).toLocaleString(), M.left - 5, y + 4);
  }}

  // X 축 레이블
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.floor(dates.length / 8));
  for (let i = 0; i < dates.length; i += step) {{
    const x = M.left + (i / (dates.length - 1)) * cW;
    ctx.fillStyle = '#64748b';
    ctx.fillText(dates[i].slice(5), x, H - 10);
  }}

  // 데이터셋 그리기
  const colors = ['#38bdf8', '#f59e0b', '#a78bfa', '#e67e22', '#e74c3c', '#10b981'];
  datasets.forEach((ds, idx) => {{
    const color = ds.color || colors[idx % colors.length];
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < ds.data.length; i++) {{
      if (ds.data[i] == null) continue;
      const x = M.left + (i / (ds.data.length - 1)) * cW;
      const y = M.top + (1 - (ds.data[i] - yMin) / (yMax - yMin)) * cH;
      if (!started) {{
        ctx.moveTo(x, y);
        started = true;
      }} else {{
        ctx.lineTo(x, y);
      }}
    }}
    ctx.stroke();
  }});
}}

function drawBarChart(containerId, data, colors, yMin, yMax) {{
  const container = document.getElementById(containerId);
  if (!container) return;
  const W = container.clientWidth || 1000;
  const H = container.clientHeight || 300;
  const M = {{ top: 20, right: 20, bottom: 40, left: 70 }};
  const cW = W - M.left - M.right;
  const cH = H - M.top - M.bottom;

  container.innerHTML = '<canvas id="' + containerId + '_canvas" width="' + W + '" height="' + H + '" style="width:100%;height:100%"></canvas>';
  const canvas = container.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(0, 0, W, H);

  // 그리드
  ctx.strokeStyle = '#334155';
  for (let i = 0; i <= 5; i++) {{
    const y = M.top + (cH * i / 5);
    ctx.beginPath();
    ctx.moveTo(M.left, y);
    ctx.lineTo(M.left + cW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    const val = yMax - (yMax - yMin) * i / 5;
    ctx.fillText(Math.round(val).toLocaleString(), M.left - 5, y + 4);
  }}

  // 막대
  const barW = Math.max(1, (cW / data.length) * 0.6);
  data.forEach((v, i) => {{
    const x = M.left + (i / data.length) * cW + (cW / data.length - barW) / 2;
    const h = (v / yMax) * cH;
    const y = M.top + cH - h;
    ctx.fillStyle = colors ? colors[i % colors.length] : '#3b82f680';
    ctx.fillRect(x, y, barW, h);
  }});
}}

// 차트 그리기
drawLineChart('priceChart', [
  {{ data: bbUpper, color: 'rgba(148,163,184,0.4)' }},
  {{ data: bbLower, color: 'rgba(148,163,184,0.4)' }},
  {{ data: closes, color: '#38bdf8' }},
  {{ data: ma20, color: '#f59e0b' }},
  {{ data: ma60, color: '#a78bfa' }}
], 0, Math.max(...closes.map(c => c || 0), ...ma20.filter(v => v), ...ma60.filter(v => v)) * 1.1);

drawBarChart('volChart', volumes, null, 0, Math.max(...volumes) * 1.2);

// MACD
const macdMax = Math.max(Math.abs(Math.max(...macdHist.filter(v => v))), Math.abs(Math.min(...macdHist.filter(v => v)))) * 1.1;
drawBarChart('macdChart', macdHist, macdHist.map(v => v >= 0 ? 'rgba(39,174,96,0.6)' : 'rgba(231,76,60,0.6)'), -macdMax, macdMax);

// ATR & ADX (복합 차트)
const atrAdxMax = Math.max(Math.max(...atrData.filter(v => v)) * 1.1, 100);
drawLineChart('atrAdxChart', [
  {{ data: atrData, color: '#e67e22' }},
  {{ data: adxData, color: '#e74c3c' }}
], 0, atrAdxMax);

// KDJ
drawLineChart('kdjChart', [
  {{ data: kData, color: '#38bdf8' }},
  {{ data: dData, color: '#f59e0b' }},
  {{ data: jData, color: '#a78bfa' }}
], 0, 120);

// 거래량 & Vol MA20
drawLineChart('volMaChart', [
  {{ data: volumes, color: '#3b82f680' }},
  {{ data: volMa20, color: '#f59e0b' }}
], 0, Math.max(...volumes, ...volMa20.filter(v => v)) * 1.2);

// ===== 새로고침 기능 =====
const TICKER = "{TICKER}";
let toastTimer = null;

function showToast(msg, isError) {{
  let t = document.getElementById('toast');
  if (!t) {{
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast';
    document.body.appendChild(t);
  }}
  t.textContent = msg;
  t.className = 'toast show' + (isError ? ' error' : '');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast' + (isError ? ' error' : ''), 2200);
}}

// 이동평균선 계산
function sma(arr, n) {{
  const out = new Array(arr.length).fill(null);
  for (let i = n - 1; i < arr.length; i++) {{
    let sum = 0;
    for (let j = i - n + 1; j <= i; j++) sum += arr[j];
    out[i] = sum / n;
  }}
  return out;
}}

// RSI(14) 계산
function calcRSI(arr, n = 14) {{
  const out = new Array(arr.length).fill(null);
  let gain = 0, loss = 0;
  for (let i = 1; i <= n; i++) {{
    const d = arr[i] - arr[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }}
  let avgG = gain / n, avgL = loss / n;
  out[n] = 100 - 100 / (1 + (avgL === 0 ? 100 : avgG / avgL));
  for (let i = n + 1; i < arr.length; i++) {{
    const d = arr[i] - arr[i - 1];
    const g = d > 0 ? d : 0, l = d < 0 ? -d : 0;
    avgG = (avgG * (n - 1) + g) / n;
    avgL = (avgL * (n - 1) + l) / n;
    out[i] = avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL);
  }}
  return out;
}}

// 표준편차 계산
function std(arr, n, end) {{
  const slice = arr.slice(end - n + 1, end + 1);
  const mean = slice.reduce((a, b) => a + b, 0) / n;
  const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
  return Math.sqrt(variance);
}}

// 볼린저 밴드 계산
function calcBB(closes, n = 20, k = 2) {{
  const upper = new Array(closes.length).fill(null);
  const lower = new Array(closes.length).fill(null);
  const width = new Array(closes.length).fill(null);
  for (let i = n - 1; i < closes.length; i++) {{
    const ma = sma(closes.slice(), n)[i];
    if (ma == null) continue;
    const sd = std(closes, n, i);
    upper[i] = ma + k * sd;
    lower[i] = ma - k * sd;
    width[i] = ma > 0 ? (upper[i] - lower[i]) / ma * 100 : 0;
  }}
  return {{ upper, lower, width }};
}}

// EMA 계산
function ema(arr, n) {{
  const out = new Array(arr.length).fill(null);
  const k = 2 / (n + 1);
  let prev = null;
  for (let i = 0; i < arr.length; i++) {{
    if (arr[i] == null) continue;
    if (prev == null) prev = arr[i];
    else prev = arr[i] * k + prev * (1 - k);
    out[i] = prev;
  }}
  return out;
}}

// MACD 계산 (12, 26, 9)
function calcMACD(closes) {{
  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const macd = closes.map((_, i) =>
    (ema12[i] != null && ema26[i] != null) ? ema12[i] - ema26[i] : null);
  const signal = ema(macd.map(v => v == null ? 0 : v), 9).map((v, i) => macd[i] == null ? null : v);
  const hist = macd.map((v, i) => (v != null && signal[i] != null) ? v - signal[i] : null);
  return {{ macd, signal, hist }};
}}

// ===== 뉴스 감성 분석 (JS) =====
const POSITIVE_WORDS = {json.dumps(POSITIVE_WORDS)};
const NEGATIVE_WORDS = {json.dumps(NEGATIVE_WORDS)};

function classifySentiment(text) {{
  if (!text) return 0;
  let pos = 0, neg = 0;
  for (const w of POSITIVE_WORDS) if (text.includes(w)) pos++;
  for (const w of NEGATIVE_WORDS) if (text.includes(w)) neg++;
  return pos > neg ? 1 : neg > pos ? -1 : 0;
}}

function analyzeSentimentJS(news) {{
  let p = 0, n = 0, u = 0;
  for (const item of news) {{
    const s = classifySentiment((item.title || '') + ' ' + (item.desc || ''));
    item.sentiment = s;
    if (s > 0) p++; else if (s < 0) n++; else u++;
  }}
  return {{ score: p - n, pos: p, neg: n, neu: u }};
}}

// Google News RSS에서 뉴스 가져오기
async function fetchNews() {{
  const rssUrl = 'https://news.google.com/rss/search?q=' + encodeURIComponent('{QUERY}') + '&hl=ko&gl=KR&ceid=KR:ko';
  const proxies = [
    `https://corsproxy.io/?url=${{encodeURIComponent(rssUrl)}}`,
    `https://api.allorigins.win/raw?url=${{encodeURIComponent(rssUrl)}}`,
  ];
  let lastErr;
  for (const url of proxies) {{
    try {{
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
      const text = await r.text();
      const parser = new DOMParser();
      const xml = parser.parseFromString(text, 'text/xml');
      const items = [...xml.querySelectorAll('item')].slice(0, {NEWS_COUNT}).map(it => {{
        let title = it.querySelector('title')?.textContent || '';
        let source = '';
        const dashIdx = title.lastIndexOf(' - ');
        if (dashIdx > 0) {{ source = title.slice(dashIdx + 3); title = title.slice(0, dashIdx); }}
        let pub = it.querySelector('pubDate')?.textContent || '';
        try {{
          const d = new Date(pub);
          if (!isNaN(d)) pub = d.toISOString().slice(0, 16).replace('T', ' ');
        }} catch (e) {{}}
        return {{
          title, source,
          link: it.querySelector('link')?.textContent || '',
          pubDate: pub,
          desc: source ? `출처: ${{source}}` : '',
        }};
      }});
      return items;
    }} catch (e) {{ lastErr = e; }}
  }}
  throw lastErr || new Error('뉴스 조회 실패');
}}

// 신호 점수 계산 (Python 로직과 동일)
function calcSignal(cur, ma20v, ma60v, rsi, pos, bbPos, bbWidth, macdV, macdSigV, macdHistV, macdTrend, sentScore) {{
  let score = 0;
  const reasons = [];
  if (ma20v != null && ma60v != null) {{
    if (ma20v > ma60v) {{ score += 1; reasons.push("단기이평선이 장기이평선 위(골든크로스) - 상승 추세"); }}
    else {{ score -= 1; reasons.push("단기이평선이 장기이평선 아래(데드크로스) - 하락 추세"); }}
  }}
  if (ma20v != null) {{
    if (cur > ma20v) {{ score += 1; reasons.push(`현재가 ${{Math.round(cur)}}원이 MA20 ${{Math.round(ma20v)}}원 위 - 단기 강세`); }}
    else {{ score -= 1; reasons.push(`현재가 ${{Math.round(cur)}}원이 MA20 ${{Math.round(ma20v)}}원 아래 - 단기 약세`); }}
  }}
  if (rsi != null) {{
    if (rsi < 30) {{ score += 2; reasons.push(`RSI ${{rsi.toFixed(1)}} - 과매도 구간 (반등 가능)`); }}
    else if (rsi > 70) {{ score -= 2; reasons.push(`RSI ${{rsi.toFixed(1)}} - 과매수 구간 (조정 가능)`); }}
    else {{ reasons.push(`RSI ${{rsi.toFixed(1)}} - 중립 구간`); }}
  }}
  if (pos > 80) {{ score -= 1; reasons.push(`최근 최고가 대비 ${{Math.round(pos)}}% 위치 - 고점 근접`); }}
  else if (pos < 20) {{ score += 1; reasons.push(`최근 최저가 대비 ${{Math.round(pos)}}% 위치 - 저점 근접`); }}
  if (bbPos != null) {{
    if (bbPos < 10) {{ score += 2; reasons.push(`볼린저밴드 하단 접근 (위치 ${{Math.round(bbPos)}}%) - 과매도/반등 가능`); }}
    else if (bbPos > 90) {{ score -= 2; reasons.push(`볼린저밴드 상단 접근 (위치 ${{Math.round(bbPos)}}%) - 과매수/조정 가능`); }}
    else if (bbPos < 20) {{ score += 1; reasons.push(`볼린저밴드 하단 근접 (위치 ${{Math.round(bbPos)}}%) - 단기 약세`); }}
    else if (bbPos > 80) {{ score -= 1; reasons.push(`볼린저밴드 상단 근접 (위치 ${{Math.round(bbPos)}}%) - 단기 강세`); }}
    else {{ reasons.push(`볼린저밴드 중간 구간 (위치 ${{Math.round(bbPos)}}%) - 밴드 내 정상`); }}
    if (bbWidth != null) {{
      if (bbWidth < 5) reasons.push(`밴드 폭 ${{bbWidth.toFixed(1)}}% - 변동성 축소 (큰 움직임 임박)`);
      else if (bbWidth > 20) reasons.push(`밴드 폭 ${{bbWidth.toFixed(1)}}% - 변동성 확대`);
    }}
  }}
  if (macdV != null && macdSigV != null) {{
    if (macdV > macdSigV && macdHistV > 0) {{
      if (macdTrend < 0) {{ score += 2; reasons.push(`MACD 골든크로스 발생 (히스토그램 ${{macdHistV >= 0 ? '+' : ''}}${{macdHistV.toFixed(0)}}) - 강한 매수 신호`); }}
      else {{ score += 1; reasons.push(`MACD 시그널 상향 (히스토그램 ${{macdHistV >= 0 ? '+' : ''}}${{macdHistV.toFixed(0)}}) - 상승 모멘텀`); }}
    }} else if (macdV < macdSigV && macdHistV < 0) {{
      if (macdTrend > 0) {{ score -= 2; reasons.push(`MACD 데드크로스 발생 (히스토그램 ${{macdHistV >= 0 ? '+' : ''}}${{macdHistV.toFixed(0)}}) - 강한 매도 신호`); }}
      else {{ score -= 1; reasons.push(`MACD 시그널 하향 (히스토그램 ${{macdHistV >= 0 ? '+' : ''}}${{macdHistV.toFixed(0)}}) - 하락 모멘텀`); }}
    }} else {{
      reasons.push(`MACD 중립 (히스토그램 ${{macdHistV >= 0 ? '+' : ''}}${{macdHistV.toFixed(0)}}) - 모멘텀 약화`);
    }}
  }}
  if (sentScore != null) {{
    if (sentScore >= 2) {{ score += 2; reasons.push(`뉴스 감성 ${{sentScore >= 0 ? '+' : ''}}${{sentScore}} - 강한 긍정`); }}
    else if (sentScore == 1) {{ score += 1; reasons.push(`뉴스 감성 +1 - 긍정 우세`); }}
    else if (sentScore <= -2) {{ score -= 2; reasons.push(`뉴스 감성 ${{sentScore}} - 강한 부정`); }}
    else if (sentScore == -1) {{ score -= 1; reasons.push(`뉴스 감성 -1 - 부정 우세`); }}
    else {{ reasons.push(`뉴스 감성 0 - 중립`); }}
  }}
  let action, label;
  if (score >= 2) {{ action = "BUY"; label = "매수 추천"; }}
  else if (score <= -2) {{ action = "SELL"; label = "매도 추천"; }}
  else {{ action = "HOLD"; label = "관망 (보유 유지)"; }}
  return {{ action, label, score, reasons }};
}}

async function fetchStockData() {{
  const now = Math.floor(Date.now() / 1000);
  const start = now - (MONTHS * 30 + 5) * 86400;
  const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${{TICKER}}?period1=${{start}}&period2=${{now}}&interval=1d`;
  // Yahoo Finance API는 CORS를 허용하지 않으므로 공개 CORS 프록시 사용
  const proxies = [
    `https://corsproxy.io/?url=${{encodeURIComponent(yahooUrl)}}`,
    `https://api.allorigins.win/raw?url=${{encodeURIComponent(yahooUrl)}}`,
  ];
  let lastErr;
  for (const url of proxies) {{
    try {{
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${{r.status}}`);
      const data = await r.json();
      const res = data?.chart?.result?.[0];
      if (!res) throw new Error("데이터 없음");
      const ts = res.timestamp;
      const q = res.indicators.quote[0];
      const rows = [];
      for (let i = 0; i < ts.length; i++) {{
        if (q.close[i] == null) continue;
        rows.push({{
          date: new Date(ts[i] * 1000).toISOString().slice(0, 10),
          close: q.close[i],
          volume: q.volume[i] ?? 0,
        }});
      }}
      return rows;
    }} catch (e) {{
      lastErr = e;
    }}
  }}
  throw lastErr || new Error("주가 데이터 조회 실패");
}}

async function refreshData() {{
  const btn = document.getElementById('refreshBtn');
  if (btn.disabled) return;
  btn.disabled = true;
  btn.classList.add('loading');
  try {{
    // 주가와 뉴스를 병렬로 갱신
    const [rows, newsItems] = await Promise.all([
      fetchStockData(),
      fetchNews().catch(e => {{ console.warn('뉴스 갱신 실패:', e); return null; }}),
    ]);
    if (rows.length === 0) throw new Error("주가 데이터 없음");

    // 뉴스 갱신 + 감성 재분석
    let sentScore = null;
    if (newsItems && newsItems.length > 0) {{
      const sent = analyzeSentimentJS(newsItems);
      sentScore = sent.score;
      // 뉴스 카드 갱신
      const newsList = document.getElementById('newsList');
      if (newsList) {{
        newsList.innerHTML = newsItems.map((n, i) => {{
          const badge = n.sentiment > 0 ? '<span class="badge pos">긍정</span>'
            : n.sentiment < 0 ? '<span class="badge neg">부정</span>'
            : '<span class="badge neu">중립</span>';
          return `<div class="news-card"><div class="news-num">${{i+1}}</div><div>
            <div class="news-title">${{n.title}} ${{badge}}</div>
            <div class="news-meta">${{n.pubDate}}</div>
            <div class="news-desc">${{n.desc}}</div>
            <a class="news-link" href="${{n.link}}" target="_blank">기사 전문 보기 →</a>
          </div></div>`;
        }}).join('');
      }}
      document.getElementById('newsHeader').textContent = `최신 뉴스 Top ${{newsItems.length}}`;
      // 감성 카드 갱신
      const sc = sent.score;
      const sColor = sc > 0 ? '#27ae60' : sc < 0 ? '#e74c3c' : '#f39c12';
      const sLabel = sc > 0 ? '긍정 우세' : sc < 0 ? '부정 우세' : '중립';
      const card = document.getElementById('sentimentCard');
      if (card) {{
        card.style.borderLeftColor = sColor;
        document.getElementById('sentScore').style.color = sColor;
        document.getElementById('sentScore').innerHTML = `${{sc >= 0 ? '+' : ''}}${{sc}} <span class="sent-label" id="sentLabel">${{sLabel}}</span>`;
        const total = newsItems.length;
        document.getElementById('sentPos').parentElement.style.width = `${{sent.pos/total*100}}%`;
        document.getElementById('sentNeu').parentElement.style.width = `${{sent.neu/total*100}}%`;
        document.getElementById('sentNeg').parentElement.style.width = `${{sent.neg/total*100}}%`;
        document.getElementById('sentPos').textContent = sent.pos;
        document.getElementById('sentNeu').textContent = sent.neu;
        document.getElementById('sentNeg').textContent = sent.neg;
        document.getElementById('sentDesc').textContent = `최근 뉴스 ${{total}}건 기준 (새로고침됨). 긍정-부정 점수가 매수/매도 신호에 반영됩니다.`;
      }}
    }}
    const newDates = rows.map(r => r.date);
    const newCloses = rows.map(r => Math.round(r.close));
    const newVols = rows.map(r => Math.round(r.volume));
    const ma20Arr = sma(rows.map(r => r.close), 20).map(v => v == null ? null : Math.round(v));
    const ma60Arr = sma(rows.map(r => r.close), 60).map(v => v == null ? null : Math.round(v));
    const rsiArr = calcRSI(rows.map(r => r.close), 14);
    const bb = calcBB(rows.map(r => r.close), 20, 2);
    const bbUpperArr = bb.upper.map(v => v == null ? null : Math.round(v));
    const bbLowerArr = bb.lower.map(v => v == null ? null : Math.round(v));
    const mc = calcMACD(rows.map(r => r.close));
    const macdArr = mc.macd.map(v => v == null ? null : Math.round(v));
    const macdSigArr = mc.signal.map(v => v == null ? null : Math.round(v));
    const macdHistArr = mc.hist.map(v => v == null ? null : Math.round(v));

    const cur = rows[rows.length - 1].close;
    const hi = Math.max(...rows.map(r => r.close));
    const lo = Math.min(...rows.map(r => r.close));
    const pos = hi > lo ? (cur - lo) / (hi - lo) * 100 : 50;
    const curMa20 = ma20Arr[ma20Arr.length - 1];
    const curMa60 = ma60Arr[ma60Arr.length - 1];
    const curRsi = rsiArr[rsiArr.length - 1];
    const curBbU = bb.upper[bb.upper.length - 1];
    const curBbL = bb.lower[bb.lower.length - 1];
    const curBbW = bb.width[bb.width.length - 1];
    const bbPos = (curBbU != null && curBbL != null && curBbU > curBbL)
      ? (cur - curBbL) / (curBbU - curBbL) * 100 : 50;
    const curMacd = mc.macd[mc.macd.length - 1];
    const curMacdSig = mc.signal[mc.signal.length - 1];
    const curMacdHist = mc.hist[mc.hist.length - 1];
    const macdTrend = mc.hist.slice(-3).filter(v => v != null).length >= 2
      ? (mc.hist[mc.hist.length - 1] || 0) - (mc.hist[mc.hist.length - 3] || 0) : 0;
    const sig = calcSignal(cur, curMa20, curMa60, curRsi, pos, bbPos, curBbW, curMacd, curMacdSig, curMacdHist, macdTrend, sentScore);

    // 차트 업데이트
    priceChart.data.labels = newDates;
    priceChart.data.datasets[0].data = bbUpperArr;  // BB 상단
    priceChart.data.datasets[1].data = bbLowerArr;  // BB 하단
    priceChart.data.datasets[2].data = newCloses;   // 종가
    priceChart.data.datasets[3].data = ma20Arr;     // MA20
    priceChart.data.datasets[4].data = ma60Arr;     // MA60
    priceChart.update();
    volChart.data.labels = newDates;
    volChart.data.datasets[0].data = newVols;
    volChart.update();
    macdChart.data.labels = newDates;
    macdChart.data.datasets[0].data = macdHistArr;   // 히스토그램
    macdChart.data.datasets[1].data = macdArr;       // MACD
    macdChart.data.datasets[2].data = macdSigArr;   // 시그널
    macdChart.update();

    // 텍스트 업데이트
    const nf = n => Math.round(n).toLocaleString();
    document.getElementById('priceText').textContent = `${{nf(cur)}} 원`;
    document.getElementById('hiText').textContent = `${{nf(hi)}} 원`;
    document.getElementById('loText').textContent = `${{nf(lo)}} 원`;
    document.getElementById('posText').textContent = `${{Math.round(pos)}}%`;
    document.getElementById('posBar').style.width = `${{Math.round(pos)}}%`;
    if (curMa20 != null) document.getElementById('ma20Text').textContent = `${{nf(curMa20)}} 원`;
    if (curMa60 != null) document.getElementById('ma60Text').textContent = `${{nf(curMa60)}} 원`;
    if (curRsi != null) document.getElementById('rsiText').textContent = curRsi.toFixed(1);
    if (curBbU != null) document.getElementById('bbUpperText').textContent = `${{nf(curBbU)}} 원`;
    if (curBbL != null) document.getElementById('bbLowerText').textContent = `${{nf(curBbL)}} 원`;
    if (curBbW != null) document.getElementById('bbWidthText').textContent = `${{curBbW.toFixed(1)}}% / ${{Math.round(bbPos)}}%`;
    if (curMacd != null) document.getElementById('macdText').textContent = `${{Math.round(curMacd)}} / ${{Math.round(curMacdSig)}}`;
    if (curMacdHist != null) document.getElementById('macdHistText').textContent = `${{curMacdHist >= 0 ? '+' : ''}}${{Math.round(curMacdHist)}}`;

    // 추천 박스
    const colors = {{ BUY: "#27ae60", SELL: "#e74c3c", HOLD: "#f39c12" }};
    const box = document.getElementById('actionBox');
    box.style.background = colors[sig.action];
    document.getElementById('actionLabel').textContent = sig.label;
    document.getElementById('actionScore').textContent = `신호 점수: ${{sig.score >= 0 ? '+' : ''}}${{sig.score}} (BUY≥2 / SELL≤-2 / HOLD 그 외)`;

    // 판단 근거
    document.getElementById('reasonsList').innerHTML = sig.reasons.map(r => `<li>${{r}}</li>`).join('');

    // 기준일
    const today = new Date().toISOString().slice(0, 10);
    document.getElementById('subText').textContent = `기준일 ${{today}} · 최근 ${{MONTHS}}개월 데이터 · 기술 분석 기반 (새로고침됨)`;

    showToast(`새로고침 완료 · 현재가 ${{nf(cur)}}원`);
  }} catch (e) {{
    showToast(`새로고침 실패: ${{e.message}}`, true);
  }} finally {{
    btn.disabled = false;
    btn.classList.remove('loading');
  }}
}}

// ===== 페이지 로드 시 자동 새로고침 =====
window.addEventListener('DOMContentLoaded', () => {{
  // URL 파라미터 ?noauto=1 이 있으면 자동 새로고침 건너뛰기
  if (new URLSearchParams(window.location.search).has('noauto')) return;
  // 1.5초 후 자동 새로고침
  setTimeout(refreshData, 1500);
}});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="SK하이닉스 투자 레포트 생성")
    parser.add_argument("--months", type=int, default=3, help="분석 기간 (개월, 기본 3)")
    args = parser.parse_args()

    print(f"[1/5] 네이버 뉴스 검색: {QUERY}")
    news = fetch_news()
    print(f"  → {len(news)}건")

    print("[2/5] 뉴스 감성 분석")
    sent = analyze_sentiment(news)
    print(f"  → 감성 점수: {sent['score']:+d} (긍정 {sent['pos']}/부정 {sent['neg']}/중립 {sent['neu']})")

    print(f"[3/5] Yahoo Finance 주가 데이터: {TICKER} (최근 {args.months}개월)")
    df = fetch_stock(args.months)
    print(f"  → {len(df)}일 데이터")

    print("[4/5] 기술 분석 계산")
    a = analyze(df)
    sig = signal(a, sent)
    print(f"  → 추천: {sig['label']} (점수 {sig['score']:+d})")

    print("[5/5] HTML 레포트 생성")
    html = render_html(news, a, sig, args.months, sent)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {out_path}")

    # 요약 출력
    print("\n" + "=" * 50)
    print(f"추천: {sig['label']}  (점수 {sig['score']:+d})")
    print(f"현재가: {a['cur']:,.0f}원  RSI: {a['cur_rsi']:.1f}")
    print("=" * 50)
    print(f"\n레포트 파일: {out_path}")


if __name__ == "__main__":
    main()
