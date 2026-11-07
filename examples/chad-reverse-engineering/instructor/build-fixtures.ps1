[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $AndroidSdk,
    [Parameter(Mandatory)] [string] $JavaHome,
    [Parameter(Mandatory)] [string] $OutputDirectory
)

$ErrorActionPreference = 'Stop'

function Invoke-FixtureTool {
    param([string] $Program, [string[]] $Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program exited with code $LASTEXITCODE"
    }
}

$sdk = (Resolve-Path -LiteralPath $AndroidSdk).Path
$jdk = (Resolve-Path -LiteralPath $JavaHome).Path
$compiler = (Get-Command cl.exe -ErrorAction Stop).Source
$dotnet = (Get-Command dotnet.exe -ErrorAction Stop).Source
$buildTools = Join-Path $sdk 'build-tools/36.0.0'
$androidJar = Join-Path $sdk 'platforms/android-36/android.jar'
$output = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
if (Test-Path -LiteralPath $output) {
    throw "Choose a new output directory. Already exists: $output"
}

$stage = [IO.Directory]::CreateTempSubdirectory('assimilation-fixtures-').FullName
$previousJavaHome = $env:JAVA_HOME
$previousDotnetHome = $env:DOTNET_CLI_HOME
$previousDotnetCertificate = $env:DOTNET_GENERATE_ASPNET_CERTIFICATE
$previousDotnetTelemetry = $env:DOTNET_CLI_TELEMETRY_OPTOUT
Push-Location -LiteralPath $stage
try {
    $env:JAVA_HOME = $jdk
    $env:DOTNET_CLI_HOME = $stage
    $env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    Invoke-FixtureTool $compiler @('/nologo', '/std:c17', '/Od', '/GS-', '/Zl',
        (Join-Path $PSScriptRoot 'native/quota.c'), '/Fe:quota.exe', '/link', '/Brepro',
        '/NODEFAULTLIB', '/ENTRY:lab_main', '/SUBSYSTEM:CONSOLE', 'kernel32.lib', 'shell32.lib')
    $native = [IO.File]::ReadAllBytes((Join-Path $stage 'quota.exe'))
    $header = [BitConverter]::ToInt32($native, 0x3C)
    if ([BitConverter]::ToUInt16($native, $header + 4) -ne 0x8664) {
        throw 'Build from an x64 Native Tools Command Prompt.'
    }

    $managed = Join-Path $stage 'managed'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'managed') -Destination $managed -Recurse
    Invoke-FixtureTool $dotnet @('build', (Join-Path $managed 'LabArithmetic.csproj'),
        '-c', 'Release', '-o', (Join-Path $stage 'managed-out'))

    $classes = [IO.Directory]::CreateDirectory((Join-Path $stage 'classes')).FullName
    $dex = [IO.Directory]::CreateDirectory((Join-Path $stage 'dex')).FullName
    Invoke-FixtureTool (Join-Path $jdk 'bin/javac.exe') @('--release', '8', '-d', $classes,
        (Join-Path $PSScriptRoot 'android/RetryPolicy.java'))
    Invoke-FixtureTool (Join-Path $buildTools 'd8.bat') @('--min-api', '23', '--lib', $androidJar,
        '--output', $dex, (Join-Path $classes 'org/assimilation/lab/RetryPolicy.class'))
    $apkPath = Join-Path $stage 'assimilation-lab.apk'
    Invoke-FixtureTool (Join-Path $buildTools 'aapt2.exe') @('link', '-I', $androidJar, '--manifest',
        (Join-Path $PSScriptRoot 'android/AndroidManifest.xml'), '-o', $apkPath)

    $apk = [IO.Compression.ZipFile]::Open($apkPath, [IO.Compression.ZipArchiveMode]::Update)
    try {
        $entry = [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $apk, (Join-Path $dex 'classes.dex'), 'classes.dex')
        $entry.LastWriteTime = [DateTimeOffset]::Parse('1980-01-01T00:00:00Z')
    } finally {
        $apk.Dispose()
    }

    [IO.Directory]::CreateDirectory($output) | Out-Null
    foreach ($artifact in @('quota.exe', 'managed-out/LabArithmetic.dll', 'assimilation-lab.apk')) {
        Copy-Item -LiteralPath (Join-Path $stage $artifact) -Destination $output
    }
    Get-ChildItem -LiteralPath $output -File | Get-FileHash -Algorithm SHA256
} finally {
    Pop-Location
    $env:JAVA_HOME = $previousJavaHome
    $env:DOTNET_CLI_HOME = $previousDotnetHome
    $env:DOTNET_GENERATE_ASPNET_CERTIFICATE = $previousDotnetCertificate
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = $previousDotnetTelemetry
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $fullStage = [IO.Path]::GetFullPath($stage)
    if (!$fullStage.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
        ![IO.Path]::GetFileName($fullStage).StartsWith('assimilation-fixtures-')) {
        throw "Build staging directory is outside the expected boundary: $fullStage"
    }
    [IO.Directory]::Delete($fullStage, $true)
}
