Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strDir
objShell.Environment("Process")("USERPROFILE") = objShell.Environment("User")("USERPROFILE")
objShell.Environment("Process")("LOCALAPPDATA") = objShell.Environment("User")("LOCALAPPDATA")
objShell.Environment("Process")("PROGRAMFILES") = objShell.ExpandEnvironmentStrings("%ProgramFiles%")
objShell.Environment("Process")("PROGRAMFILES(X86)") = objShell.ExpandEnvironmentStrings("%ProgramFiles(x86)%")
objShell.Run "py -m jarvis --tray", 0, False
