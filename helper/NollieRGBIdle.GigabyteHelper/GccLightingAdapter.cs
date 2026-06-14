using System.Text.Json;

namespace NollieRGBIdle.GigabyteHelper;

public sealed record GccBoardDescription(
    string BoardFingerprint,
    IReadOnlyDictionary<string, string> AssemblyVersions,
    IReadOnlyList<string> ZoneIds);

public interface IGccLightingSession
{
    string GetLedSetting();
    int SetAllLedColor(uint color);
    int ApplyState(string vendorState);
}

public sealed class GccLightingAdapter(
    GccBoardDescription board,
    Func<IGccLightingSession> createSession,
    Func<bool>? isGccRunning = null,
    IGigabyteAdapter? discovery = null) : IGigabyteAdapter
{
    private readonly Func<bool> isGccRunning =
        isGccRunning ?? (() => System.Diagnostics.Process.GetProcessesByName("GCC").Length > 0);

    public Task<JsonElement> ProbeAsync() =>
        discovery?.ProbeAsync()
        ?? Task.FromResult(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = board.BoardFingerprint,
            assemblyVersions = board.AssemblyVersions,
            zones = board.ZoneIds.Select(id => new { id, category = "unsupported" }),
        }));

    public Task<JsonElement> SnapshotAsync(JsonElement? payload)
    {
        EnsureGccIsClosed();
        var requestedZones = ValidateRequest(payload);
        RequireCompleteZoneSet(requestedZones);
        using var document = JsonDocument.Parse(createSession().GetLedSetting());
        if (document.RootElement.ValueKind != JsonValueKind.Array)
        {
            throw new AdapterException(
                "invalid_vendor_state",
                "GCC returned a lighting state that is not an array.");
        }
        if (document.RootElement.GetArrayLength() != board.ZoneIds.Count)
        {
            throw new AdapterException(
                "invalid_vendor_state",
                "GCC lighting state count does not match the validated zone count.");
        }
        return Task.FromResult(JsonSerializer.SerializeToElement(new
        {
            schema = 1,
            boardFingerprint = board.BoardFingerprint,
            assemblyVersions = board.AssemblyVersions,
            zones = requestedZones,
            vendorState = document.RootElement.Clone(),
        }));
    }

    public Task<JsonElement> BlackoutAsync(JsonElement? payload)
    {
        EnsureGccIsClosed();
        var snapshot = ValidateSnapshotRequest(payload);
        RequireCompleteZoneSet(ReadZones(snapshot));
        EnsureSuccess(createSession().SetAllLedColor(0), "SetAllLedColor");
        return Task.FromResult(JsonSerializer.SerializeToElement(new { applied = true }));
    }

    public Task<JsonElement> RestoreAsync(JsonElement? payload)
    {
        EnsureGccIsClosed();
        var snapshot = ValidateSnapshotRequest(payload);
        RequireCompleteZoneSet(ReadZones(snapshot));
        var vendorState = snapshot.GetProperty("vendorState");
        EnsureSuccess(createSession().ApplyState(vendorState.GetRawText()), "Apply");
        return Task.FromResult(JsonSerializer.SerializeToElement(new { restored = true }));
    }

    private IReadOnlyList<string> ValidateRequest(JsonElement? payload)
    {
        var value = RequireObject(payload, "request");
        ValidateBoard(value);
        if (!value.TryGetProperty("zones", out var zones) ||
            zones.ValueKind != JsonValueKind.Array)
        {
            throw new AdapterException("invalid_request", "The request has no zone list.");
        }
        return ReadZones(value);
    }

    private JsonElement ValidateSnapshotRequest(JsonElement? payload)
    {
        var value = RequireObject(payload, "request");
        ValidateBoard(value);
        if (!value.TryGetProperty("snapshot", out var snapshot) ||
            snapshot.ValueKind != JsonValueKind.Object)
        {
            throw new AdapterException("invalid_snapshot", "The request has no snapshot.");
        }
        if (!snapshot.TryGetProperty("schema", out var schema) || schema.GetInt32() != 1)
        {
            throw new AdapterException("invalid_snapshot", "Unsupported snapshot schema.");
        }
        ValidateBoard(snapshot);
        ValidateVersions(snapshot);
        if (!snapshot.TryGetProperty("vendorState", out var vendorState) ||
            vendorState.ValueKind != JsonValueKind.Array)
        {
            throw new AdapterException("invalid_snapshot", "Snapshot vendor state is invalid.");
        }
        return snapshot;
    }

    private void ValidateBoard(JsonElement value)
    {
        if (!value.TryGetProperty("boardFingerprint", out var fingerprint) ||
            fingerprint.GetString() != board.BoardFingerprint)
        {
            throw new AdapterException(
                "board_mismatch",
                "The request board fingerprint does not match the active board.");
        }
    }

    private void ValidateVersions(JsonElement snapshot)
    {
        if (!snapshot.TryGetProperty("assemblyVersions", out var versions) ||
            versions.ValueKind != JsonValueKind.Object)
        {
            throw new AdapterException("invalid_snapshot", "Snapshot has no assembly versions.");
        }
        foreach (var pair in board.AssemblyVersions)
        {
            if (!versions.TryGetProperty(pair.Key, out var version) ||
                version.GetString() != pair.Value)
            {
                throw new AdapterException(
                    "version_mismatch",
                    $"GCC assembly version changed for {pair.Key}.");
            }
        }
    }

    private static JsonElement RequireObject(JsonElement? payload, string name)
    {
        if (payload is null || payload.Value.ValueKind != JsonValueKind.Object)
        {
            throw new AdapterException("invalid_request", $"The {name} must be an object.");
        }
        return payload.Value;
    }

    private static IReadOnlyList<string> ReadZones(JsonElement value)
    {
        if (!value.TryGetProperty("zones", out var zones) ||
            zones.ValueKind != JsonValueKind.Array)
        {
            throw new AdapterException("invalid_snapshot", "Snapshot has no zone list.");
        }
        var result = new List<string>();
        foreach (var zone in zones.EnumerateArray())
        {
            var id = zone.GetString();
            if (string.IsNullOrWhiteSpace(id))
            {
                throw new AdapterException("invalid_snapshot", "Snapshot has an invalid zone.");
            }
            result.Add(id);
        }
        return result;
    }

    private void RequireCompleteZoneSet(IReadOnlyList<string> zones)
    {
        if (zones.Count != board.ZoneIds.Count ||
            !zones.Order(StringComparer.Ordinal).SequenceEqual(
                board.ZoneIds.Order(StringComparer.Ordinal),
                StringComparer.Ordinal))
        {
            throw new AdapterException(
                "partial_zone_unsupported",
                "This validated GCC backend currently requires the complete zone set.");
        }
    }

    private void EnsureGccIsClosed()
    {
        if (isGccRunning())
        {
            throw new AdapterException(
                "gcc_running",
                "GCC is running and currently owns the motherboard lighting.");
        }
    }

    private static void EnsureSuccess(int result, string method)
    {
        if (result < 0)
        {
            throw new AdapterException(
                "vendor_write_failed",
                $"GCC method {method} failed with result {result}.");
        }
    }
}
