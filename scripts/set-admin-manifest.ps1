param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $Path)) {
    throw "Executable not found: $Path"
}

$code = @'
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

public static class ExeManifestTools
{
    private const uint LOAD_LIBRARY_AS_DATAFILE = 0x00000002;
    private const ushort RT_MANIFEST = 24;
    private const ushort MAIN_MANIFEST_ID = 1;

    private delegate bool EnumResLangProc(IntPtr hModule, IntPtr lpType, IntPtr lpName, ushort wLanguage, IntPtr lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadLibraryExW(string lpFileName, IntPtr hFile, uint dwFlags);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr FindResourceW(IntPtr hModule, IntPtr lpName, IntPtr lpType);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint SizeofResource(IntPtr hModule, IntPtr hResInfo);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LoadResource(IntPtr hModule, IntPtr hResInfo);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LockResource(IntPtr hResData);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool FreeLibrary(IntPtr hModule);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr BeginUpdateResourceW(string pFileName, bool bDeleteExistingResources);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool UpdateResourceW(
        IntPtr hUpdate,
        IntPtr lpType,
        IntPtr lpName,
        ushort wLanguage,
        byte[] lpData,
        uint cbData);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool EndUpdateResourceW(IntPtr hUpdate, bool fDiscard);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool EnumResourceLanguagesW(
        IntPtr hModule,
        IntPtr lpType,
        IntPtr lpName,
        EnumResLangProc lpEnumFunc,
        IntPtr lParam);

    private static IntPtr MakeIntResource(ushort value)
    {
        return new IntPtr(value);
    }

    public static string ReadManifest(string path)
    {
        IntPtr module = LoadLibraryExW(path, IntPtr.Zero, LOAD_LIBRARY_AS_DATAFILE);
        if (module == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        try
        {
            IntPtr resource = FindResourceW(module, MakeIntResource(MAIN_MANIFEST_ID), MakeIntResource(RT_MANIFEST));
            if (resource == IntPtr.Zero)
            {
                throw new InvalidOperationException("Manifest resource not found.");
            }

            uint size = SizeofResource(module, resource);
            IntPtr data = LoadResource(module, resource);
            IntPtr pointer = LockResource(data);
            if (pointer == IntPtr.Zero)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }

            byte[] bytes = new byte[size];
            Marshal.Copy(pointer, bytes, 0, (int)size);
            return Encoding.UTF8.GetString(bytes);
        }
        finally
        {
            FreeLibrary(module);
        }
    }

    private static ushort GetManifestLanguage(string path)
    {
        IntPtr module = LoadLibraryExW(path, IntPtr.Zero, LOAD_LIBRARY_AS_DATAFILE);
        if (module == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        try
        {
            ushort language = 0;
            bool captured = false;

            EnumResLangProc callback = delegate (
                IntPtr hModule,
                IntPtr lpType,
                IntPtr lpName,
                ushort wLanguage,
                IntPtr lParam)
            {
                language = wLanguage;
                captured = true;
                return false;
            };

            bool enumerated = EnumResourceLanguagesW(
                module,
                MakeIntResource(RT_MANIFEST),
                MakeIntResource(MAIN_MANIFEST_ID),
                callback,
                IntPtr.Zero);

            if (!enumerated && Marshal.GetLastWin32Error() != 0 && !captured)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }

            return language;
        }
        finally
        {
            FreeLibrary(module);
        }
    }

    public static void SetRequireAdministrator(string path)
    {
        string manifest = ReadManifest(path);
        string updatedManifest = Regex.Replace(
            manifest,
            "level=\"asInvoker\"",
            "level=\"requireAdministrator\"");

        if (updatedManifest == manifest)
        {
            if (manifest.IndexOf("level=\"requireAdministrator\"", StringComparison.Ordinal) >= 0)
            {
                return;
            }

            throw new InvalidOperationException("Executable manifest does not declare a Windows UAC execution level.");
        }

        ushort language = GetManifestLanguage(path);
        byte[] bytes = Encoding.UTF8.GetBytes(updatedManifest);

        IntPtr handle = BeginUpdateResourceW(path, false);
        if (handle == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        try
        {
            bool updated = UpdateResourceW(
                handle,
                MakeIntResource(RT_MANIFEST),
                MakeIntResource(MAIN_MANIFEST_ID),
                language,
                bytes,
                (uint)bytes.Length);
            if (!updated)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }

            if (!EndUpdateResourceW(handle, false))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
        }
        catch
        {
            EndUpdateResourceW(handle, true);
            throw;
        }
    }
}
'@

Add-Type -TypeDefinition $code
[ExeManifestTools]::SetRequireAdministrator((Resolve-Path -LiteralPath $Path).Path)
