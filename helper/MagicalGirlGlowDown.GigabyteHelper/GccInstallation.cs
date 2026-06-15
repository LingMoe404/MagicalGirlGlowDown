namespace MagicalGirlGlowDown.GigabyteHelper;

public sealed record GccInstallation(string Root)
{
    public string MotherboardLibraryDirectory =>
        Path.Combine(Root, "Lib", "GBT_rgbMotherboard_UC");

    public string CommonLibraryDirectory => Path.Combine(Root, "Lib", "COMMDLL");

    public string ConfigurationPath => Path.Combine(Root, "rgbcfg.xml");

    public string ProfilePath => Path.Combine(Root, "RGBMotherboard", "Profile-0.xml");

    public string UserDataPath => Path.Combine(Root, "usdata2.xml");

    public string SmbControlPath => Path.Combine(Root, "SMBCtrl.dll");

    public static string DefaultRoot(string programFiles) =>
        Path.Combine(programFiles, "GIGABYTE", "Control Center");

    public static GccInstallation FromRoot(string root) => Validate(new GccInstallation(root));

    public static GccInstallation Locate(string? developmentRoot = null)
    {
        var root = developmentRoot ?? DefaultRoot(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles));
        return Validate(new GccInstallation(root));
    }

    private static GccInstallation Validate(GccInstallation installation)
    {
        if (!Directory.Exists(installation.MotherboardLibraryDirectory) ||
            !File.Exists(installation.ConfigurationPath))
        {
            throw new AdapterException(
                "gcc_not_found",
                $"A compatible GCC installation was not found at {installation.Root}.");
        }
        return installation;
    }

}
