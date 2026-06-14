using System.Text.Json;

namespace NollieRGBIdle.GigabyteHelper;

public sealed class HelperServer(IGigabyteAdapter adapter)
{
    public async Task<HelperResponse> HandleAsync(HelperRequest request)
    {
        if (request.Schema != 1)
        {
            return HelperResponse.Failure(
                request.RequestId,
                "unsupported_schema",
                $"Unsupported schema version: {request.Schema}");
        }

        try
        {
            var result = request.Operation switch
            {
                "probe" => await adapter.ProbeAsync(),
                "snapshot" => await adapter.SnapshotAsync(request.Payload),
                "blackout" => await adapter.BlackoutAsync(request.Payload),
                "restore" => await adapter.RestoreAsync(request.Payload),
                _ => throw new AdapterException(
                    "unsupported_operation",
                    $"Unsupported operation: {request.Operation}"),
            };
            return HelperResponse.Success(request.RequestId, result);
        }
        catch (AdapterException exc)
        {
            return HelperResponse.Failure(request.RequestId, exc.Code, exc.Message);
        }
        catch (Exception exc)
        {
            Console.Error.WriteLine(exc);
            return HelperResponse.Failure(
                request.RequestId,
                "internal_error",
                "The helper could not complete the request.");
        }
    }
}
