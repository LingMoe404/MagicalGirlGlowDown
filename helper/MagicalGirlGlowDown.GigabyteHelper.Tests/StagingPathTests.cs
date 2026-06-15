using System;
using System.IO;
using MagicalGirlGlowDown.GigabyteHelper;
using Xunit;

namespace MagicalGirlGlowDown.GigabyteHelper.Tests;

public sealed class StagingPathTests
{
    [Fact]
    public void StagingRootUsesCommonApplicationData()
    {
        Assert.Equal(
            Path.Combine(
                @"C:\ProgramData",
                "MagicalGirlGlowDown",
                "GigabyteHelperStage"),
            GccReflectionLightingSession.BuildStagingRoot(@"C:\ProgramData"));
    }

    [Fact]
    public void ReparsePointIsRejected()
    {
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        try
        {
            Assert.False(GccReflectionLightingSession.IsSafeStagingRoot(path, true));
        }
        finally
        {
            Directory.Delete(path);
        }
    }
}
