namespace NollieRGBIdle.GigabyteHelper;

public sealed class GccAssemblyResolver(
    GccInstallation installation,
    string? stagingDirectory = null)
{
    public string? ResolvePath(string simpleName)
    {
        foreach (var directory in new string?[]
                 {
                     stagingDirectory,
                     installation.MotherboardLibraryDirectory,
                     installation.CommonLibraryDirectory,
                 })
        {
            if (directory is null)
            {
                continue;
            }
            var path = Path.Combine(directory, $"{simpleName}.dll");
            if (File.Exists(path))
            {
                return path;
            }
        }
        return null;
    }
}
