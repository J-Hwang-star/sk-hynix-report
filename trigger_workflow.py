"""수동/스케줄 트리거용 GitHub Actions dispatch 스크립트"""
import os
import urllib.request
import ssl

REPO = "J-Hwang-star/sk-hynix-report"
WORKFLOW = "update-report.yml"
TOKEN_FILE = os.path.expanduser("~/.gh_token")

def trigger():
    token = open(TOKEN_FILE, encoding="utf-8").read().strip()
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
    body = b'{"ref":"master"}'
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        print(f"Trigger OK: HTTP {resp.status}")
    except Exception as e:
        print(f"Trigger FAILED: {e}")

if __name__ == "__main__":
    trigger()
