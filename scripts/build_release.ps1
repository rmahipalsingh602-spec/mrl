param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not $Version) {
    $Version = (& python -c "from mrl.version import __version__; print(__version__)").Trim()
}

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must use major.minor.patch format. Received: $Version"
}

$versionParts = $Version.Split(".")
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]
$patch = [int]$versionParts[2]
$versionQuad = "$Version.0"

$pyInstaller = (Get-Command pyinstaller -ErrorAction SilentlyContinue).Source
if (-not $pyInstaller) {
    throw "pyinstaller was not found on PATH."
}

$innoCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$iscc = $innoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup compiler (ISCC.exe) was not found."
}

$versionInfoPath = Join-Path $repoRoot "build_assets\mrl_version_info.txt"
$versionInfo = @"
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($major, $minor, $patch, 0),
    prodvers=($major, $minor, $patch, 0),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'Mr. Rathore'),
            StringStruct('FileDescription', 'MRL Multi Runtime Language'),
            StringStruct('FileVersion', '$versionQuad'),
            StringStruct('InternalName', 'mrl'),
            StringStruct('LegalCopyright', 'Copyright (c) Mr. Rathore. All rights reserved.'),
            StringStruct('OriginalFilename', 'mrl.exe'),
            StringStruct('ProductName', 'MRL'),
            StringStruct('ProductVersion', '$versionQuad')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
Set-Content -Path $versionInfoPath -Value $versionInfo -Encoding utf8

& $pyInstaller --clean --noconfirm "mrl.spec"

$setupBaseName = "mrl-windows-x64-setup-$Version"
& $iscc "/DReleaseVersion=$Version" "/DReleaseVersionQuad=$versionQuad" "/DOutputBaseName=$setupBaseName" "mrl_installer.iss"

$downloadsDir = Join-Path $repoRoot "website\downloads"
New-Item -ItemType Directory -Path $downloadsDir -Force | Out-Null

$portableSource = Join-Path $repoRoot "dist\mrl.exe"
$setupSource = Join-Path $repoRoot ("output\" + $setupBaseName + ".exe")

if (-not (Test-Path $portableSource)) {
    throw "Portable executable was not created: $portableSource"
}
if (-not (Test-Path $setupSource)) {
    throw "Installer executable was not created: $setupSource"
}

$portableVersionedName = "mrl-windows-x64-$Version.exe"
$portableStableName = "mrl-windows-x64.exe"
$setupVersionedName = "$setupBaseName.exe"
$setupStableName = "mrl-windows-x64-setup.exe"

$portableVersionedPath = Join-Path $downloadsDir $portableVersionedName
$portableStablePath = Join-Path $downloadsDir $portableStableName
$setupVersionedPath = Join-Path $downloadsDir $setupVersionedName
$setupStablePath = Join-Path $downloadsDir $setupStableName

Copy-Item $portableSource $portableVersionedPath -Force
Copy-Item $portableSource $portableStablePath -Force
Copy-Item $setupSource $setupVersionedPath -Force
Copy-Item $setupSource $setupStablePath -Force

function Get-SignatureLabel {
    param(
        [string]$Status
    )

    switch ($Status) {
        "Valid" { return "Signed release" }
        "NotSigned" { return "Unsigned build" }
        default { return "Signature status: $Status" }
    }
}

function Get-ArtifactMetadata {
    param(
        [string]$Key,
        [string]$Name,
        [string]$FilePath,
        [string]$DownloadPath,
        [string]$AliasPath
    )

    $absolutePath = Join-Path $repoRoot $FilePath
    $item = Get-Item $absolutePath
    $hash = (Get-FileHash $absolutePath -Algorithm SHA256).Hash
    $signature = Get-AuthenticodeSignature $absolutePath

    return [ordered]@{
        key = $Key
        name = $Name
        download_path = ($DownloadPath -replace "\\", "/")
        alias_path = ($AliasPath -replace "\\", "/")
        size_bytes = [int64]$item.Length
        sha256 = $hash
        signature_status = $signature.Status.ToString()
        signature_label = Get-SignatureLabel -Status $signature.Status.ToString()
        signer_subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
    }
}

$setupArtifact = Get-ArtifactMetadata -Key "setup" -Name $setupVersionedName -FilePath ("website\downloads\" + $setupVersionedName) -DownloadPath ("downloads/" + $setupVersionedName) -AliasPath ("downloads/" + $setupStableName)
$portableArtifact = Get-ArtifactMetadata -Key "portable" -Name $portableVersionedName -FilePath ("website\downloads\" + $portableVersionedName) -DownloadPath ("downloads/" + $portableVersionedName) -AliasPath ("downloads/" + $portableStableName)

$manifest = [ordered]@{
    product = "MRL"
    version = $Version
    display_version = "MRL $Version"
    platform = "windows-x64"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    artifacts = [ordered]@{
        setup = $setupArtifact
        portable = $portableArtifact
    }
}

$manifestPath = Join-Path $downloadsDir "release-manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding utf8

$checksumLines = @(
    "$($setupArtifact.sha256)  $($setupArtifact.name)",
    "$($portableArtifact.sha256)  $($portableArtifact.name)"
)
Set-Content -Path (Join-Path $downloadsDir "SHA256SUMS.txt") -Value $checksumLines -Encoding utf8

Write-Host "Built release $Version"
Write-Host "Setup:    website/downloads/$setupVersionedName"
Write-Host "Portable: website/downloads/$portableVersionedName"
Write-Host "Manifest: website/downloads/release-manifest.json"

