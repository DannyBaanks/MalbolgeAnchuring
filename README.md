# malbolge-anchuring

Certified state transfer between finite Malbolge processes. Run one program
to its halt, seal its output with SHA-256, and feed those bytes to the next
program — but only if the seal matches, bit for bit.

```
hello.mal  ──run──▶  "Hello World!"  ──seal──▶  sha256
                                                │  checked
                                                ▼
echo12.mal ──run──▶  "Hello World!"  ◀──feed──  (stdin)
```

Everything here is plain, single-machine Classic Malbolge. Each program runs
on a fresh interpreter (registers zeroed, memory rebuilt from the program
text). The only thing that crosses between two processes is a string of
bytes, verified bit-exact before it is accepted.

## Quickstart

```bash
# build the demo chain and seal it
py anchuring.py run
```
```
link0: fixtures/hello.mal status=HALTED steps=40 out=b'Hello World!'
link1: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'
link2: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'
chain sealed -> fixtures/chain_demo.json
```

```bash
# replay the whole manifest, re-checking every hash and every run
py anchuring.py verify fixtures/chain_demo.json
```
```
replay OK: 3 links, all seals verified, deterministic
```

```bash
# show that a 1-bit change is rejected
py anchuring.py tamper-demo fixtures/chain_demo.json
```
```
sealed payload: b'Hello World!'
1-bit tampered payload (b'Iello World!') -> REJECTED
```

Python 3.10+. No dependencies.

## The pieces

| file | what it is |
|---|---|
| `malbolge.py` | self-contained Classic Malbolge interpreter (public 1998/2005 semantics), nothing to install |
| `anchuring.py` | the harness: run, seal, feed, verify, tamper-demo |
| `gen_echo.py` | generator for straight-line `[in, out]×n + halt` programs |
| `fixtures/` | the demo chain manifest and its programs |
| `FORMAT.md` | the chain manifest format (`malbolge-anchuring/1`), field by field |

## What this demonstrates

- **Bit-exact transport.** The bytes one process emits are delivered to the
  next one unchanged, and the manifest proves it (`stdin_sha256` of each link
  equals `stdout_sha256` of the previous one).
- **Tamper evidence.** Flip one bit of a sealed payload and feeding is
  rejected before the next program ever runs.
- **Deterministic replay.** Every link in a sealed manifest can be
  re-executed from scratch and reproduces status, step count and output
  exactly. `verify` does this.
- **A hard per-process budget.** Every process runs with a fixed step
  allowance ("fuel"). If the allowance runs out first, the status is
  `OUT_OF_FUEL`, not a halt:

  ```
  fuel=10 on hello.mal -> status=OUT_OF_FUEL steps=10 out=b'Hel'
  ```

## What this does NOT do or claim

- **It is not process resumption.** Each link is a brand-new Malbolge
  process. Nothing serializes a machine mid-run; registers and memory start
  fresh every time. Only output bytes move.
- **It is not a Turing-completeness device, and no such claim is made.**
  Every link is a finite computation with a finite budget, and a chain with a
  fixed budget per link can only carry payloads of bounded size — a fixed
  composition of finite maps over a bounded payload space is itself a finite
  iteration. Anchuring changes *who vouches for the bytes*, not what a single
  Malbolge process can compute.
- **It is not multi-interpreter arbitrage.** One reference interpreter is
  included so results are reproducible out of the box; checking the same
  fixtures against other implementations is left to the reader.

## Semantics notes

- Classic Malbolge, 59049 cells, 10-trit `crazy`/`rotate`, self-encryption
  after each executed instruction.
- On end-of-input, `a` becomes `59048` (the original 1998 interpreter's
  behavior). None of the bundled fixtures ever reach EOF, so this choice
  cannot affect any included result — but cross-implementation comparisons
  should state their EOF convention, because interpreters diverge here.

## Reproduce from zero

```bash
py anchuring.py run            # writes fixtures/chain_demo.json + echo12.mal
py anchuring.py verify fixtures/chain_demo.json
py anchuring.py tamper-demo fixtures/chain_demo.json
```

Deleting `fixtures/chain_demo.json` and re-running `run` regenerates the
identical manifest except for the `created_utc` timestamp.

## License

MIT
