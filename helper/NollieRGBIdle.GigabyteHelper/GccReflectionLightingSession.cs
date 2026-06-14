using System.Reflection;

namespace NollieRGBIdle.GigabyteHelper;

public sealed class GccReflectionLightingSession : IGccLightingSession
{
    private readonly object vendor;
    private readonly Type vendorType;

    public GccReflectionLightingSession(GccInstallation installation)
    {
        var resolver = new GccAssemblyResolver(installation);
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

    public string GetLedSetting() =>
        (string?)InvokeAllowed("GetLedSetting")
        ?? throw new AdapterException("invalid_vendor_state", "GCC returned no lighting state.");

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
