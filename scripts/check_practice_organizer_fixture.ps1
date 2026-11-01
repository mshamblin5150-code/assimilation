# Read-only fixture-presence guard shared by CI and its behavioral regression.
# Emits exactly 'true' or 'false' to the success output stream.
param(
  [Parameter(Mandatory = $true)][string]$SourcePath,
  [Parameter(Mandatory = $true)][string]$TestPath
)
$present = (Test-Path -LiteralPath $SourcePath -PathType Leaf) -and
           (Test-Path -LiteralPath $TestPath -PathType Leaf)
if ($present) { 'true' } else { 'false' }
