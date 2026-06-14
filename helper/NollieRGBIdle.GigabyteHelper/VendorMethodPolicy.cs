namespace NollieRGBIdle.GigabyteHelper;

public static class VendorMethodPolicy
{
    private static readonly HashSet<string> Allowed =
        new(StringComparer.Ordinal)
        {
            "Apply",
            "GetLedSetting",
            "SetAllLedColor",
        };

    public static bool IsAllowed(string methodName) => Allowed.Contains(methodName);
}
