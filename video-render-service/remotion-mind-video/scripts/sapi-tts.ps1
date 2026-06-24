param(
  [Parameter(Mandatory=$true)][string]$TextPath,
  [Parameter(Mandatory=$true)][string]$OutPath,
  [string]$VoiceName = "",
  [int]$Rate = 0
)

Add-Type -AssemblyName System.Speech

$text = Get-Content -LiteralPath $TextPath -Raw -Encoding UTF8
$dir = Split-Path -Parent $OutPath
if (!(Test-Path -LiteralPath $dir)) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = [Math]::Max(-10, [Math]::Min(10, $Rate))

if ($VoiceName -and $VoiceName.Trim().Length -gt 0) {
  $synth.SelectVoice($VoiceName)
}

$synth.SetOutputToWaveFile($OutPath)
$synth.Speak($text)
$synth.SetOutputToNull()
$synth.Dispose()
