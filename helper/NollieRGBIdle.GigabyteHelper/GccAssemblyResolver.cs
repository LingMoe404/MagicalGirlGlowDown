namespace NollieRGBIdle.GigabyteHelper;

public sealed class GccAssemblyResolver(GccInstallation installation)
{
    public string? ResolvePath(string simpleName)
    {
        foreach (var directory in new[]
                 {
                     installation.MotherboardLibraryDirectory,
                     installation.CommonLibraryDirectory,
                 })
        {
            var path = Path.Combine(directory, $"{simpleName}.dll");
            if (File.Exists(path))
            {
                return path;
            }
        }
        return null;
    }
}
