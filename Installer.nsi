; ========================================================
; SmartCalculator installer by NSIS 
; Version 1.2.2
; ========================================================

Unicode true
!include "MUI2.nsh"

Name "SmartCalculator 1.2.2"
OutFile "SmartCalculator_Setup.exe"
InstallDir "$PROGRAMFILES\SmartCalculator"
RequestExecutionLevel admin

!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Var DesktopStatus

LangString SecMain     ${LANG_RUSSIAN} "Основные файлы"
LangString SecDesktop  ${LANG_RUSSIAN} "Создать ярлык на рабочем столе"

; ========================================================
; Sections
; ========================================================

Section "$(SecMain)" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  
  ; Копируем ВСЁ из собранной PyInstaller папки
  File /r "dist\SmartCalculator\*.*"

  CreateDirectory "$SMPROGRAMS\SmartCalculator"
  CreateShortcut "$SMPROGRAMS\SmartCalculator\SmartCalculator.lnk" \
    "$INSTDIR\SmartCalculator.exe" "" "$INSTDIR\icon.ico" 0 "" "" "Умный калькулятор ЕГЭ"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "DisplayName" "SmartCalculator 1.2.2"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "DisplayIcon" "$INSTDIR\icon.ico"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "Publisher" "SmartCalculator"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "DisplayVersion" "1.2.2"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator" "NoRepair" 1

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "$(SecDesktop)" SecDesktop
  CreateShortcut "$DESKTOP\SmartCalculator.lnk" \
    "$INSTDIR\SmartCalculator.exe" "" "$INSTDIR\icon.ico" 0 "" "" "Умный калькулятор ЕГЭ"
  StrCpy $DesktopStatus "создан"
SectionEnd

Section -PostInstall
  ${If} $DesktopStatus == ""
    StrCpy $DesktopStatus "не создан (можно добавить позже)"
  ${EndIf}

  MessageBox MB_OK|MB_ICONINFORMATION \
    "Установка SmartCalculator успешно завершена!$\r$\n$\r$\n\
     • Программа добавлена в меню Пуск$\r$\n\
     • Ярлык на рабочий стол $DesktopStatus$\r$\n$\r$\n\
     Ollama настроится автоматически при первом запуске."
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\SmartCalculator.lnk"
  Delete "$SMPROGRAMS\SmartCalculator\SmartCalculator.lnk"
  RMDir "$SMPROGRAMS\SmartCalculator"
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SmartCalculator"
SectionEnd