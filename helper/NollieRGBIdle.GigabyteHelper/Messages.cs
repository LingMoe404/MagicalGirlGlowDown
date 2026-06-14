using System.Text.Json;

namespace NollieRGBIdle.GigabyteHelper;

public sealed record HelperRequest(
    int Schema,
    string RequestId,
    string Operation,
    JsonElement? Payload);

public sealed record HelperError(string Code, string Message);

public sealed record HelperResponse(
    int Schema,
    string RequestId,
    bool Ok,
    JsonElement? Result,
    HelperError? Error)
{
    public static HelperResponse Success(string requestId, JsonElement result) =>
        new(1, requestId, true, result, null);

    public static HelperResponse Failure(string requestId, string code, string message) =>
        new(1, requestId, false, null, new HelperError(code, message));
}
