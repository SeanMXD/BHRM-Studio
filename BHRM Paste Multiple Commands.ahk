#Requires AutoHotkey v2.0

; Hotkey: Press Ctrl+Shift+V to start the process
^+v::
{
    SleepTime := 200 ; <<-- Adjust this value to change all sleep durations
    ClipSaved := A_Clipboard
    commands := StrSplit(A_Clipboard, "`n", "`r") ; Split clipboard into lines

    for cmd in commands
    {
        if GetKeyState("Enter", "P") ; Escape sequence: Press Enter to abort
            break

        A_Clipboard := cmd
        Sleep SleepTime
        Send "^v"
        Sleep SleepTime
        Send "{Enter}"
        Sleep SleepTime
    }
    A_Clipboard := ClipSaved
    return
}