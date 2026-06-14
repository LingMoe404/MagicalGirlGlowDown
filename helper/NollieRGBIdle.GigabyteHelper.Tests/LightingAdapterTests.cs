using System.Text.Json;
using NollieRGBIdle.GigabyteHelper;
using Xunit;

namespace NollieRGBIdle.GigabyteHelper.Tests;

public sealed class LightingAdapterTests
{
    [Fact]
    public async Task BlackoutAndRestoreUseExactCapturedVendorState()
    {
        const string original =
            """[{"ledMode":3,"ledColor0":1193046,"spLv":2,"briLv":7}]""";
        var session = new FakeLightingSession(original);
        var adapter = CreateAdapter(session);
        var snapshotRequest = JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            zones = new[] { "profile-0" },
        });

        var snapshot = await adapter.SnapshotAsync(snapshotRequest);
        await adapter.BlackoutAsync(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            snapshot,
        }));
        await adapter.RestoreAsync(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            snapshot,
        }));

        Assert.Equal(0u, session.LastColor);
        Assert.Equal(original, session.AppliedState);
    }

    [Fact]
    public async Task WritesAreRejectedWhileGccOwnsTheHardware()
    {
        var session = new FakeLightingSession("""[{"briLv":8}]""");
        var adapter = CreateAdapter(session, gccRunning: true);
        var payload = JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            snapshot = Snapshot(),
        });

        var error = await Assert.ThrowsAsync<AdapterException>(
            () => adapter.BlackoutAsync(payload));

        Assert.Equal("gcc_running", error.Code);
        Assert.Null(session.LastColor);
    }

    [Fact]
    public async Task SnapshotIsRejectedWhileGccOwnsTheHardware()
    {
        var session = new FakeLightingSession("""[{"briLv":8}]""");
        var adapter = CreateAdapter(session, gccRunning: true);
        var payload = JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            zones = new[] { "profile-0" },
        });

        var error = await Assert.ThrowsAsync<AdapterException>(
            () => adapter.SnapshotAsync(payload));

        Assert.Equal("gcc_running", error.Code);
    }

    [Fact]
    public async Task SnapshotRejectsVendorStateWithWrongZoneCount()
    {
        var adapter = CreateAdapter(new FakeLightingSession("[]"));
        var payload = JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = "board-A",
            zones = new[] { "profile-0" },
        });

        var error = await Assert.ThrowsAsync<AdapterException>(
            () => adapter.SnapshotAsync(payload));

        Assert.Equal("invalid_vendor_state", error.Code);
    }

    [Theory]
    [InlineData("Apply")]
    [InlineData("GetLedSetting")]
    [InlineData("SetAllLedColor")]
    public void TemporaryRuntimeMethodsAreAllowed(string method)
    {
        Assert.True(VendorMethodPolicy.IsAllowed(method));
    }

    [Theory]
    [InlineData("SaveSetting")]
    [InlineData("SaveToBios")]
    [InlineData("SetCalibrationValue")]
    [InlineData("WriteProfile")]
    public void PersistentMethodsAreForbidden(string method)
    {
        Assert.False(VendorMethodPolicy.IsAllowed(method));
    }

    private static GccLightingAdapter CreateAdapter(
        FakeLightingSession session,
        bool gccRunning = false) =>
        new(
            new GccBoardDescription(
                "board-A",
                new Dictionary<string, string> { ["RgbMotherboard"] = "1.0.0.0" },
                ["profile-0"]),
            () => session,
            () => gccRunning);

    private static object Snapshot() => new
    {
        schema = 1,
        boardFingerprint = "board-A",
        assemblyVersions = new Dictionary<string, string>
        {
            ["RgbMotherboard"] = "1.0.0.0",
        },
        zones = new[] { "profile-0" },
        vendorState = JsonSerializer.Deserialize<JsonElement>("""[{"briLv":8}]"""),
    };

    private sealed class FakeLightingSession(string state) : IGccLightingSession
    {
        public uint? LastColor { get; private set; }
        public string? AppliedState { get; private set; }

        public string GetLedSetting() => state;

        public string GetDiagnostics() => "fake diagnostics";

        public int SetAllLedColor(uint color)
        {
            LastColor = color;
            return 0;
        }

        public int ApplyState(string vendorState)
        {
            AppliedState = vendorState;
            return 0;
        }
    }
}
