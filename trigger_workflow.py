"""수동/스케줄 트리거용 GitHub Actions dispatch 스크립트.

GitHub Actions schedule 크론은 큐 밀림/누락이 잦아 5분 폴링도 불안정.
외부 cron(작업 스케줄러 등)에서 이 스크립트를 10분 간격으로 호출하면
workflow_dispatch 이벤트로 강제 트리거되어 schedule 누락을 보완한다.

사용:
    python trigger_workflow.py            # 일반 (force=false)
    python trigger_workflow.py --force    # 강제 (debounce/장외 스킵)

외부 스케줄 예시 (Windows 작업 스케줄러, KST):
    장내 09:00~16:30 -> 10분 간격
    폐장 후 17:00, 17:15 -> 2회
"""
import os
import sys
import json
import urllib.request
import ssl

REPO = "J-Hwang-star/sk-hynix-report"
WORKFLOW = "update-report.yml"
TOKEN_FILE = os.path.expanduser("~/.gh_token")


def trigger(force: bool = False) -> bool:
    token = open(TOKEN_FILE, encoding="utf-8").read().strip()
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
    body = json.dumps({
        "ref": "master",
        "inputs": {"force": "true" if force else "false"},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        print(f"Trigger OK: HTTP {resp.status} (force={force})")
        return True
    except Exception as e:
        print(f"Trigger FAILED: {e}")
        return False


if __name__ == "__main__":
    force = "--force" in sys.argv
    ok = trigger(force=force)
    sys.exit(0 if ok else 1)
