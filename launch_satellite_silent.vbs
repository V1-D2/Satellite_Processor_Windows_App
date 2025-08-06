' Silent launcher for SatelliteProcessor
' This VBS script runs the batch file without showing any console window
' Place this file in the same directory as launch_satellite.bat

Dim objShell, objFSO, strScriptDir, strBatchFile

' Get the directory where this VBS script is located
Set objFSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Path to the batch file
strBatchFile = strScriptDir & "\launch_satellite.bat"

' Check if batch file exists
If objFSO.FileExists(strBatchFile) Then
    ' Create shell object and run batch file hidden
    Set objShell = CreateObject("WScript.Shell")

    ' Run with window style 0 (hidden) and don't wait for completion
    objShell.Run """" & strBatchFile & """", 0, False

    Set objShell = Nothing
Else
    ' Show error if batch file not found
    MsgBox "Error: launch_satellite.bat not found in " & strScriptDir, vbCritical, "SatelliteProcessor"
End If

Set objFSO = Nothing