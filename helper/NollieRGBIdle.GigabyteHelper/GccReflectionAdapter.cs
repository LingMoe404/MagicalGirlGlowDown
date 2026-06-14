using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using Microsoft.Win32;

namespace NollieRGBIdle.GigabyteHelper;

public sealed record BoardIdentity(string Manufacturer, string Product, string Version);

public sealed class GccReflectionAdapter : IGigabyteAdapter
{
    private static readonly IReadOnlyDictionary<string, string> ValidatedLayouts =
        new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["X870E AORUS MASTER X3D ICE"] = "98",
        };

    private static readonly string[] AssemblyNames =
    [
        "RgbMotherboard",
        "LedIoControl",
        "GBT_rgbMotherboard_UC",
        "MB_RGB_Capability",
    ];

    private readonly GccInstallation installation;
    private readonly GccAssemblyResolver resolver;

    public GccReflectionAdapter(GccInstallation installation)
    {
        this.installation = installation;
        resolver = new GccAssemblyResolver(installation);
    }

    public Task<JsonElement> ProbeAsync()
    {
        var board = ReadBoardIdentity();
        var fingerprint = Fingerprint(board.Manufacturer, board.Product, board.Version);
        var assemblyVersions = AssemblyNames.ToDictionary(
            name => name,
            name => ReadFileVersion(resolver.ResolvePath(name)));
        var zones = ReadProfileZones(board.Product);
        return Task.FromResult(JsonSerializer.SerializeToElement(new
        {
            boardFingerprint = fingerprint,
            board,
            assemblyVersions,
            zones,
            readOnly = true,
            warnings = zones.Length == 0
                ? new[] { "GCC did not expose any saved motherboard zones." }
                : new[]
                {
                    "Saved profile positions are reported as unsupported until their "
                    + "vendor zone identities are confirmed.",
                },
        }));
    }

    public Task<JsonElement> SnapshotAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(WritesUnavailable());

    public Task<JsonElement> BlackoutAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(WritesUnavailable());

    public Task<JsonElement> RestoreAsync(JsonElement? payload) =>
        Task.FromException<JsonElement>(WritesUnavailable());

    private object[] ReadProfileZones(string product)
    {
        if (!File.Exists(installation.ProfilePath))
        {
            return [];
        }
        var profileCount = XDocument.Load(installation.ProfilePath)
            .Descendants("ProfileFormat")
            .Count();
        if (!ValidatedLayouts.TryGetValue(product, out var layoutId))
        {
            return Enumerable.Range(0, profileCount)
                .Select(index => (object)new
                {
                    id = $"profile-{index}",
                    category = "unsupported",
                    name = $"GCC profile zone {index}",
                    source = "RGBMotherboard/Profile-0.xml",
                })
                .ToArray();
        }

        var configuration = XDocument.Load(installation.ConfigurationPath);
        var layout = configuration
            .Descendants("layout")
            .Elements("type")
            .SingleOrDefault(element => (string?)element.Attribute("id") == layoutId);
        if (layout is null)
        {
            throw new AdapterException(
                "layout_not_found",
                $"Validated GCC layout {layoutId} is absent from rgbcfg.xml.");
        }
        var layoutZones = layout.Elements("zone")
            .OrderBy(element => (int?)element.Attribute("num") ?? int.MaxValue)
            .ToArray();
        if (layoutZones.Length != profileCount)
        {
            throw new AdapterException(
                "layout_mismatch",
                "The saved GCC profile count does not match the validated board layout.");
        }
        return layoutZones.Select((element, index) =>
        {
            var name = (string?)element.Attribute("desc") ?? $"GCC zone {index}";
            return (object)new
            {
                id = $"profile-{index}",
                category = ZoneClassifier.Classify(name),
                name,
                pin = (string?)element.Attribute("pin_num"),
                layoutId,
                source = "rgbcfg.xml",
            };
        })
            .ToArray();
    }

    private static BoardIdentity ReadBoardIdentity()
    {
        using var bios = Registry.LocalMachine.OpenSubKey(
            @"HARDWARE\DESCRIPTION\System\BIOS");
        var manufacturer = bios?.GetValue("BaseBoardManufacturer") as string ?? "unknown";
        var product = bios?.GetValue("BaseBoardProduct") as string ?? "unknown";
        var version = bios?.GetValue("BaseBoardVersion") as string ?? "unknown";
        return new BoardIdentity(manufacturer, product, version);
    }

    private static string Fingerprint(params string[] values)
    {
        var normalized = string.Join(
            "|",
            values.Select(value => value.Trim().ToUpperInvariant()));
        return Convert.ToHexString(
            SHA256.HashData(Encoding.UTF8.GetBytes(normalized))).ToLowerInvariant();
    }

    private static string ReadFileVersion(string? path)
    {
        if (path is null)
        {
            return "missing";
        }
        return FileVersionInfo.GetVersionInfo(path).FileVersion ?? "unknown";
    }

    private static AdapterException WritesUnavailable() =>
        new(
            "write_not_implemented",
            "This helper build supports read-only GCC discovery only.");
}
