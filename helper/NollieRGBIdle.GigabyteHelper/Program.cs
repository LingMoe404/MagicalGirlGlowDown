using System.Text.Json;
using NollieRGBIdle.GigabyteHelper;

var jsonOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    PropertyNameCaseInsensitive = true,
};
IGigabyteAdapter adapter = args.Contains("--fake", StringComparer.OrdinalIgnoreCase)
    ? new FakeGigabyteAdapter()
    : CreateVendorAdapter();
var server = new HelperServer(adapter);

while (await Console.In.ReadLineAsync() is { } line)
{
    HelperResponse response;
    try
    {
        var request = JsonSerializer.Deserialize<HelperRequest>(line, jsonOptions)
            ?? throw new JsonException("Request is null.");
        response = await server.HandleAsync(request);
    }
    catch (JsonException exc)
    {
        response = HelperResponse.Failure("", "invalid_json", exc.Message);
    }

    Console.WriteLine(JsonSerializer.Serialize(response, jsonOptions));
}

static IGigabyteAdapter CreateVendorAdapter()
{
    try
    {
        var installation = GccInstallation.Locate();
        var discovery = new GccReflectionAdapter(installation);
        return new GccLightingAdapter(
            discovery.Describe(),
            () => new GccReflectionLightingSession(installation),
            discovery: discovery);
    }
    catch (AdapterException)
    {
        return new UnavailableGigabyteAdapter();
    }
}
