namespace NollieRGBIdle.GigabyteHelper;

public sealed record GccInstallation(string Root)
{
    public string MotherboardLibraryDirectory =>
        Path.Combine(Root, "Lib", "GBT_rgbMotherboard_UC");

    public string CommonLibraryDirectory => Path.Combine(Root, "Lib", "COMMDLL");

    public string ConfigurationPath => Path.Combine(Root, "rgbcfg.xml");

    public string ProfilePath => Path.Combine(Root, "RGBMotherboard", "Profile-0.xml");

    public static GccInstallation Locate()
    {
        var configured = Environment.GetEnvironmentVariable("NOLLIERGBIDLE_GCC_ROOT");
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        var root = configured ?? Path.Combine(programFiles, "GIGABYTE", "Control Center");
        var installation = new GccInstallation(root);
        if (!Directory.Exists(installation.MotherboardLibraryDirectory) ||
            !File.Exists(installation.ConfigurationPath))
        {
            throw new AdapterException(
                "gcc_not_found",
                $"A compatible GCC installation was not found at {root}.");
        }
        return installation;
    }
}
