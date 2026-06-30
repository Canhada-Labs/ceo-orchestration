---
name: embedded-firmware
description: >
  Governance and hard-rules for embedded firmware development on
  resource-constrained microcontrollers. Covers RTOS selection and task
  architecture (FreeRTOS / Zephyr / NuttX), MCU target selection across ESP32
  / STM32 / Nordic / RP2040, peripheral driver architecture with HAL
  abstraction, power-state hierarchy and current budgeting, dual-bank OTA
  update pipelines with signed verification and rollback, secure boot chain
  from ROM to application image, and MISRA-C / CERT-C compliance gating. Use
  when designing RTOS task hierarchies, implementing peripheral drivers,
  selecting a microcontroller, authoring or reviewing OTA update logic,
  hardening boot security, enforcing static-analysis gates, or debugging
  power-budget violations. Trigger list: new .c / .h driver file, RTOS task
  creation, OTA partition configuration, bootloader modification, power-mode
  state machine, or any ISR that communicates with application tasks.
owner: Embedded Firmware Engineer (domain persona)
tier: domain:embedded
scope_tags: [embedded, firmware, rtos, microcontroller, secure-boot, ota-updates, misra-c]
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-embedded-firmware-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: embedded
priority: 8
risk_class: medium
stack: [c, cpp, rust]
context_budget_tokens: 600
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/firmware/**"
  - "**/drivers/**"
  - "**/bootloader/**"
  - "**/ota/**"
  - "**/rtos/**"
  - "**/hal/**"
---

# Embedded Firmware

## Cardinal Rule

Every firmware image MUST be authored as though the target device will
be deployed in a physically adversarial environment, will never receive
manual intervention after shipment, and must survive power interruption
at any instruction boundary. Determinism, recoverability, and minimal
attack surface are non-negotiable invariants. Clever optimizations that
sacrifice any of these three properties are rejected regardless of
perceived performance benefit. A device that reboots cleanly from a
watchdog reset without corrupting persistent state is strictly more
valuable than a device that achieves lower average latency at the cost
of undefined behavior under edge conditions.

## Fail-Fast Rule

Stop and reject (do not proceed, do not patch around) if any of the
following conditions are detected during authoring or review:

- `malloc` or `new` is called from an ISR context or from any task
  declared as safety-critical after the initialization phase is complete.
- A blocking API (`vTaskDelay`, `osDelay`, `k_sleep`, or any variant with
  a non-zero timeout) is called from inside an interrupt handler.
- A FreeRTOS API without the `FromISR` suffix is called from an ISR.
- A shared variable between an ISR and a task is accessed without a
  critical section, `volatile` qualifier, or atomic intrinsic.
- An OTA binary is accepted without cryptographic signature verification
  against a root key stored in protected flash or eFuse.
- A debug port (JTAG, SWD, UART console) is enabled in a production
  firmware image without explicit eFuse lockdown or hardware fuse blow.
- A busy-wait polling loop with no timeout exists on a peripheral status
  register in production code.
- Firmware is compiled without a stack-guard canary on Cortex-M targets
  that support MPU stack overflow detection.

No exception is granted for "it's a prototype," "the peripheral is internal
only," or "we'll fix it before shipping." Fail-fast means stop-now.

## When to Apply

Apply this skill for any of the following triggers:

- Authoring a new MCU peripheral driver (UART, SPI, I2C, CAN, ADC, DAC,
  PWM, USB).
- Designing or modifying an RTOS task hierarchy: task creation, priority
  assignment, stack sizing, or inter-task communication primitives.
- Selecting or changing the target MCU family for a hardware platform.
- Writing or reviewing OTA update logic, partition tables, or bootloader
  chains.
- Configuring power modes, wake sources, or current-budget states.
- Adding or modifying secure-boot key provisioning, signature verification,
  or debug-port access control.
- Introducing static-analysis tooling (MISRA-C, CERT-C, PC-lint, clang-tidy)
  or modifying deviation justification records.
- Reviewing a pull request that changes any file under `components/`,
  `drivers/`, `bootloader/`, `partitions/`, or any linker script.

## Target Selection

Selection of a microcontroller family is an architectural decision that
constrains every subsequent layer. Cost is never the sole selection
criterion; cost-only selection deferred to procurement has historically
produced platforms incompatible with security or power requirements.

| Criterion | ESP32 (Xtensa LX6/LX7 or RISC-V) | STM32 (Cortex-M0+ to M7) | Nordic nRF52/nRF53/nRF91 (Cortex-M33/M4) | RP2040 (Dual Cortex-M0+) |
|---|---|---|---|---|
| Typical RAM | 520 KB (ESP32) to 8 MB (ESP32-S3 PSRAM) | 8 KB (G0) to 1 MB (H7) | 256 KB to 512 KB | 264 KB |
| Typical Flash | 4–16 MB (external SPI) | 32 KB to 2 MB (internal) | 512 KB to 1 MB (internal) | 2 MB (external QSPI) |
| Radio | Wi-Fi 802.11 b/g/n + BLE 5.0 (dual-core models) | None (requires external module) | BLE 5.4 + Thread/Zigbee/NFC (nRF52); LTE-M/NB-IoT (nRF91) | None |
| Power floor (deep sleep) | ~10 µA (ULP co-processor active) | ~300 nA (STANDBY + RTC) | ~1.3 µA (System OFF, RAM off) | ~180 µA (DORMANT, SRAM retained) |
| Security features | Secure Boot v2, Flash Encryption, eFuse, RSA/ECC in ROM | TrustZone-M (M23/M33), TAMP, RDP levels 0–2 | TrustZone-M, CryptoCell-312, APPROTECT eFuse, key slot in uICC | No TrustZone; OTP fuse row; software-only secure boot |
| RTOS fit | FreeRTOS (ESP-IDF default); Zephyr partial | FreeRTOS, Zephyr, ThreadX, bare-metal | Zephyr (nRF Connect SDK default); FreeRTOS supported | FreeRTOS (SDK default); bare-metal via PIO |
| Unit cost (2024 volume) | $1.50–$4.00 | $0.40–$8.00 | $2.50–$6.00 | $0.70–$1.00 |
| When to select | Connectivity-heavy IoT, prototyping, Wi-Fi + BLE co-existence | Hard-real-time control, motor drives, industrial, tight memory budget | Low-power BLE mesh, Thread, NB-IoT asset tracking, security-critical | Low-cost dual-core signal processing, USB HID, PIO peripheral emulation |

Decision gate: before committing to a target, verify all of the following
are satisfied: (a) RAM budget ≤ 70% of available RAM at steady-state;
(b) Flash budget ≤ 80% of available Flash including OTA swap partition;
(c) required radio standard is natively supported or a certified module
exists with a known BOM cost; (d) hardware security requirements (secure
boot, encrypted flash, debug lockdown) are met by the MCU's hardware
security engine, not by software alone.

## RTOS Discipline

| RTOS | Licensing | Scheduler | Primary use case | Key constraint |
|---|---|---|---|---|
| FreeRTOS | MIT | Preemptive priority-based | ESP-IDF, STM32, RP2040 | `FromISR` variants mandatory in ISR context; heap_4 or heap_5 only in production |
| Zephyr | Apache 2.0 | Preemptive + cooperative; configurable | Nordic nRF Connect SDK, multi-arch | Devicetree-first configuration; Kconfig must pin all driver options |
| NuttX | Apache 2.0 | POSIX-compliant preemptive | Aerospace, industrial POSIX compliance | POSIX syscall overhead; best fit when POSIX portability is a hard requirement |

Task design rules:

- Assign a unique, documented priority to every task. Priority inversion
  is a correctness defect, not a performance defect. Use priority
  inheritance mutexes (`configUSE_MUTEXES = 1` with
  `xSemaphoreCreateMutex()`) when a lower-priority task holds a resource
  required by a higher-priority task.
- Size every task stack empirically: deploy with
  `uxTaskGetStackHighWaterMark()` instrumentation enabled in the
  development build, capture the high-water mark under stress conditions,
  then set the production stack size to `high_water_mark + 25%` headroom,
  rounded up to the next 256-byte boundary. Never guess stack sizes.
- Never busy-wait in a task loop. Every `while(1)` body MUST include
  either a blocking queue receive, a semaphore take, an event group wait,
  or an explicit `vTaskDelay(pdMS_TO_TICKS(N))` with documented rationale
  for the chosen N.
- Use `xQueueSendFromISR` / `xSemaphoreGiveFromISR` to transfer data from
  interrupt context to task context. The ISR wakes the task; the task
  performs all non-trivial processing.
- Declare every inter-task shared variable `volatile` when accessed from
  both ISR and task context without a mutex or critical section. `volatile`
  prevents compiler optimization from caching the value in a register;
  it does not provide atomicity for multi-byte reads on Cortex-M0 targets
  where unaligned accesses are not atomic.

```c
/* FreeRTOS — canonical task + ISR handoff pattern */
#define SENSOR_TASK_STACK   2048U
#define SENSOR_TASK_PRIO    5U
#define SENSOR_QUEUE_DEPTH  8U

static QueueHandle_t s_sensor_queue;

/* ISR — deferred to task; no processing in ISR body */
void SENSOR_IRQHandler(void) {
    BaseType_t higher_prio_woken = pdFALSE;
    sensor_raw_t raw = sensor_read_raw_from_isr();
    xQueueSendFromISR(s_sensor_queue, &raw, &higher_prio_woken);
    portYIELD_FROM_ISR(higher_prio_woken);
}

static void sensor_task(void *arg) {
    (void)arg;
    sensor_raw_t raw;
    for (;;) {
        if (xQueueReceive(s_sensor_queue, &raw, pdMS_TO_TICKS(500)) == pdTRUE) {
            sensor_process(raw);
        }
        /* queue timeout handled gracefully; task yields on every iteration */
    }
}

void sensor_init(void) {
    s_sensor_queue = xQueueCreate(SENSOR_QUEUE_DEPTH, sizeof(sensor_raw_t));
    configASSERT(s_sensor_queue != NULL);
    xTaskCreate(sensor_task, "sensor", SENSOR_TASK_STACK, NULL,
                SENSOR_TASK_PRIO, NULL);
}
```

## Peripheral Driver Architecture

Peripheral drivers MUST be layered: a hardware-abstraction layer (HAL)
exposes a target-independent interface; a platform-specific implementation
satisfies that interface for each MCU family. The application layer calls
only the HAL interface. This constraint enables unit testing on host
(with a mock HAL) and simplifies porting to a new MCU variant.

Interrupt vs. polling selection:

| Transfer mode | When to use | Constraint |
|---|---|---|
| Polling | Initialization sequences only; one-time blocking transfers during boot where RTOS is not yet running | Never in production RTOS task loops; constitutes a busy-wait |
| Interrupt-driven | Single-byte or small-frame transfers where DMA setup overhead exceeds transfer time | ISR body MUST be minimal; queue or semaphore to wake task |
| DMA | Streaming data: SPI display frames, audio, large ADC bursts, UART at >115200 baud | DMA descriptor buffer MUST be in non-cached RAM or cache-coherence invalidation MUST be explicit (Cortex-M7 SCB_CleanInvalidateDCache_by_Addr) |

ISR-safe operations are restricted to: reading/writing hardware registers,
pushing to a queue via `FromISR` variant, giving a semaphore via
`FromISR` variant, setting an event bit via `FromISR` variant, and
calling `portYIELD_FROM_ISR` at exit. Everything else belongs in a task.

Ring buffer pattern for streaming peripherals:

```c
/* ISR-safe ring buffer — power-of-two size for masking */
#define RING_BUF_SIZE  256U   /* must be power of two */
#define RING_BUF_MASK  (RING_BUF_SIZE - 1U)

typedef struct {
    volatile uint8_t buf[RING_BUF_SIZE];
    volatile uint32_t head;   /* written by ISR */
    volatile uint32_t tail;   /* read by task   */
} ring_buf_t;

static inline bool ring_buf_push(ring_buf_t *rb, uint8_t byte) {
    uint32_t next_head = (rb->head + 1U) & RING_BUF_MASK;
    if (next_head == rb->tail) { return false; } /* full — drop byte; caller handles */
    rb->buf[rb->head] = byte;
    rb->head = next_head;
    return true;
}

static inline bool ring_buf_pop(ring_buf_t *rb, uint8_t *out) {
    if (rb->head == rb->tail) { return false; } /* empty */
    *out = rb->buf[rb->tail];
    rb->tail = (rb->tail + 1U) & RING_BUF_MASK;
    return true;
}
```

## Power Management

Power management is a first-class design requirement, not a post-shipment
optimization. Current budgets MUST be defined per system state before
hardware selection is finalized. A device that cannot meet its power
budget in the selected sleep mode requires an MCU change, not a software
workaround.

| State | Description | Typical current (target-dependent) | Wake latency |
|---|---|---|---|
| Active (full speed) | CPU running, all peripherals clocked | 30–300 mA | — |
| Idle / tickless | CPU halted (WFI), peripherals retained, systick gated | 1–10 mA | <1 ms |
| Light sleep | CPU halted, SRAM retained, clocks gated, select peripherals powered | 50–800 µA | 1–5 ms |
| Deep sleep | CPU halted, SRAM partially retained (configurable), RTC running, most clocks off | 5–50 µA | 5–50 ms |
| Hibernate / System OFF | No SRAM retention (or minimal via RAM retention bitmask), RTC or GPIO wake only | 0.1–5 µA | Full reboot sequence |

Wake source mapping MUST be documented before enabling any sleep mode.
Undocumented wake sources produce phantom resets that are indistinguishable
from watchdog resets in the field. Required wake-source documentation:

1. Source (GPIO pin, RTC alarm, UART break, radio event, WDT).
2. Polarity or threshold (rising edge, level, timeout value).
3. Required peripheral state before sleep entry (GPIO pull, UART CTS).
4. Expected wake latency and effect on pending transactions.

Power budget verification: measure idle, light-sleep, and deep-sleep
currents on production PCB (not devkit) using a shunt resistor or
precision current probe. Compare against budget. If deep-sleep current
exceeds budget by >20%, audit leakage sources: GPIO floating inputs,
active pull-ups on I2C lines, LDO quiescent current, peripheral power
rails not gated by a load switch.

## OTA Update Pipeline

Firmware updates in the field MUST be atomic and recoverable. A device
that can be left in an unbootable state by a power interruption during
OTA is a field-support liability and, in safety-critical applications,
a hazard.

Required pipeline elements:

1. **Dual-bank (A/B) flash partition**: the running image occupies one
   bank; the incoming image is written to the inactive bank. The active
   bank is never erased until the new image is verified and the swap
   is committed.
2. **Signed binary verification**: the OTA client MUST verify the incoming
   image signature against a public key stored in write-protected flash
   (ESP32 eFuse, STM32 option bytes RDP Level 2, Nordic UICR APPROTECT)
   before writing a single byte to the inactive bank. Verification MUST
   occur after full download, not during streaming write.
3. **Integrity check**: verify CRC-32 or SHA-256 of the complete received
   image before marking it bootable. Hash MUST cover the full binary
   including the header, not just the payload.
4. **Rollback on watchdog reset**: if the newly booted image fails to
   call `ota_mark_valid()` within a configurable window (default: 60
   seconds after first successful boot), the bootloader MUST revert to
   the previous image on next reset. This window MUST be enforced by
   the watchdog timer, not by application-layer logic alone.
5. **Partial-image fallback**: if a download is interrupted, the
   incomplete image MUST be discarded and the device MUST remain on the
   current image. Do not mark an image bootable unless its full hash
   has been verified.

```c
/* Canonical OTA commit gate — called after smoke-test passes */
esp_err_t ota_commit_and_validate(void) {
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t state;
    if (esp_ota_get_state_partition(running, &state) != ESP_OK) {
        return ESP_ERR_NOT_FOUND;
    }
    if (state == ESP_OTA_IMG_PENDING_VERIFY) {
        /* Smoke test passed — mark image valid; WDT rollback window closes */
        return esp_ota_mark_app_valid_cancel_rollback();
    }
    return ESP_OK;  /* already valid; not a pending-verify boot */
}
```

## Secure Boot

Secure boot establishes a cryptographic chain of trust from hardware ROM
through the bootloader to the application image. Every link in the chain
MUST be verified before execution is transferred to the next stage.

Root-of-trust chain (generic Cortex-M with hardware security engine):

```
ROM (immutable, manufacturer-signed)
  └─> Stage 1 bootloader (vendor ROM verifies hash/sig against OTP)
        └─> Stage 2 / MCUboot (signed with OEM key stored in eFuse/HSM)
              └─> Application image (signed with OEM key; version counter enforced)
```

Key provisioning requirements:

- **Manufacturer key vs. OEM key separation**: the MCU manufacturer's
  ROM-level key is distinct from the OEM application signing key. Both
  must be valid for the respective verification stage. Conflating them
  (e.g., reusing the same key pair for ROM trust anchor and application
  signing) eliminates the ability to rotate the OEM key without replacing
  hardware.
- **Key revocation**: maintain a monotonic rollback-prevention counter
  (anti-rollback counter) in eFuse or secure storage. Reject any image
  whose version counter is below the committed minimum. This prevents
  downgrade attacks to a previously valid but now-patched image.
- **Debug-port lockdown**: disable JTAG/SWD in production by blowing the
  appropriate eFuse (ESP32 `JTAG_DISABLE` eFuse, STM32 RDP Level 2,
  Nordic `APPROTECT` + `SECUREAPPROTECT`). Debug access MUST NOT be
  re-enabled by firmware update; hardware fuse blow is irreversible by
  design.
- **Manufacturing mode separation**: the manufacturing firmware image used
  for factory test MUST NOT be the same binary signed for production. The
  manufacturing image MUST be blocked from booting in the field by a
  separate eFuse bit or a signed manifest that the production bootloader
  explicitly rejects.

## MISRA-C / CERT-C Compliance

MISRA-C:2012 is the baseline standard for safety-critical firmware (IEC
61508, ISO 26262, IEC 62443). CERT-C provides complementary coverage for
defensive coding and undefined-behavior avoidance. Both are enforced by
static-analysis gate in CI.

Minimum mandatory rule subset for firmware in this framework:

| Rule class | MISRA-C:2012 | CERT-C | Enforcement |
|---|---|---|---|
| No implicit type conversions on arithmetic | Rule 10.1–10.8 | INT02-C, FLP36-C | clang-tidy `bugprone-implicit-widening-of-multiplication-result` |
| No dynamic memory allocation after init | Rule 21.3 | MEM31-C, MEM34-C | custom lint rule; heap_4/heap_5 `configAPPLICATION_ALLOCATED_HEAP` + static guard |
| No recursion | Rule 17.2 | MEM05-C | clang-tidy `-Wrecursion`; forbidden in ISR and RTOS tasks |
| Single-point `break` / `continue` | Rule 15.5 | — | clang-tidy |
| All switch cases covered + default | Rule 16.1–16.4 | MSC01-C | `-Wswitch-enum` + `-Wswitch-default` |
| No undefined behavior arithmetic | Rules 12.1, 12.2 | INT32-C, INT34-C | UBSan in test builds; sanitizer findings block merge |
| Pointer arithmetic bounds | Rule 18.1, 18.2 | ARR30-C, ARR38-C | clang-tidy `bounds` module |
| No uninitialized variables | Rule 9.1 | EXP33-C | `-Wuninitialized`; `-Wmaybe-uninitialized` |

Deviation justification protocol: any deviation from a mandatory MISRA-C
rule MUST be documented in a deviation record that includes: (a) rule
identifier, (b) file and line range, (c) justification citing the
specific constraint that makes compliance impossible or the evidence that
the deviation introduces no safety risk, (d) reviewer sign-off. Deviations
without records are treated as violations.

## Memory Discipline

Memory discipline in embedded firmware is stricter than in general systems
programming because there is no OS memory protection, no swap space, and
no recovery mechanism other than a watchdog reset.

- Do not call `malloc`, `free`, `realloc`, `calloc`, or `new`/`delete`
  in ISR context under any circumstances. These functions are not
  reentrant with respect to interrupt context.
- Do not use dynamic allocation in safety-critical task paths after the
  system initialization phase is complete. "Initialization phase complete"
  MUST be a defined, testable condition: a flag set after all tasks are
  created and all buffers are allocated.
- Use FreeRTOS static allocation APIs (`xTaskCreateStatic`,
  `xQueueCreateStatic`, `xSemaphoreCreateMutexStatic`) for all objects
  in safety-critical code paths. Static allocation eliminates heap
  fragmentation and provides deterministic allocation at compile time.
- Enable stack-coloring debug (FreeRTOS `configCHECK_FOR_STACK_OVERFLOW = 2`)
  in development builds. The hook `vApplicationStackOverflowHook` MUST
  log a fatal breadcrumb and trigger a controlled reset.
- Heap fragmentation diagnostics: in products that use dynamic allocation
  during initialization, measure `xPortGetFreeHeapSize()` and
  `xPortGetMinimumEverFreeHeapSize()` at steady state. If minimum-ever
  falls below 15% of total heap, the allocation strategy must be reviewed.

## Anti-patterns

| Pattern | Why wrong | What to do instead |
|---|---|---|
| Blocking call inside ISR (`vTaskDelay`, `osDelay`, etc.) | Corrupts RTOS scheduler state; produces hard fault or priority inversion on most RTOSes | Defer work to a task via queue or semaphore `FromISR` variant; ISR body executes in <1 µs |
| Unprotected shared variable between ISR and task | Compiler may cache value in register; multi-byte reads non-atomic on Cortex-M0 | Declare `volatile`; use critical section (`taskENTER_CRITICAL`) or atomic intrinsic for multi-byte values |
| Busy-wait polling loop in production task | Starves lower-priority tasks; masks real-time deadlines; inflates power consumption | Use interrupt-driven or DMA transfer; blocking queue receive with timeout for polling fallback |
| OTA flash write without prior signature verification | Malicious or corrupted image flashed and booted; no recovery without physical access | Verify full image signature and hash against root key before writing first byte to inactive partition |
| Unsigned production firmware image | Attacker can reflash via OTA or debug port with arbitrary code; secure boot provides no protection if OTA client accepts unsigned binaries | Sign every image with OEM private key; OTA client rejects images failing signature check unconditionally |
| Debug port (JTAG/SWD) enabled in production | Full read/write access to RAM, Flash, and peripheral registers at runtime; bypasses all software security | Blow irreversible eFuse at end-of-line test; document in manufacturing procedure; verify with automated test fixture |
| `malloc` called from safety-critical task after boot | Heap fragmentation over time; non-deterministic allocation latency; potential allocation failure with no recovery path | Pre-allocate all buffers during initialization; use static allocation APIs for all RTOS objects |
| Stack size hard-coded without measurement | Stack overflow corrupts adjacent memory silently on targets without MPU | Instrument with `uxTaskGetStackHighWaterMark()`; size at measured peak + 25% headroom |
| GPIO floating input during sleep | Leakage current through the input buffer; prevents reaching advertised sleep current floor | Explicitly configure unused GPIOs as output-low or input with pull-down before sleep entry |
| Mixing HAL and LL peripheral access in the same driver | HAL state machine and LL register writes conflict; produces undefined peripheral state on re-init | Choose one abstraction level per peripheral and document the choice in the driver header |

## Cross-References

- `core/security-and-auth` — Key lifecycle management, certificate
  provisioning, and OWASP secure-coding patterns apply to the host-side
  OTA server and device management backend. The OTA transport channel
  MUST use TLS 1.2+ with certificate pinning; the same certificate
  lifecycle discipline from `core/security-and-auth` governs rotation
  and revocation. ADR-052 VETO floor applies to security review of OTA
  and secure-boot implementation.

- `core/code-review-checklist` — The two-pass review protocol from
  ADR-058 applies to all firmware pull requests touching OTA logic,
  secure boot, or cryptographic key handling. Pass 1 reviews structure
  (task architecture, driver layering, partition layout). Pass 2 is
  adversarial (ISR safety, shared-variable races, memory discipline,
  OTA bypass vectors).

- `core/architecture-decisions` — MCU family selection, RTOS choice,
  and OTA pipeline design are L3 architectural decisions requiring a
  formal ADR. Any deviation from the MISRA-C deviation protocol requires
  an ADR documenting the rule, justification, and sign-off.

## ADR Anchors

- **ADR-052** (`multi-model-dispatch-by-role`): Security review of OTA
  pipeline, secure boot configuration, and debug-port lockdown is subject
  to the VETO floor defined in ADR-052. The security-engineer archetype
  flagged `veto_floor: true` MUST approve before any OTA or secure-boot
  change is merged. Code-reviewer approval alone is insufficient for
  security-scoped changes.

- **ADR-058** (`brainstorm-gate-and-two-pass-review`): All firmware
  changes that modify OTA logic, cryptographic key handling, ISR
  communication patterns, or power-state transitions MUST complete a
  two-pass review. Pass 1 is structural; Pass 2 is adversarial. The two
  passes MUST be documented as distinct review rounds, not merged.
