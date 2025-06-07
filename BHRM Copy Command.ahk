#Requires AutoHotkey v2.0

^+c::  ; CTRL+SHIFT+C hotkey
{
    doubleClickSleep := 50
    defaultSleep := 150

    Click
    Sleep doubleClickSleep
    Click
    Sleep doubleClickSleep
    Click              ; Triple-click with pauses to select the line or paragraph
    Sleep defaultSleep
    Send "^c"          ; Copy
    Sleep defaultSleep ; Short pause to ensure copy completes
    Send "!{Tab}"      ; ALT+TAB to switch window
    Sleep defaultSleep
    Send "^v"          ; Paste
    Sleep defaultSleep

    ; --- Deleting prefix ---
    Send "{Home}"      ; Move to start of line
    Sleep defaultSleep
    Send "^+{Right 5}" ; Hold CTRL+SHIFT and press RIGHT 5 times
    Sleep defaultSleep
    Send "^+{Left}"    ; Hold CTRL+SHIFT and press LEFT once
    Sleep defaultSleep
    Send "{Backspace}" ; Delete selection
    Sleep defaultSleep
    Send "{End}"       ; Move to end of line
    ; --- END Deleting prefix ---
    Sleep defaultSleep
    Send "{Enter}"     ; Press Enter
    Sleep defaultSleep
    Send "!{Tab}"      ; ALT+TAB back
}