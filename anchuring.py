"""anchuring.py — run / seal / feed harness for chained Malbolge processes.

What it does, in plain words:

  1. RUN a Malbolge program to its halt, under a fixed step budget ("fuel").
  2. SEAL its output bytes with SHA-256.
  3. FEED those bytes as the standard input of the next program, but only
     after checking the seal. One flipped bit and the feed is rejected.

Every run is a fresh, ordinary Malbolge process: registers start at zero and
memory starts fresh from the program text. The only thing that ever crosses
from one process to the next is a sequence of output bytes, checked bit for
bit. Nothing is resumed; nothing is reinterpreted.

Commands:
  py anchuring.py run [--out PATH]       build the demo chain and seal it
  py anchuring.py verify FILE            replay a chain manifest, check hashes
  py anchuring.py tamper-demo FILE       show that a 1-bit change is rejected
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import malbolge
from gen_echo import gen_echo

FORMAT_ID = "malbolge-anchuring/1"
HERE = Path(__file__).resolve().parent
HELLO_FILE = "fixtures/hello.mal"
FUEL = 200_000


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_link(program_file: str, source: str, stdin_data: bytes) -> dict:
    status, steps, stdout = malbolge.run(source, stdin_data=stdin_data,
                                         max_steps=FUEL)
    return {
        "program_file": program_file,
        "program_sha256": sha256_hex(source.encode("latin-1")),
        "fuel": FUEL,
        "stdin_hex": stdin_data.hex(),
        "stdin_sha256": sha256_hex(stdin_data),
        "status": status,
        "steps": steps,
        "stdout_hex": stdout.hex(),
        "stdout_sha256": sha256_hex(stdout),
    }


def feed(sealed_sha256: str, payload: bytes):
    """The only gate between processes: exact hash or no entry."""
    if sha256_hex(payload) != sealed_sha256:
        return False
    return True


def build_chain() -> dict:
    hello_src = (HERE / HELLO_FILE).read_text(encoding="latin-1").strip()
    link0 = run_link(HELLO_FILE, hello_src, b"")
    payload = bytes.fromhex(link0["stdout_hex"])

    echo_src = gen_echo(len(payload))
    echo_file = f"fixtures/echo{len(payload)}.mal"
    (HERE / echo_file).write_text(echo_src, encoding="latin-1")

    ok = feed(link0["stdout_sha256"], payload)
    assert ok  # internal consistency: we sealed it ourselves
    link1 = run_link(echo_file, echo_src, payload)

    payload2 = bytes.fromhex(link1["stdout_hex"])
    ok2 = feed(link1["stdout_sha256"], payload2)
    assert ok2
    link2 = run_link(echo_file, echo_src, payload2)

    return {
        "format": FORMAT_ID,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "links": [link0, link1, link2],
    }


def verify(manifest: dict) -> list[str]:
    problems = []
    links = manifest.get("links", [])
    prev_out = None
    for i, link in enumerate(links):
        source = (HERE / link["program_file"]).read_text(encoding="latin-1")
        if sha256_hex(source.encode("latin-1")) != link["program_sha256"]:
            problems.append(f"link {i}: program file differs from sealed hash")
            continue
        stdin_bytes = bytes.fromhex(link["stdin_hex"])
        if sha256_hex(stdin_bytes) != link["stdin_sha256"]:
            problems.append(f"link {i}: recorded stdin fails its own seal")
        if i > 0 and sha256_hex(stdin_bytes) != prev_out:
            problems.append(f"link {i}: stdin does not match sealed stdout "
                            f"of link {i - 1}")
        recorded_stdout = bytes.fromhex(link["stdout_hex"])
        if sha256_hex(recorded_stdout) != link["stdout_sha256"]:
            problems.append(f"link {i}: recorded stdout fails its own seal")
        status, steps, stdout = malbolge.run(
            source, stdin_data=stdin_bytes, max_steps=link["fuel"])
        if status != link["status"] or steps != link["steps"]:
            problems.append(f"link {i}: replay diverged "
                            f"({status}/{steps} vs {link['status']}/{link['steps']})")
        if sha256_hex(stdout) != link["stdout_sha256"]:
            problems.append(f"link {i}: replayed stdout fails the seal")
        if stdout != recorded_stdout:
            problems.append(f"link {i}: replayed stdout differs byte-for-byte")
        prev_out = link["stdout_sha256"]
    return problems


def tamper_demo(manifest: dict) -> None:
    link0 = manifest["links"][0]
    payload = bytearray.fromhex(link0["stdout_hex"])
    print(f"sealed payload: {bytes(payload)!r}")
    original = link0["stdout_sha256"]
    payload[0] ^= 0x01
    if feed(original, bytes(payload)):
        print("1-bit tampered payload was ACCEPTED — this must never happen")
        sys.exit(1)
    print(f"1-bit tampered payload ({bytes(payload)!r}) -> REJECTED")

    # Second attack class: rewrite ONLY the recorded stdout_hex, leaving the
    # seal untouched. Before v1.1 the replay alone could still pass; now the
    # recorded bytes must match their own seal AND the replayed bytes.
    tampered = json.loads(json.dumps(manifest))
    hexed = bytearray.fromhex(tampered["links"][0]["stdout_hex"])
    hexed[0] ^= 0x01
    tampered["links"][0]["stdout_hex"] = hexed.hex()
    problems = verify(tampered)
    if not problems:
        print("edited stdout_hex went UNNOTICED by verify — must never happen")
        sys.exit(1)
    print(f"stdout_hex edited without re-sealing -> verify REJECTS "
          f"({problems[0]})")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "verify", "tamper-demo"):
        print(__doc__)
        return 2

    if sys.argv[1] == "run":
        out_path = HERE / "fixtures" / "chain_demo.json"
        if "--out" in sys.argv:
            out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        manifest = build_chain()
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for i, link in enumerate(manifest["links"]):
            print(f"link{i}: {link['program_file']} "
                  f"status={link['status']} steps={link['steps']} "
                  f"out={bytes.fromhex(link['stdout_hex'])!r}")
        print(f"chain sealed -> {out_path}")
        return 0

    manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT_ID:
        print(f"unknown format: {manifest.get('format')!r}")
        return 2

    if sys.argv[1] == "verify":
        problems = verify(manifest)
        if problems:
            for p in problems:
                print("MISMATCH:", p)
            return 1
        print(f"replay OK: {len(manifest['links'])} links, "
              f"all seals verified, deterministic")
        return 0

    tamper_demo(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
