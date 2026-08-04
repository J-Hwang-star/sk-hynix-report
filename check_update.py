"""SK Hynix Report 자동 갱신 상태 확인.

GitHub Actions 실행 이력 + 최신 커밋 시각 + Pages 최종 업데이트를 종합 출력.
내일 장 시간(KST 09:00~16:30)에 실행하여 자동 갱신이 잘 동작하는지 검증.

사용:
    python check_update.py
"""
import os
import sys
import urllib.request
import ssl
import json
from datetime import datetime, timezone, timedelta

# Windows 콘솔 인코딩 강제 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = "J-Hwang-star/sk-hynix-report"
TOKEN_FILE = os.path.expanduser("~/.gh_token")
KST = timezone(timedelta(hours=9))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api(path):
    token = open(TOKEN_FILE).read().strip()
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    return json.loads(urllib.request.urlopen(req, context=ctx, timeout=15).read())


def to_kst(iso):
    dt = datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc).astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M KST")


def main():
    print("=" * 60)
    print(f"SK Hynix Report 자동 갱신 상태 (now: {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')})")
    print("=" * 60)

    # 최근 Actions 실행 (5개)
    runs = api("actions/runs?per_page=10")["workflow_runs"]
    print("\n[최근 Actions 실행]")
    for x in runs[:8]:
        ev = x["event"]
        if ev == "dynamic" and "pages" in str(x.get("name", "")).lower():
            ev = "pages-build"
        conc = x.get("conclusion") or x["status"]
        print(f"  {to_kst(x['created_at'])} | {ev:18} | {conc}")

    # 최신 커밋
    commits = api("commits?per_page=3")
    print("\n[최근 커밋]")
    for c in commits[:3]:
        print(f"  {to_kst(c['commit']['author']['date'])} | {c['commit']['message'][:50]}")

    # 최신 갱신 커밋 찾기 (Auto-update 또는 force 트리거)
    last_update = None
    for c in commits:
        msg = c["commit"]["message"]
        if "Auto-update" in msg or "force" in msg.lower() or "report" in msg.lower():
            last_update = c["commit"]["author"]["date"]
            break
    if last_update:
        dt = datetime.strptime(last_update.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(KST)
        elapsed_min = int((datetime.now(KST) - dt).total_seconds() // 60)
        print(f"\n[최종 리포트 갱신] {dt.strftime('%Y-%m-%d %H:%M KST')} ({elapsed_min}분 전)")

    # 판정
    now = datetime.now(KST)
    print("\n[판정]")
    if now.weekday() >= 5:
        print("  주말 - 장 안 열림. 자동 갱신 스킵됨 (정상)")
        return
    hour_min = now.hour * 60 + now.minute
    if hour_min < 540:
        print("  장전 (09:00 이전) - 아직 자동 갱신 안 됨 (정상)")
    elif hour_min <= 990:
        if last_update:
            if elapsed_min <= 30:
                print(f"  장중 - 최근 갱신 {elapsed_min}분 전 [OK] 정상")
            elif elapsed_min <= 60:
                print(f"  장중 - 최근 갱신 {elapsed_min}분 전 [WARN] 약간 지연 (debounce 25분 + schedule 밀림 가능)")
            else:
                print(f"  장중 - 최근 갱신 {elapsed_min}분 전 [ERR] 지연 의심 (작업 스케줄러/GitHub Actions 확인 필요)")
    else:
        print("  장후 - 폐장. afterhours(17:00~17:30) 정리 갱신만 동작")


if __name__ == "__main__":
    main()
