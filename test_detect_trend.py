# -*- coding: utf-8 -*-
"""detect_trend() 시나리오 테스트.

전환 인식 지연 개선 검증:
  S1. 하락→상승 전환 초기: +1
  S2. 상승→하락 전환 초기: -1
  S3. 횡보장: 0 유지 (과다 신호 방지)
  S4. 강한 상승 추세 유지: +1
  S5. 강한 하락 추세 유지: -1
"""
import sys
import math
import numpy as np
import pandas as pd
import pytest

from sk_hynix_report import analyze, detect_trend


def _synth_df(trend_path, start=100_000):
    """일별 종가 경로로부터 DataFrame 생성 (고가/저가/거래량 포함).

    trend_path: 일별 종가 리스트 (예: [100000, 99500, 99000, ...])
    """
    n = len(trend_path)
    closes = np.array(trend_path, dtype=float)
    # 고가는 종가 ±1.5%, 저가는 종가 ∓1.5%
    noise = np.linspace(-0.001, 0.001, n)
    highs = closes * (1.005 + noise)
    lows = closes * (0.995 + noise)
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = np.full(n, 1_000_000, dtype=float)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows,
         "Close": closes, "Volume": volumes},
        index=dates,
    )


def _make_path(segments):
    """세그먼트(개수, 방향)를 이어 붙여 경로 생성.
    segments: [(n_days, daily_change_rate), ...]
    예: [(60, -0.005), (10, 0.005)] -> 60일 하락 후 10일 상승
    """
    prices = [100_000.0]
    for n, rate in segments:
        for _ in range(n):
            prices.append(prices[-1] * (1 + rate))
    return prices[1:]


# ---- S4: 강한 상승 추세 유지 ----
def test_s4_strong_uptrend():
    """120일간 일관되게 +0.5%/일 상승 → 상승 추세."""
    path = _make_path([(200, 0.005)])
    df = _synth_df(path)
    a = analyze(df)
    assert detect_trend(a) == 1, f"강한 상승 추세를 인식 못함 (got {detect_trend(a)})"


# ---- S5: 강한 하락 추세 유지 ----
def test_s5_strong_downtrend():
    """120일간 일관되게 -0.5%/일 하락 → 하락 추세."""
    path = _make_path([(200, -0.005)])
    df = _synth_df(path)
    a = analyze(df)
    assert detect_trend(a) == -1, f"강한 하락 추세를 인식 못함 (got {detect_trend(a)})"


# ---- S3: 횡보장 ----
def test_s3_sideways():
    """좁은 박스권 ±0.1%/일 진동 → 횡보 (0)."""
    # 매일 왕복: +0.1% / -0.1% 교차
    segments = []
    for _ in range(100):
        segments.append((1, 0.001))
        segments.append((1, -0.001))
    path = _make_path(segments)
    df = _synth_df(path)
    a = analyze(df)
    assert detect_trend(a) == 0, f"횡보장을 추세로 오판 (got {detect_trend(a)})"


# ---- S1: 하락 → 상승 전환 초기 ----
def test_s1_downtrend_to_uptrend():
    """90일 하락 후 5일간 강한 반등(+0.8%/일) → 상승으로 전환 인식."""
    path = _make_path([(90, -0.005), (5, 0.008)])
    df = _synth_df(path)
    a = analyze(df)
    trend = detect_trend(a)
    assert trend == 1, (
        f"하락→상승 전환(5일)을 인식 못함 (got {trend}, expected 1). "
        f"MA20={a['cur_ma20']:.0f}, macd_hist={a['cur_macd_hist']}"
    )


# ---- S2: 상승 → 하락 전환 초기 ----
def test_s2_uptrend_to_downtrend():
    """90일 상승 후 5일간 강한 하락(-0.8%/일) → 하락으로 전환 인식."""
    path = _make_path([(90, 0.005), (5, -0.008)])
    df = _synth_df(path)
    a = analyze(df)
    trend = detect_trend(a)
    assert trend == -1, (
        f"상승→하락 전환(5일)을 인식 못함 (got {trend}, expected -1). "
        f"MA20={a['cur_ma20']:.0f}, macd_hist={a['cur_macd_hist']}"
    )


# ---- S1-b: 하락 → 상승 전환 (완만, 7일) ----
def test_s1b_slow_reversal():
    """90일 하락 후 7일간 +0.5%/일 반등 → 상승 전환 인식 (7일 이내)."""
    path = _make_path([(90, -0.005), (7, 0.005)])
    df = _synth_df(path)
    a = analyze(df)
    trend = detect_trend(a)
    assert trend == 1, (
        f"하락→상승 완만 전환(7일)을 인식 못함 (got {trend}, expected 1)"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
