Add-Type -AssemblyName System.Speech

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $synth.GetInstalledVoices() | ForEach-Object {
  $info = $_.VoiceInfo
  [PSCustomObject]@{
    name = $info.Name
    culture = $info.Culture.Name
    gender = $info.Gender.ToString()
    age = $info.Age.ToString()
  }
}

$voices | ConvertTo-Json -Depth 3
$synth.Dispose()
