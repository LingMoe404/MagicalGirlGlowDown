using System.Reflection;

namespace MagicalGirlGlowDown.GigabyteHelper;

public sealed class GccReflectionLightingSession : IGccLightingSession
{
    private readonly object vendor;
    private readonly Type vendorType;

    public GccReflectionLightingSession(GccInstallation installation)
    {
        Environment.CurrentDirectory = installation.Root;
        var stagingDirectory = CreateStagingDirectory(installation);
        var resolver = new GccAssemblyResolver(installation, stagingDirectory);
        AppDomain.CurrentDomain.AssemblyResolve += (_, args) =>
        {
            var simpleName = new AssemblyName(args.Name).Name;
            var path = simpleName is null ? null : resolver.ResolvePath(simpleName);
            return path is null ? null : Assembly.LoadFrom(path);
        };
        var assemblyPath = resolver.ResolvePath("RgbMotherboard")
            ?? throw new AdapterException(
                "vendor_adapter_unavailable",
                "RgbMotherboard.dll was not found in the GCC installation.");
        var assembly = Assembly.LoadFrom(assemblyPath);
        vendorType = assembly.GetType("RgbMotherboard.RGB_Motherboard", throwOnError: true)!;
        vendor = Activator.CreateInstance(vendorType)
            ?? throw new AdapterException(
                "vendor_adapter_unavailable",
                "GCC motherboard lighting could not be initialized.");
    }

    public static string BuildStagingRoot(string commonApplicationData) =>
        Path.Combine(
            commonApplicationData,
            "MagicalGirlGlowDown",
            "GigabyteHelperStage");

    public static bool IsSafeStagingRoot(string path, bool isReparsePoint) =>
        Directory.Exists(path) && !isReparsePoint;

    private static string CreateStagingDirectory(GccInstallation installation)
    {
        var root = BuildStagingRoot(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData));
        if (!Directory.Exists(root))
        {
            throw new AdapterException(
                "protected_stage_unavailable",
                "The protected Gigabyte staging directory has not been initialized.");
        }
        var attributes = File.GetAttributes(root);
        if (!IsSafeStagingRoot(root, attributes.HasFlag(FileAttributes.ReparsePoint)))
        {
            throw new AdapterException(
                "protected_stage_invalid",
                "The protected Gigabyte staging directory is a reparse point.");
        }

        foreach (var existing in Directory.EnumerateDirectories(root))
        {
            try
            {
                Directory.Delete(existing, recursive: true);
            }
            catch (IOException)
            {
                // A previous helper may still be shutting down.
            }
            catch (UnauthorizedAccessException)
            {
                // Leave an inaccessible stale directory untouched.
            }
        }

        var stagingDirectory = Path.Combine(root, Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(stagingDirectory);
        foreach (var source in Directory.EnumerateFiles(
                     installation.MotherboardLibraryDirectory))
        {
            File.Copy(
                source,
                Path.Combine(stagingDirectory, Path.GetFileName(source)));
        }
        File.Copy(
            installation.ConfigurationPath,
            Path.Combine(stagingDirectory, "rgbcfg.xml"));
        if (File.Exists(installation.SmbControlPath))
        {
            File.Copy(
                installation.SmbControlPath,
                Path.Combine(stagingDirectory, "SMBCtrl.dll"));
        }
        if (File.Exists(installation.UserDataPath))
        {
            File.Copy(
                installation.UserDataPath,
                Path.Combine(stagingDirectory, "usdata2.xml"));
        }
        return stagingDirectory;
    }

    public string GetLedSetting() =>
        (string?)InvokeAllowed("GetLedSetting")
        ?? throw new AdapterException("invalid_vendor_state", "GCC returned no lighting state.");

    public string GetDiagnostics()
    {
        var deviceName = vendorType.GetProperty(
            "DeviceName",
            BindingFlags.Instance | BindingFlags.Public)?.GetValue(vendor);
        return $"DeviceName={deviceName ?? "null"}, "
            + $"MbId={InvokeAllowed("GetMbId")}, "
            + $"LedId={InvokeAllowed("GetLedId")}, "
            + $"McuType={InvokeAllowed("GetMcuType")}, "
            + $"Layout={InvokeAllowed("GetLedLayoutInfo")}";
    }

    public int SetAllLedColor(uint color) => Convert.ToInt32(
        InvokeAllowed("SetAllLedColor", color));

    public int ApplyState(string vendorState)
    {
        var stateProperty = vendorType.GetProperty(
            "sInfo",
            BindingFlags.Instance | BindingFlags.Public)
            ?? throw new AdapterException(
                "vendor_method_missing",
                "GCC state property sInfo is unavailable.");
        stateProperty.SetValue(vendor, vendorState);
        return Convert.ToInt32(InvokeAllowed("Apply", 3));
    }

    private object? InvokeAllowed(string methodName, params object[] arguments)
    {
        if (!VendorMethodPolicy.IsAllowed(methodName))
        {
            throw new AdapterException(
                "forbidden_vendor_method",
                $"Vendor method {methodName} is not allowed.");
        }
        var method = vendorType.GetMethod(
            methodName,
            BindingFlags.Instance | BindingFlags.Public)
            ?? throw new AdapterException(
                "vendor_method_missing",
                $"GCC method {methodName} is unavailable.");
        try
        {
            return method.Invoke(vendor, arguments);
        }
        catch (TargetInvocationException exc)
        {
            throw new AdapterException(
                "vendor_call_failed",
                $"GCC method {methodName} failed: {exc.InnerException?.Message ?? exc.Message}");
        }
    }
}
