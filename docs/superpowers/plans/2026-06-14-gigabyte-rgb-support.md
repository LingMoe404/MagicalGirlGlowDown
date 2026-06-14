# Gigabyte RGB Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe idle blackout and exact restoration for Gigabyte motherboard, 5V ARGB, and 12V RGB zones exposed by the locally installed GCC package.

**Architecture:** Generalize the Python brightness service into an opaque lighting-target service, then add a Python client for a source-built .NET helper. The helper loads GCC assemblies from their installed locations, performs read-only discovery first, and permits writes only for a validated motherboard fingerprint and explicit zone set; GCC process detection pauses this backend without pausing Nollie controllers.

**Tech Stack:** Python 3.12.10, asyncio, pytest, PySide6, psutil, .NET 10 C#, System.Text.Json, reflection over locally installed GCC assemblies.

---

## File Structure

- `src/magical_girl_glow_down/lighting.py`: generic target identity, opaque snapshot, and target protocol.
- `src/magical_girl_glow_down/service.py`: transactional dim/restore orchestration for all lighting targets.
- `src/magical_girl_glow_down/storage.py`: version-2 mixed target snapshot persistence and version-1 migration.
- `src/magical_girl_glow_down/gigabyte.py`: helper discovery, JSON client, Gigabyte target adapter, and error mapping.
- `src/magical_girl_glow_down/app_guard.py`: independent NollieRGB and GCC process guards.
- `src/magical_girl_glow_down/tray.py`: backend lifecycle, GCC pause behavior, and combined status.
- `src/magical_girl_glow_down/main.py`: safe Gigabyte probe/snapshot CLI commands.
- `helper/MagicalGirlGlowDown.GigabyteHelper/`: isolated .NET console helper.
- `helper/MagicalGirlGlowDown.GigabyteHelper.Tests/`: fake-adapter unit tests with no hardware access.
- `tests/test_lighting.py`: generic snapshot model tests.
- `tests/test_service.py`: mixed-backend orchestration tests.
- `tests/test_storage.py`: persistence migration and opaque state tests.
- `tests/test_gigabyte.py`: Python/helper protocol tests.
- `tests/test_app_guard.py`: GCC ownership tests.
- `tests/test_tray_worker.py`: worker policy tests without Qt event-loop hardware access.
- `docs/gigabyte-validation.md`: staged read-only and hardware acceptance commands.

### Task 1: Introduce Generic Lighting Targets

**Files:**
- Create: `src/magical_girl_glow_down/lighting.py`
- Modify: `src/magical_girl_glow_down/domain.py`
- Modify: `src/magical_girl_glow_down/protocol.py`
- Modify: `tests/fakes.py`
- Create: `tests/test_lighting.py`

- [ ] **Step 1: Write failing model and adapter tests**

```python
def test_snapshot_round_trip() -> None:
    snapshot = LightingSnapshot(
        identity=TargetIdentity("nollie", "Nollie16:ABC"),
        state={"canvases": [30, 80]},
        pending_restore=True,
    )
    assert LightingSnapshot.from_dict(snapshot.to_dict()) == snapshot


async def test_nollie_target_uses_brightness_state() -> None:
    target = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    state = await target.snapshot()
    await target.blackout(state)
    assert target.state == {"canvases": [0]}
    await target.restore(state)
    assert target.state == {"canvases": [30]}
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `uv run pytest tests/test_lighting.py -v`

Expected: collection fails because `LightingSnapshot`, `TargetIdentity`, and `FakeLightingTarget` do not exist.

- [ ] **Step 3: Add the generic contract**

```python
@dataclass(frozen=True, slots=True)
class TargetIdentity:
    backend: str
    device: str

    @property
    def key(self) -> str:
        return f"{self.backend}:{self.device}"


@dataclass(frozen=True, slots=True)
class LightingSnapshot:
    identity: TargetIdentity
    state: dict[str, object]
    pending_restore: bool = False


class LightingTarget(Protocol):
    identity: TargetIdentity

    async def snapshot(self) -> dict[str, object]: ...
    async def blackout(self, snapshot: dict[str, object]) -> None: ...
    async def restore(self, snapshot: dict[str, object]) -> None: ...
```

Add `NollieLightingTarget` around the existing `NollieController`; it maps
`read_standby_brightness()` to `{"canvases": [...]}`, writes zeros in
`blackout()`, and restores the captured tuple in `restore()`.

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest tests/test_lighting.py tests/test_protocol.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/magical_girl_glow_down/lighting.py src/magical_girl_glow_down/domain.py src/magical_girl_glow_down/protocol.py tests/fakes.py tests/test_lighting.py
git commit -m "refactor: add generic lighting target contract"
```

### Task 2: Generalize Transactions and Persistence

**Files:**
- Modify: `src/magical_girl_glow_down/service.py`
- Modify: `src/magical_girl_glow_down/storage.py`
- Modify: `tests/test_service.py`
- Modify: `tests/test_storage.py`
- Modify: `src/magical_girl_glow_down/simulator.py`

- [ ] **Step 1: Write failing mixed-target and migration tests**

```python
async def test_dims_and_restores_mixed_targets(tmp_path) -> None:
    targets = [
        FakeLightingTarget("nollie", "A", {"canvases": [30]}),
        FakeLightingTarget("gigabyte", "board", {"zones": [{"id": "logo", "brightness": 80}]}),
    ]
    service = LightingService(StateStore(tmp_path))
    await service.dim(targets)
    assert targets[0].state == {"canvases": [0]}
    assert targets[1].blackout_calls == 1
    await service.restore(targets)
    assert targets[1].state["zones"][0]["brightness"] == 80


def test_loads_version_one_brightness_snapshot(tmp_path) -> None:
    (tmp_path / "state.json").write_text(
        '{"version":1,"snapshots":{"Nollie16:A":{"model":"Nollie16",'
        '"serial":"A","canvases":[30],"pending_restore":true}}}',
        encoding="utf-8",
    )
    loaded = StateStore(tmp_path).load_snapshots()
    assert loaded["nollie:Nollie16:A"].state == {"canvases": [30]}
```

- [ ] **Step 2: Verify the tests fail**

Run: `uv run pytest tests/test_service.py tests/test_storage.py tests/test_simulator.py -v`

Expected: failures because the service accepts brightness controllers only and storage has no version-2 schema.

- [ ] **Step 3: Implement transactional opaque snapshots**

Rename `BrightnessService` to `LightingService`. For each target, capture and
atomically persist state before blackout. Preserve an existing pending snapshot,
never replacing it with a blacked-out state. Restore by identity and clear the
pending marker only after success. Catch `LightingError` and `OSError` per target
so one backend cannot block another.

Store version 2:

```json
{
  "version": 2,
  "snapshots": {
    "gigabyte:board-id": {
      "backend": "gigabyte",
      "device": "board-id",
      "state": {"schema": 1, "zones": []},
      "pending_restore": true
    }
  }
}
```

Migrate version-1 Nollie entries in memory and write version 2 on the next save.

- [ ] **Step 4: Run service, storage, and simulator tests**

Run: `uv run pytest tests/test_service.py tests/test_storage.py tests/test_simulator.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/magical_girl_glow_down/service.py src/magical_girl_glow_down/storage.py src/magical_girl_glow_down/simulator.py tests/test_service.py tests/test_storage.py tests/test_simulator.py
git commit -m "refactor: support opaque lighting snapshots"
```

### Task 3: Build the Versioned Helper Protocol

**Files:**
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/MagicalGirlGlowDown.GigabyteHelper.csproj`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/Program.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/Messages.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/IGigabyteAdapter.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/FakeGigabyteAdapter.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper.Tests/MagicalGirlGlowDown.GigabyteHelper.Tests.csproj`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper.Tests/ProtocolTests.cs`

- [ ] **Step 1: Create failing protocol tests**

```csharp
[Fact]
public async Task ProbeReturnsVersionedEnvelope()
{
    var server = new HelperServer(new FakeGigabyteAdapter());
    var response = await server.HandleAsync(
        new HelperRequest(1, "request-1", "probe", null));

    Assert.True(response.Ok);
    Assert.Equal(1, response.Schema);
    Assert.Equal("request-1", response.RequestId);
}

[Fact]
public async Task WriteRequiresMatchingBoardFingerprint()
{
    var server = new HelperServer(new FakeGigabyteAdapter("board-A"));
    var response = await server.HandleAsync(
        Requests.Blackout("request-2", "board-B", ["logo"]));
    Assert.Equal("board_mismatch", response.Error!.Code);
}
```

- [ ] **Step 2: Verify the tests fail**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Expected: build fails because the helper protocol types do not exist.

- [ ] **Step 3: Implement JSON-lines request handling**

Define operations `probe`, `snapshot`, `blackout`, and `restore`. Every envelope
contains `schema`, `requestId`, `ok`, and either `result` or a structured
`error { code, message }`. Reject unknown schema versions and operations.

`Program.cs` reads one JSON object per line from stdin and writes exactly one
JSON response per line to stdout. Logs use stderr. Use
`FakeGigabyteAdapter` only when `--fake` is explicitly passed; otherwise return
the structured `vendor_adapter_unavailable` error from a temporary
`UnavailableGigabyteAdapter`. Task 5 replaces that adapter with GCC discovery.

- [ ] **Step 4: Run helper tests**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add helper
git commit -m "feat: add Gigabyte helper protocol"
```

### Task 4: Add the Python Helper Client

**Files:**
- Create: `src/magical_girl_glow_down/gigabyte.py`
- Create: `tests/test_gigabyte.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing client tests**

```python
async def test_probe_parses_supported_zones(fake_helper) -> None:
    client = GigabyteHelperClient(fake_helper.command)
    probe = await client.probe()
    assert probe.board_fingerprint == "board-A"
    assert [zone.category for zone in probe.zones] == ["onboard", "argb5v", "rgb12v"]


async def test_timeout_becomes_backend_error(hanging_helper) -> None:
    client = GigabyteHelperClient(hanging_helper.command, timeout=0.01)
    with pytest.raises(GigabyteError, match="timed out"):
        await client.probe()
```

- [ ] **Step 2: Verify the tests fail**

Run: `uv run pytest tests/test_gigabyte.py -v`

Expected: import fails because `gigabyte.py` does not exist.

- [ ] **Step 3: Implement client, discovery, and target adapter**

Implement:

```python
class GigabyteHelperClient:
    async def probe(self) -> GigabyteProbe: ...
    async def snapshot(self, board: str, zones: tuple[str, ...]) -> dict[str, object]: ...
    async def blackout(self, board: str, snapshot: dict[str, object]) -> None: ...
    async def restore(self, board: str, snapshot: dict[str, object]) -> None: ...


class GigabyteLightingTarget:
    identity: TargetIdentity
    async def snapshot(self) -> dict[str, object]: ...
    async def blackout(self, snapshot: dict[str, object]) -> None: ...
    async def restore(self, snapshot: dict[str, object]) -> None: ...
```

Resolve the helper from `MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER`, a packaged helper
directory, or the local `dotnet run --project` path during development. Validate
the response schema, request ID, board fingerprint, zone categories, and JSON
shape. Kill timed-out helpers and include stderr in debug logs.

- [ ] **Step 4: Run Python tests and static checks**

Run: `uv run pytest tests/test_gigabyte.py -v`

Run: `uv run ruff check src/magical_girl_glow_down/gigabyte.py tests/test_gigabyte.py`

Run: `uv run mypy src`

Expected: all commands succeed.

- [ ] **Step 5: Commit**

```powershell
git add src/magical_girl_glow_down/gigabyte.py tests/test_gigabyte.py pyproject.toml
git commit -m "feat: add Gigabyte helper client"
```

### Task 5: Implement Read-Only GCC Discovery

**Files:**
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/GccInstallation.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/GccAssemblyResolver.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/GccReflectionAdapter.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/ZoneClassifier.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper.Tests/ZoneClassifierTests.cs`
- Modify: `src/magical_girl_glow_down/main.py`
- Modify: `tests/test_main.py`
- Create: `docs/gigabyte-validation.md`

- [ ] **Step 1: Write failing discovery and classification tests**

```csharp
[Theory]
[InlineData("MB_LED", "onboard")]
[InlineData("D_LED1", "argb5v")]
[InlineData("LED_C1", "rgb12v")]
[InlineData("mystery", "unsupported")]
public void ClassifiesOnlyExplicitZoneKinds(string vendorKind, string expected)
{
    Assert.Equal(expected, ZoneClassifier.Classify(vendorKind));
}
```

```python
def test_cli_parses_gigabyte_probe() -> None:
    args = build_parser().parse_args(["--gigabyte-probe"])
    assert args.gigabyte_probe is True
```

- [ ] **Step 2: Verify tests fail**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Run: `uv run pytest tests/test_main.py -v`

Expected: failures because discovery and CLI support do not exist.

- [ ] **Step 3: Implement strictly read-only probing**

`GccInstallation` locates:

```text
C:\Program Files\GIGABYTE\Control Center
Lib\GBT_rgbMotherboard_UC
Lib\COMMDLL
rgbcfg.xml
```

`GccAssemblyResolver` resolves dependencies only from those GCC directories.
`GccReflectionAdapter.ProbeAsync()` reads assembly versions, board identity, and
zone metadata using reflection and configuration parsing. It must not invoke
methods whose names match:

```text
Set*, Apply*, Output*, TurnOff*, LedOff*, LedOn*, Save*, Write*, Calibration*
```

`ZoneClassifier` uses explicit vendor metadata and known GCC configuration
labels. Anything ambiguous is `unsupported`.

Add `--gigabyte-probe`, which prints formatted JSON and exits without starting
the tray. Document the exact command and state clearly that it performs no
writes:

```powershell
uv run magical-girl-glow-down --gigabyte-probe --debug
```

- [ ] **Step 4: Run all read-only checks**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Run: `uv run pytest tests/test_main.py tests/test_gigabyte.py -v`

Run: `uv run magical-girl-glow-down --gigabyte-probe --debug`

Expected: tests pass; live command reports the current board fingerprint and
zone list without changing any light.

- [ ] **Step 5: Stop for hardware review**

Compare the live zone list with GCC. Confirm each `onboard`, `argb5v`, and
`rgb12v` entry. Add exact accepted vendor identifiers to
`docs/gigabyte-validation.md`. Do not begin Task 6 until this review passes.

- [ ] **Step 6: Commit**

```powershell
git add helper src/magical_girl_glow_down/main.py tests/test_main.py docs/gigabyte-validation.md
git commit -m "feat: add read-only Gigabyte RGB discovery"
```

### Task 6: Implement Snapshot, Blackout, and Restore

**Files:**
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/GccLightingAdapter.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper/VendorMethodPolicy.cs`
- Create: `helper/MagicalGirlGlowDown.GigabyteHelper.Tests/LightingAdapterTests.cs`
- Modify: `helper/MagicalGirlGlowDown.GigabyteHelper/Program.cs`
- Modify: `src/magical_girl_glow_down/main.py`
- Modify: `tests/test_main.py`
- Modify: `docs/gigabyte-validation.md`

- [ ] **Step 1: Write failing safety and restoration tests**

```csharp
[Fact]
public async Task BlackoutRestoresExactZoneState()
{
    var vendor = FakeVendor.WithZone("logo", mode: 3, color: 0x123456, speed: 2, brightness: 70);
    var adapter = new GccLightingAdapter(vendor);
    var snapshot = await adapter.SnapshotAsync("board-A", ["logo"]);
    await adapter.BlackoutAsync(snapshot);
    Assert.Equal(0, vendor.Zone("logo").Brightness);
    await adapter.RestoreAsync(snapshot);
    Assert.Equal((3, 0x123456, 2, 70), vendor.Zone("logo").Tuple());
}

[Theory]
[InlineData("dllexp_SaveToBios")]
[InlineData("SetCalibrationValue")]
public void PersistentMethodsAreForbidden(string method)
{
    Assert.False(VendorMethodPolicy.IsAllowed(method));
}
```

- [ ] **Step 2: Verify helper tests fail**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Expected: failures because write support does not exist.

- [ ] **Step 3: Implement validated temporary writes**

Capture all restorable fields exposed for each confirmed zone: power, effect or
mode, colors, speed, brightness, direction, and vendor extension data. Serialize
the raw field set with assembly versions and board fingerprint.

Prefer a vendor temporary off/power method when it preserves configuration.
Otherwise set brightness to zero and apply without calling any persistent-save
method. Restore the captured fields in vendor-required order and read back when
available. Reject snapshots with unknown fields, missing zones, mismatched
versions, or mismatched board fingerprints.

Add CLI flags `--gigabyte-snapshot`, `--gigabyte-test-zone`, and
`--restore-after`. The test-zone command requires one explicit zone ID,
snapshots it before writing, schedules restoration in a `finally` block, and
rejects restore delays below one second or above 30 seconds.

- [ ] **Step 4: Run fake-adapter tests**

Run: `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -v minimal`

Run: `uv run pytest tests/test_main.py tests/test_gigabyte.py -v`

Expected: all tests pass with no physical hardware access.

- [ ] **Step 5: Perform staged live validation**

Run snapshot only:

```powershell
uv run magical-girl-glow-down --gigabyte-snapshot --debug
```

Then run one confirmed onboard zone with a five-second automatic restore:

```powershell
uv run magical-girl-glow-down --gigabyte-test-zone "<confirmed-zone-id>" --restore-after 5
```

Expected: the selected zone turns off and returns to its exact prior effect.
Repeat only after success for one confirmed 5V and one confirmed 12V zone with
attached lighting. Never run an all-zone test before these checks pass.

- [ ] **Step 6: Commit**

```powershell
git add helper src/magical_girl_glow_down/main.py tests/test_main.py docs/gigabyte-validation.md
git commit -m "feat: control validated Gigabyte RGB zones"
```

### Task 7: Add GCC Coexistence and Tray Orchestration

**Files:**
- Modify: `src/magical_girl_glow_down/app_guard.py`
- Modify: `src/magical_girl_glow_down/tray.py`
- Create: `src/magical_girl_glow_down/worker.py`
- Modify: `tests/test_app_guard.py`
- Create: `tests/test_tray_worker.py`

- [ ] **Step 1: Write failing ownership-policy tests**

```python
def test_gcc_guard_is_case_insensitive() -> None:
    assert is_gcc_running(["explorer.exe", "GCC.EXE"])


async def test_gcc_start_restores_and_pauses_only_gigabyte(tmp_path) -> None:
    nollie = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    gigabyte = FakeLightingTarget("gigabyte", "board", {"zones": [{"id": "logo"}]})
    policy = WorkerPolicy(StateStore(tmp_path))
    await policy.tick([nollie, gigabyte], idle=True, gcc_running=False)
    await policy.tick([nollie, gigabyte], idle=True, gcc_running=True)
    assert gigabyte.restore_calls == 1
    assert nollie.restore_calls == 0
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest tests/test_app_guard.py tests/test_tray_worker.py -v`

Expected: failures because GCC detection and backend-specific pausing do not exist.

- [ ] **Step 3: Extract and implement worker policy**

Move hardware-independent decisions from `tray.Worker` into `worker.py`.
Maintain separate target groups:

- `NollieRGB.exe` restores and pauses Nollie targets.
- `GCC.exe` restores and pauses Gigabyte targets.
- manual pause restores and pauses all targets.

When GCC closes, wait two seconds, discard the pre-GCC target object, probe
again, and create a fresh Gigabyte target so the next idle snapshot adopts the
state GCC left behind.

Keep the Qt worker as a thin loop that discovers targets, polls input, calls the
policy, and emits a combined status string.

- [ ] **Step 4: Run worker and regression tests**

Run: `uv run pytest tests/test_app_guard.py tests/test_tray_worker.py tests/test_service.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/magical_girl_glow_down/app_guard.py src/magical_girl_glow_down/tray.py src/magical_girl_glow_down/worker.py tests/test_app_guard.py tests/test_tray_worker.py
git commit -m "feat: pause Gigabyte control while GCC is open"
```

### Task 8: Package, Document, and Verify End to End

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/gigabyte-validation.md`
- Create: `scripts/build-helper.ps1`
- Modify: `.gitignore`

- [ ] **Step 1: Add a deterministic helper build script**

```powershell
$ErrorActionPreference = "Stop"
dotnet publish helper/MagicalGirlGlowDown.GigabyteHelper `
  -c Release -r win-x64 --self-contained false `
  -o src/magical_girl_glow_down/gigabyte_helper
```

Exclude `bin/`, `obj/`, and copied GCC vendor assemblies. Include only our
published helper files in application packaging.

- [ ] **Step 2: Document prerequisites and behavior**

Update README with:

- compatible GCC must remain installed;
- Gigabyte DLLs are loaded from the local GCC installation;
- supported categories are confirmed onboard, 5V ARGB, and 12V RGB zones;
- GCC opening triggers restore and Gigabyte-only pause;
- no BIOS persistence or low-level bus fallback is used;
- probe and staged test commands.

- [ ] **Step 3: Run the complete automated verification**

Run:

```powershell
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy src
dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -c Release -v minimal
```

Expected: every command exits successfully.

- [ ] **Step 4: Run live acceptance**

1. Close GCC and NollieRGB.
2. Run `uv run magical-girl-glow-down --gigabyte-probe --debug`.
3. Start `uv run magical-girl-glow-down`.
4. Wait 30 seconds and confirm Nollie plus all validated Gigabyte zones turn off.
5. Test keyboard, mouse, and every connected game controller; verify exact
   restoration.
6. Open GCC while dimmed; verify restoration and Gigabyte pause.
7. Change a GCC effect, close GCC, wait for idle, and verify the new state is
   restored after input.
8. Force-close MagicalGirlGlowDown while dimmed, restart it, and verify pending
   recovery.

- [ ] **Step 5: Inspect repository contents**

Run:

```powershell
git status --short
git ls-files | Select-String -Pattern 'RgbMotherboard|LedIoControl|GBT_rgb|RGBFI|RgbCommon'
```

Expected: only source references appear; no Gigabyte DLL is tracked.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml README.md docs/gigabyte-validation.md scripts/build-helper.ps1 .gitignore
git commit -m "docs: package and validate Gigabyte RGB support"
```
