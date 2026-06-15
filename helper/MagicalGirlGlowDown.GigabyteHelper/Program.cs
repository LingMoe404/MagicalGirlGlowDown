using System.Text.Json;
using MagicalGirlGlowDown.GigabyteHelper;

var jsonOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    PropertyNameCaseInsensitive = true,
};
string? developmentGccRoot = null;
try
{
    developmentGccRoot = ReadOption(args, "--gcc-root");
}
catch (AdapterException exc)
{
    Console.WriteLine(JsonSerializer.Serialize(
        HelperResponse.Failure("", exc.Code, exc.Message),
        jsonOptions));
    return;
}

IGigabyteAdapter adapter = args.Contains("--fake", StringComparer.OrdinalIgnoreCase)
    ? new FakeGigabyteAdapter()
    : CreateVendorAdapter(developmentGccRoot);
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

static string? ReadOption(string[] args, string name)
{
    var index = Array.FindIndex(
        args,
        value => string.Equals(value, name, StringComparison.OrdinalIgnoreCase));
    if (index < 0)
    {
        return null;
    }
    if (index + 1 >= args.Length || string.IsNullOrWhiteSpace(args[index + 1]))
    {
        throw new AdapterException("invalid_argument", $"{name} requires a path.");
    }
    return args[index + 1];
}

static IGigabyteAdapter CreateVendorAdapter(string? developmentGccRoot)
{
    try
    {
        var installation = GccInstallation.Locate(developmentGccRoot);
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

