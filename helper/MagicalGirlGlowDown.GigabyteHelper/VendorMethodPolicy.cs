namespace MagicalGirlGlowDown.GigabyteHelper;

public static class VendorMethodPolicy
{
    private static readonly HashSet<string> Allowed =
        new(StringComparer.Ordinal)
        {
            "Apply",
            "GetLedId",
            "GetLedLayoutInfo",
            "GetLedSetting",
            "GetMbId",
            "GetMcuType",
            "SetAllLedColor",
        };

    public static bool IsAllowed(string methodName) => Allowed.Contains(methodName);
}
