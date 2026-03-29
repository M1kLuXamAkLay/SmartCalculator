; ========================================================
; УСТАНОВЩИК SmartCalculator
; Версия 1.2.0
; ========================================================

[Setup]
AppName=SmartCalculator
AppVersion=1.2.0
AppPublisher=SmartCalculator
AppCopyright=© 2026 SmartCalculator
AppComments=Умный калькулятор для ЕГЭ профильная математика
DefaultDirName={pf}\SmartCalculator
DefaultGroupName=SmartCalculator
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico
OutputDir=Output
OutputBaseFilename=SmartCalculator_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

LicenseFile=LICENSE
DisableDirPage=no
DisableProgramGroupPage=no
AlwaysShowDirOnReadyPage=yes

[Tasks]
Name: desktopicon; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи";

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "app\*.py"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SmartCalculator"; Filename: "{cmd}"; Parameters: "/c pythonw ""{app}\main.py"""; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"
Name: "{commondesktop}\SmartCalculator"; Filename: "{cmd}"; Parameters: "/c pythonw ""{app}\main.py"""; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Установка зависимостей
Filename: "powershell.exe";
Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""pip install -r ""{app}\requirements.txt"" --upgrade --no-deps""";
Flags: runhidden shellexec waituntilterminated;
StatusMsg: "Установка библиотек";

; Запуск программы после установки
Filename: "{cmd}";
Parameters: "/c pythonw ""{app}\main.py""";
Description: "Запустить SmartCalculator";
Flags: postinstall nowait skipifsilent

[Code]
function DesktopIconStatus: string;
begin
  if WizardIsTaskSelected('desktopicon') then
    Result := 'создан'
  else
    Result := 'не создан (можно добавить позже)';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    MsgBox('✅ Установка SmartCalculator успешно завершена!' + #13#10#13#10 +
           '• Программа добавлена в «Программы и компоненты»' + #13#10 +
           '• Ярлык создан в меню Пуск' + #13#10 +
           '• Ярлык на рабочий стол ' + DesktopIconStatus + #13#10#13#10 +
           'При первом запуске Ollama настроится автоматически.',
           mbInformation, MB_OK);
end;