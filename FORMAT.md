# Chain manifest format: `malbolge-anchuring/1`

A manifest is one UTF-8 JSON object:

```json
{
  "format": "malbolge-anchuring/1",
  "created_utc": "2026-09-06T00:00:00Z",
  "links": [ { ... }, { ... } ]
}
```

## Link fields

| field | meaning |
|---|---|
| `program_file` | path of the program, relative to the manifest |
| `program_sha256` | SHA-256 of the exact program bytes fed to the loader |
| `fuel` | maximum number of execution steps allowed |
| `stdin_hex` | exact stdin bytes this run received (hex) |
| `stdin_sha256` | SHA-256 of those bytes |
| `status` | `HALTED` · `OUT_OF_FUEL` · `INVALID` |
| `steps` | executed steps |
| `stdout_hex` | exact bytes emitted (hex) |
| `stdout_sha256` | SHA-256 of those bytes |

## Invariants a checker must enforce

1. For every link `i > 0`: `stdin_sha256[i] == stdout_sha256[i-1]`
   — the seal of each link's output gates entry into the next link.
2. Re-executing any link from its recorded program and stdin, with the
   recorded fuel, must reproduce `status`, `steps` and `stdout_sha256`
   exactly.
3. Every `*_sha256` field must match the bytes it describes.

A manifest violating any of these is not accepted, and there is no partial
acceptance: one flipped bit anywhere ends the check.

## Scope notes

- Fresh process per link: registers zeroed and memory rebuilt from the
  program text at every link. Only bytes travel.
- Timestamps (`created_utc`) are the only intentionally non-reproducible
  field; all execution fields are deterministic.
