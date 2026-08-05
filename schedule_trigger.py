"""SK Hynix Report — Windows 작업 스케줄러 외부 보조 트리거 등록/해제.

KST 장내 시간(10:00~16:00)에 2시간 간격으로 trigger_workflow.py를 실행하여
GitHub Actions workflow_dispatch를 호출 → GitHub Actions schedule 큐 밀림/누락 보완.
(실행 시점: 10:00, 12:00, 14:00, 16:00)

사용:
    python schedule_trigger.py install    # 작업 등록
    python schedule_trigger.py uninstall  # 작업 해제
    python schedule_trigger.py status     # 상태 확인
    python schedule_trigger.py test       # 수동 1회 실행 테스트

주의: 작업 스케줄러 등록은 현재 사용자 권한으로 실행됨 (관리자 불필요).
      다만 InteractiveToken 로그on 방식이라 PC 켜져 있고 로그인된 상태에서만 동작.
"""
import os
import sys
import subprocess
import tempfile

TASK_NAME = "SKHynixReport_Trigger"
PYTHON = r"C:\Users\2061845\AppData\Local\Programs\Python\Python311\python.exe"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "trigger_workflow.py")

# 작업 XML — 매일 10:00 시작, 2시간 간격 반복, 6시간 지속 (10:00, 12:00, 14:00, 16:00)
# StopAtDurationEnd=false: 16:00 이후엔 새 인스턴스 안 나비지만, 진행 중인 건 중단 안 함
TASK_XML = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>SK Hynix Report GitHub Actions trigger (every 2h during KST market hours)</Description>
    <Author>claude-test</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-08-04T10:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Repetition>
        <Interval>PT2H</Interval>
        <Duration>PT6H</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT2M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON}</Command>
      <Arguments>{SCRIPT}</Arguments>
      <WorkingDirectory>{SCRIPT_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def install():
    # 기존 작업 삭제 (있으면)
    _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    # XML 임시 파일 (UTF-16 LE BOM 필요 — schtasks /XML은 UTF-16 요구)
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".xml", delete=False, prefix="skhynix_"
    ) as f:
        f.write(b"\xff\xfe")  # UTF-16 LE BOM
        f.write(TASK_XML.encode("utf-16-le"))
        xml_path = f.name
    try:
        r = _run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"])
        if r.returncode == 0:
            print(f"[OK] Task '{TASK_NAME}' registered.")
            status()
        else:
            print(f"[ERROR] schtasks /Create failed (rc={r.returncode})")
            print("stdout:", r.stdout)
            print("stderr:", r.stderr)
            sys.exit(1)
    finally:
        os.unlink(xml_path)


def uninstall():
    r = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    if r.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
    else:
        print(f"[ERROR] Delete failed: {r.stdout} {r.stderr}")


def status():
    r = _run(["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"])
    if r.returncode != 0:
        print(f"[WARN] Task '{TASK_NAME}' not found.")
        return
    # 한국어/영어 무관 키워드 필터
    keep = ("TaskName", "작업 이름", "Status", "상태", "Next Run", "다음 실행",
            "Last Run", "최근 실행", "Schedule", "예약", "Last Result", "최근 결과")
    for line in r.stdout.splitlines():
        if any(k in line for k in keep):
            print(line.strip())


def test():
    """수동 1회 실행 — 등록된 작업을 즉시 트리거."""
    r = _run(["schtasks", "/Run", "/TN", TASK_NAME])
    if r.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' started manually.")
    else:
        print(f"[ERROR] Run failed: {r.stdout} {r.stderr}")
        # 폴백: trigger_workflow.py 직접 실행
        print("Fallback: running trigger_workflow.py directly...")
        r2 = _run([PYTHON, SCRIPT])
        print(r2.stdout)
        print(r2.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "uninstall", "status", "test"):
        print(__doc__)
        sys.exit(1)
    {"install": install, "uninstall": uninstall,
     "status": status, "test": test}[sys.argv[1]]()
