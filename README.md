# Malbolge Anchuring v2.0 — Transferencia Determinista Hash-Linked entre Procesos Malbolge

[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](https://github.com/DannyBaanks/MalbolgeAnchuring)
[![Deterministic](https://img.shields.io/badge/transfer-SHA--256%20hash--linked-brightgreen.svg)]()

Transferencia determinista hash-linked entre procesos finitos de Malbolge. Corre un
programa hasta su halt, sella su output con SHA-256, y alimenta esos bytes al
siguiente programa — pero solo si el sello concuerda, bit por bit.

Parte de la **Suite Experimental de Macroestados y Épocas v2.0** del ecosistema Malbolge de ISyCo.

```
hello.mal  ──corre──▶  "Hello World!"  ──sella──▶  sha256
                                                │  verificado
                                                ▼
echo12.mal ──corre──▶  "Hello World!"  ◀──alimenta──  (stdin)
```

Todo aqui es Malbolge Clasico plain, de maquina unica. Cada programa corre
en un interprete nuevo (registros a cero, memoria reconstruida desde el texto
del programa). Lo unico que cruza entre dos procesos es una cadena de
bytes, verificado bit-exact antes de ser aceptado.

## Quickstart

```bash
# construir la demo chain y sellarla
py anchuring.py run
```
```
link0: fixtures/hello.mal status=HALTED steps=40 out=b'Hello World!'
link1: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'
link2: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'
chain sealed -> fixtures/chain_demo.json
```

```bash
# re-ejecutar todo el manifest, re-verificando cada hash y cada run
py anchuring.py verify fixtures/chain_demo.json
```
```
replay OK: 3 links, todos los sellos verificados, deterministico
```

```bash
# mostrar que un cambio de 1 bit es rechazado
py anchuring.py tamper-demo fixtures/chain_demo.json
```
```
sealed payload: b'Hello World!'
1-bit tampered payload (b'Iello World!') -> REJECTED
stdout_hex edited without re-sealing -> verify REJECTS (link 0: stdout registrado falla su propio sello)
```

Python 3.10+. Sin dependencias.

## Los piezas

| archivo | que es |
|---|---|
| `malbolge.py` | interprete de Malbolge Clasico autosuficiente (semantica publica 1998/2005), nada que instalar |
| `anchuring.py` | el harness: correr, sellar, alimentar, verificar, tamper-demo |
| `gen_echo.py` | generador para programas straight-line `[in, out]×n + halt` |
| `fixtures/` | el manifest de la demo chain y sus programas |
| `FORMAT.md` | el formato del manifest de chain (`malbolge-anchuring/1`), campo por campo |

## Que demuestra esto

- **Transport bit-exact.** Los bytes que un proceso emite se entregan al
  siguiente sin cambios, y el manifest lo demuestra (`stdin_sha256` de cada link
  es igual a `stdout_sha256` del anterior).
- **Evidencia de tamper.** Voltea un bit de un payload sellado y la alimentacion es
  rechazada antes de que el siguiente programa siquiera corra.
- **Replay deterministico.** Cada link en un manifest sellado puede ser
  re-ejecutado desde cero y reproduce status, conteo de pasos y output
  exactamente. `verify` hace esto.
- **Presupuesto duro por proceso.** Cada proceso corre con un allowance fijo de pasos
  ("fuel"). Si el allowance se agota primero, el status es
  `OUT_OF_FUEL`, no un halt:

  ```
  fuel=10 on hello.mal -> status=OUT_OF_FUEL steps=10 out=b'Hel'
  ```

## Que esto NO hace ni reclama

- **No es reanudacion de procesos.** Cada link es un proceso de Malbolge
  completamente nuevo. Nada serializa una maquina a mitad de ejecucion; registros y memoria empiezan
  frescos cada vez. Solo los bytes de output se mueven.
- **No es un dispositivo de Turing-completeness, y no se hace tal reclamo.**
  Cada link es una computacion finita con un presupuesto finito, y una cadena con un
  presupuesto fijo por link solo puede transportar payloads de tamano acotado — una composicion finta
  de mapas finitos sobre un espacio de payload acotado es ella misma una
  iteracion finita. Anchuring cambia *quien avala los bytes*, no lo que un solo
  proceso de Malbolge puede computar.
- **No es arbitraje multi-interprete.** Un interprete de referencia se
  incluye para que los resultados sean reproducibles out of the box; verificar los mismos
  fixtures contra otras implementaciones se le deja al lector.
- **Los sellos dan integridad, no autenticidad.** SHA-256 detecta cualquier cambio
  que no actualice el sello correspondiente — pero un atacante que pueda
  reescribir un manifest completo puede reemplazar tanto payload como hash y crear un
  manifest diferente y auto-consistente. Por eso el termino preciso es
  *transferencia determinista hash-linked*, no "certificado". Si "certificado" alguna vez
  necesita significar "producido por X y insustituible por nadie", el manifest
  (o un root hash de el) debe ser *firmado*, ej. con Ed25519. Deliberadamente
  fuera de alcance aqui.

## Notas de semantica

- Malbolge Clasico, 59049 celdas, `crazy`/`rotate` de 10 trits, auto-encriptacion
  despues de cada instruccion ejecutada.
- El loader impone la validacion original de 1998 en tiempo de carga: cada caracter
  de programa debe ser ASCII imprimible *y*, en su posicion de carga, debe decodificar a
  una de las ocho instrucciones (`(ord(ch) + pos) % 94 ∈
  {4, 5, 23, 39, 40, 62, 68, 81}`); programas de mas de 59049 celdas se
  rechazan de plano.
- En fin de input, `a` se convierte en `59048` (el comportamiento del interprete original 1998).
  Ninguno de los fixtures empaquetados llega a EOF, asi que esta eleccion
  no puede afectar ningun resultado incluido — pero comparaciones cross-implementation
  deben declarar su convencion de EOF, porque los interpretes divergen aqui.

## Reproducir desde cero

```bash
py anchuring.py run            # escribe fixtures/chain_demo.json + echo12.mal
py anchuring.py verify fixtures/chain_demo.json
py anchuring.py tamper-demo fixtures/chain_demo.json
```

Borrar `fixtures/chain_demo.json` y re-ejecutar `run` regenera el
manifest identico excepto por el timestamp `created_utc`.

## Licencia

MIT
