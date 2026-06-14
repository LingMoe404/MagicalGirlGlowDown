using System.Text.Json;

namespace NollieRGBIdle.GigabyteHelper;

public interface IGigabyteAdapter
{
    Task<JsonElement> ProbeAsync();
    Task<JsonElement> SnapshotAsync(JsonElement? payload);
    Task<JsonElement> BlackoutAsync(JsonElement? payload);
    Task<JsonElement> RestoreAsync(JsonElement? payload);
}

public sealed class AdapterException(string code, string message) : Exception(message)
{
    public string Code { get; } = code;
}

public sealed class UnavailableGigabyteAdapter : IGigabyteAdapter
{
    private static AdapterException Unavailable() =>
        new("vendor_adapter_unavailable", "The GCC vendor adapter is unavailable.");

    public Task<JsonElement> ProbeAsync() => Task.FromException<JsonElement>(Unavailable());

    public Task<JsonElement> SnapshotAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(Unavailable());

    public Task<JsonElement> BlackoutAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(Unavailable());

    public Task<JsonElement> RestoreAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(Unavailable());
}
