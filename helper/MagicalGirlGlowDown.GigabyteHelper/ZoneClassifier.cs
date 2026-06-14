namespace MagicalGirlGlowDown.GigabyteHelper;

public static class ZoneClassifier
{
    public static string Classify(string vendorKind)
    {
        var normalized = vendorKind.Trim().ToUpperInvariant();
        if (normalized.StartsWith("D_LED", StringComparison.Ordinal) ||
            normalized.StartsWith("ARGB_", StringComparison.Ordinal))
        {
            return "argb5v";
        }
        if (normalized.StartsWith("LED_C", StringComparison.Ordinal))
        {
            return "rgb12v";
        }
        if (normalized is "MB_LED" or "MOTHERBOARD" or "ONBOARD" ||
            normalized.Contains("SHIELD LED", StringComparison.Ordinal) ||
            normalized.Contains("PCH LED", StringComparison.Ordinal))
        {
            return "onboard";
        }
        return "unsupported";
    }
}
