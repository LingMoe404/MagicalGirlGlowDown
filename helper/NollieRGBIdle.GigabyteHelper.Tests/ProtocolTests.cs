using System.Text.Json;
using NollieRGBIdle.GigabyteHelper;
using Xunit;

namespace NollieRGBIdle.GigabyteHelper.Tests;

public sealed class ProtocolTests
{
    [Fact]
    public async Task ProbeReturnsVersionedEnvelope()
    {
        var server = new HelperServer(new FakeGigabyteAdapter());

        var response = await server.HandleAsync(
            new HelperRequest(1, "request-1", "probe", null));

        Assert.True(response.Ok);
        Assert.Equal(1, response.Schema);
        Assert.Equal("request-1", response.RequestId);
        Assert.Null(response.Error);
        Assert.Equal(
            "board-A",
            response.Result!.Value.GetProperty("boardFingerprint").GetString());
    }

    [Fact]
    public async Task WriteRequiresMatchingBoardFingerprint()
    {
        var server = new HelperServer(new FakeGigabyteAdapter("board-A"));
        var payload = JsonSerializer.SerializeToElement(
            new { boardFingerprint = "board-B", zones = new[] { "logo" } });

        var response = await server.HandleAsync(
            new HelperRequest(1, "request-2", "blackout", payload));

        Assert.False(response.Ok);
        Assert.Equal("board_mismatch", response.Error!.Code);
    }

    [Fact]
    public async Task UnknownSchemaAndOperationReturnStructuredErrors()
    {
        var server = new HelperServer(new FakeGigabyteAdapter());

        var schema = await server.HandleAsync(
            new HelperRequest(2, "schema", "probe", null));
        var operation = await server.HandleAsync(
            new HelperRequest(1, "operation", "erase", null));

        Assert.Equal("unsupported_schema", schema.Error!.Code);
        Assert.Equal("unsupported_operation", operation.Error!.Code);
    }

    [Fact]
    public async Task UnavailableAdapterReturnsStructuredError()
    {
        var server = new HelperServer(new UnavailableGigabyteAdapter());

        var response = await server.HandleAsync(
            new HelperRequest(1, "request-3", "probe", null));

        Assert.Equal("vendor_adapter_unavailable", response.Error!.Code);
    }
}
