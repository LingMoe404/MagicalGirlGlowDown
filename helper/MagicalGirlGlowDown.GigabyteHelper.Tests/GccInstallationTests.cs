using MagicalGirlGlowDown.GigabyteHelper;
using Xunit;

namespace MagicalGirlGlowDown.GigabyteHelper.Tests;

public sealed class GccInstallationTests
{
    [Fact]
    public void ExplicitDevelopmentRootIsUsed()
    {
        var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var libDir = Path.Combine(tempPath, "Lib", "GBT_rgbMotherboard_UC");
        var cfgFile = Path.Combine(tempPath, "rgbcfg.xml");
        Directory.CreateDirectory(libDir);
        File.WriteAllText(cfgFile, "<cfg/>");
        try
        {
            var installation = GccInstallation.FromRoot(tempPath);
            Assert.Equal(tempPath, installation.Root);
        }
        finally
        {
            Directory.Delete(tempPath, true);
        }
    }

    [Fact]
    public void DefaultRootUsesProgramFiles()
    {
        var root = GccInstallation.DefaultRoot(@"C:\Program Files");
        Assert.Equal(
            @"C:\Program Files\GIGABYTE\Control Center",
            root);
    }
}
