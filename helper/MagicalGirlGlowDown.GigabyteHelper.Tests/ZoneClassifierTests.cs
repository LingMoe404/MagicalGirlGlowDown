using MagicalGirlGlowDown.GigabyteHelper;
using Xunit;

namespace MagicalGirlGlowDown.GigabyteHelper.Tests;

public sealed class ZoneClassifierTests
{
    [Theory]
    [InlineData("MB_LED", "onboard")]
    [InlineData("D_LED1", "argb5v")]
    [InlineData("ARGB_V2_4", "argb5v")]
    [InlineData("LED_C1", "rgb12v")]
    [InlineData("IO Shield LED", "onboard")]
    [InlineData("PCH LED", "onboard")]
    [InlineData("mystery", "unsupported")]
    public void ClassifiesOnlyExplicitZoneKinds(string vendorKind, string expected)
    {
        Assert.Equal(expected, ZoneClassifier.Classify(vendorKind));
    }
}
