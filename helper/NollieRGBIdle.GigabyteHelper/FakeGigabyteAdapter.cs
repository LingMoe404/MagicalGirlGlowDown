using System.Text.Json;

namespace NollieRGBIdle.GigabyteHelper;

public sealed class FakeGigabyteAdapter(string boardFingerprint = "board-A") : IGigabyteAdapter
{
    public Task<JsonElement> ProbeAsync() =>
        Task.FromResult(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint,
            zones = new[]
            {
                new { id = "logo", category = "onboard" },
                new { id = "d-led-1", category = "argb5v" },
                new { id = "led-c-1", category = "rgb12v" },
            },
        }));

    public Task<JsonElement> SnapshotAsync(JsonElement? payload)
    {
        ValidateBoard(payload);
        return Task.FromResult(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint,
            zones = Array.Empty<object>(),
        }));
    }

    public Task<JsonElement> BlackoutAsync(JsonElement? payload)
    {
        ValidateBoard(payload);
        return Task.FromResult(JsonSerializer.SerializeToElement(new { applied = true }));
    }

    public Task<JsonElement> RestoreAsync(JsonElement? payload)
    {
        ValidateBoard(payload);
        return Task.FromResult(JsonSerializer.SerializeToElement(new { restored = true }));
    }

    private void ValidateBoard(JsonElement? payload)
    {
        if (payload is null ||
            !payload.Value.TryGetProperty("boardFingerprint", out var board) ||
            board.GetString() != boardFingerprint)
        {
            throw new AdapterException(
                "board_mismatch",
                "The request board fingerprint does not match the active board.");
        }
    }
}
