Scriptname AnimaMCM extends SKI_ConfigBase

Int menuOption = -1
Int voiceOption = -1

Event OnConfigInit()
    ModName = "Anima"
    Pages = New String[1]
    Pages[0] = "Conversation"
EndEvent

Event OnPageReset(String page)
    SetCursorFillMode(2)
    AddHeaderOption("ANIMA dialogue controls")
    menuOption = AddKeyMapOption("Conversation / text menu", AnimaNative.GetMenuKey())
    voiceOption = AddKeyMapOption("Hold to speak", AnimaNative.GetVoiceKey())
    AddTextOption("Start", "Use the Anima dialogue option")
    AddTextOption("Alternative", "Open NPC dialogue, then menu key")
    AddTextOption("Speech / model status", "See the [ANIMA] console")
EndEvent

Event OnOptionKeyMapChange(Int option, Int keyCode, String conflictControl, String conflictName)
    If conflictControl != ""
        SetInfoText("Key conflict: " + conflictControl + " " + conflictName)
        Return
    EndIf
    Bool accepted = False
    If option == menuOption
        accepted = AnimaNative.SetMenuKey(keyCode)
    ElseIf option == voiceOption
        accepted = AnimaNative.SetVoiceKey(keyCode)
    EndIf
    If accepted
        SetKeyMapOptionValue(option, keyCode)
    Else
        SetInfoText("Choose a different keyboard key for each Anima control.")
    EndIf
EndEvent

Event OnOptionHighlight(Int option)
    SetInfoText("Anima uses its own bridge, model and speech services. Keep the [ANIMA] console running. Hold the voice key to record; release to send. Escape cancels text entry.")
EndEvent
