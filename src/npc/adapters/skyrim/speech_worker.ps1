param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($request.operation -eq 'tts') {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
        $synth.SetOutputToWaveFile($request.output, $format)
        $synth.Speak([string]$request.text)
        $synth.SetOutputToNull()
        Write-Output '{"status":"ok","engine":"Windows SAPI"}'
    } finally { $synth.Dispose() }
} elseif ($request.operation -eq 'stt') {
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    try {
        $recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
        $recognizer.SetInputToWaveFile($request.input)
        $result = $recognizer.Recognize([TimeSpan]::FromSeconds(16))
        if ($null -eq $result -or [string]::IsNullOrWhiteSpace($result.Text)) { throw 'no_speech_recognized' }
        @{text=$result.Text;confidence=[double]$result.Confidence;engine='Windows SAPI'} | ConvertTo-Json -Compress
    } finally { $recognizer.Dispose() }
} elseif ($request.operation -eq 'probe') {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $voices = @($synth.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name})
        $recognizers = @([System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | ForEach-Object {$_.Culture.Name})
        @{voices=$voices;recognizers=$recognizers;engine='Windows SAPI'} | ConvertTo-Json -Compress
    } finally { $synth.Dispose() }
} else { throw 'unsupported_operation' }
