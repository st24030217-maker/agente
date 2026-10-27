Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strPythonExe = strScriptDir & "\.venv\Scripts\python.exe"

If Not FSO.FileExists(strPythonExe) Then
    strPythonExe = "python.exe"
End If

strCmd = """" & strPythonExe & """ """ & strScriptDir & "\supervisor.py"""

' 0 = Oculto, False = No esperar a que termine
WshShell.Run strCmd, 0, False
