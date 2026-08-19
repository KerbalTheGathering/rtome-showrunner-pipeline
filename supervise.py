"""Run a resumable batch under a ComfyUI that sometimes dies mid-render.

AN INTERMITTENT CRASH YOU CANNOT PREVENT IS ONE YOU PLAN AROUND. A video
model hard-aborted the server (`Fatal Python error: Aborted`, sampler step 0)
roughly one run in four, on BOTH attention backends, with no pattern — shot
09 died on sage and rendered on pytorch, shot 40 died on pytorch and rendered
on sage minutes later. Hand-driving that batch cost five to ten minutes per
crash to notice, diagnose and relaunch, three times over, which is what ran
the night out. Supervised, the same work finished with zero failures.

WHY THIS CAN BE SIMPLE: EVERY BATCH TOOL IN THIS REPO IS RESUMABLE. Each one
skips work already on disk, so the supervisor does not orchestrate items — it
re-runs the whole COMMAND after a crash and only the item that was in flight
is redone. If you are wrapping a tool that is not resumable, fix that first;
a supervisor over a tool that restarts from zero is a loop that bills you for
the same work until the crash lands on the last item.

WHAT IT DOES, per attempt: health-check the server; launch one if none
answers; run the command; on a nonzero exit, check the server again — if it
died, that was a crash, so relaunch **on the other attention backend** (both
crash and both work; whichever just died is the one not to pick again) and go
round. `--max-restarts` caps it.

OWNERSHIP RULES, learned on a shared card:
  * An instance that already answers is USED, never restarted, never killed.
    Someone's render may be behind it.
  * PIDs this tool launches are written to `_locks/supervise_comfyui.pids`.
    `--stop` kills ONLY those, refuses while the queue is non-empty, and then
    prints `nvidia-smi` — **the driver's number is the evidence of teardown.**
    The `/free` endpoint returns 200 without returning VRAM, and a launcher's
    exit code describes the wrapper, not the process.

    python supervise.py -- python h3_shoot.py
    python supervise.py --max-restarts 5 -- python gen_still.py
    python supervise.py --stop
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import season_paths                                                # noqa: E402
import solo                                                       # noqa: E402

PIDFILE = os.path.join(HERE, "_locks", "supervise_comfyui.pids")
LOG = os.path.join(HERE, "_locks", "supervise_comfyui.log")

# Both crash and both work; the point of listing them is alternation.
BACKENDS = ["--use-sage-attention", "--use-pytorch-cross-attention"]
LAUNCH_WAIT_S = 450


def up(timeout: float = 4.0) -> bool:
    try:
        urllib.request.urlopen(f"{season_paths.COMFY_URL}/system_stats",
                               timeout=timeout).read()
        return True
    except Exception:                                            # noqa: BLE001
        return False


def queue_len() -> int | None:
    try:
        q = json.load(urllib.request.urlopen(
            f"{season_paths.COMFY_URL}/queue", timeout=6))
        return len(q["queue_running"]) + len(q["queue_pending"])
    except Exception:                                            # noqa: BLE001
        return None


def launch(backend: str) -> None:
    py = os.path.join(season_paths.COMFY, ".venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = sys.executable
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    p = subprocess.Popen(
        [py, "main.py", backend], cwd=season_paths.COMFY,
        stdout=open(LOG, "ab"), stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    with open(PIDFILE, "a", encoding="utf-8") as fh:
        fh.write(f"{p.pid}\n")
    print(f"  launched ComfyUI {backend} (wrapper pid {p.pid}, "
          f"log {LOG})", flush=True)
    t0 = time.time()
    while time.time() - t0 < LAUNCH_WAIT_S:
        if up():
            print(f"  server up after {time.time()-t0:.0f}s", flush=True)
            return
        time.sleep(5)
    sys.exit(f"FAIL: server did not answer within {LAUNCH_WAIT_S}s -- "
             f"read {LOG}")


def stop() -> int:
    n = queue_len()
    if n:
        sys.exit(f"FAIL: queue has {n} job(s) -- not killing a server with "
                 f"work in it. Wait, or clear the queue first.")
    pids = []
    if os.path.exists(PIDFILE):
        pids = [int(x) for x in open(PIDFILE, encoding="utf-8").read().split()
                if x.strip().isdigit()]
    if not pids:
        print("  nothing recorded as launched by this tool; not touching "
              "whatever is running")
        return 0
    for pid in pids:
        if solo._alive(pid):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"]
                           if os.name == "nt" else ["kill", "-9", str(pid)],
                           capture_output=True)
            print(f"  killed {pid}")
    os.remove(PIDFILE)
    # THE DRIVER'S NUMBER IS THE EVIDENCE, not this tool's bookkeeping.
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.free",
                          "--format=csv,noheader"],
                         capture_output=True, text=True)
    print(f"  nvidia-smi: {out.stdout.strip() or '(unavailable)'}")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if "--stop" in argv:
        return stop()
    max_restarts = 3
    if "--max-restarts" in argv:
        i = argv.index("--max-restarts")
        max_restarts = int(argv[i + 1])
        del argv[i:i + 2]
    if "--" not in argv:
        sys.exit(__doc__.strip().splitlines()[0]
                 + "\n  usage: supervise.py [--max-restarts N] -- <command>"
                 "\n         supervise.py --stop")
    cmd = argv[argv.index("--") + 1:]
    if not cmd:
        sys.exit("FAIL: nothing after --")

    bi, restarts = 0, 0
    while True:
        if not up():
            launch(BACKENDS[bi])
        print(f"  running: {' '.join(cmd)}", flush=True)
        rc = subprocess.run(cmd).returncode
        if rc == 0:
            print("  command finished clean", flush=True)
            return 0
        crashed = not up()
        print(f"  command exited {rc}"
              + (" and the server is DOWN -- that was a crash" if crashed
                 else " with the server still up -- a real failure, not a "
                      "crash; not retrying"), flush=True)
        if not crashed:
            return rc
        restarts += 1
        if restarts > max_restarts:
            sys.exit(f"FAIL: {restarts - 1} restarts spent. The crash is not "
                     f"intermittent at this rate -- stop and diagnose.")
        bi = (bi + 1) % len(BACKENDS)
        print(f"  restart {restarts}/{max_restarts}, switching to "
              f"{BACKENDS[bi]}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
