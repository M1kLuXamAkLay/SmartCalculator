; ========================================================
; Σuler.SC installer by NSIS 
; Version 1.3.0 — onedir структура (быстрый запуск)
; ========================================================

Unicode true
!include "MUI2.nsh"

Name "Σuler.SC 1.3.0"
OutFile "Σuler.SC_Setup.exe"
InstallDir "$PROGRAMFILES\Σuler.SC"
RequestExecutionLevel admin

!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY

Var DataDir
!define MUI_PAGE_HEADER_TEXT "Папка для данных приложения"
!define MUI_PAGE_HEADER_SUBTEXT "config.txt, .ollama, .matplotlib"
!define MUI_DIRECTORYPAGE_TEXT_TOP "Рекомендуется оставить значение по умолчанию."
!define MUI_DIRECTORYPAGE_VARIABLE $DataDir
!insertmacro MUI_PAGE_DIRECTORY

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Var DesktopStatus

LangString SecMain     ${LANG_RUSSIAN} "Основные файлы"
LangString SecDesktop  ${LANG_RUSSIAN} "Создать ярлык на рабочем столе"

Function .onInit
    StrCpy $DataDir "$APPDATA\Σuler.SC"
FunctionEnd

; ========================================================
; Sections
; ========================================================

Section "$(SecMain)" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  
  ; === КОПИРУЕМ ВСЮ ГОТОВУЮ СТРУКТУРУ ИЗ PyInstaller onedir ===
  File /r "dist\Σuler.SC\*"

  CreateDirectory "$DataDir"
  File /oname=$DataDir\config.txt "config.txt"
  CreateDirectory "$DataDir\.ollama"
  CreateDirectory "$DataDir\.matplotlib"

  ; Записываем путь к папке данных в реестр
  WriteRegStr HKCU "Software\Σuler.SC" "DataDir" "$DataDir"

  CreateDirectory "$SMPROGRAMS\Σuler.SC"
  CreateShortcut "$SMPROGRAMS\Σuler.SC\Σuler.SC.lnk" \
    "$INSTDIR\Σuler.SC.exe" "" "$INSTDIR\icon.ico" 0 "" "" "Умный калькулятор ЕГЭ"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "DisplayName" "Σuler.SC 1.3.0"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "DisplayIcon" "$INSTDIR\Σuler.SC.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "Publisher" "Σuler.SC"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "DisplayVersion" "1.3.0"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC" "NoRepair" 1

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "$(SecDesktop)" SecDesktop
  CreateShortcut "$DESKTOP\Σuler.SC.lnk" \
    "$INSTDIR\Σuler.SC.exe" "" "$INSTDIR\icon.ico" 0 "" "" "Умный калькулятор ЕГЭ"
  StrCpy $DesktopStatus "создан"
SectionEnd

Section -PostInstall
  ${If} $DesktopStatus == ""
    StrCpy $DesktopStatus "не создан (можно добавить позже)"
  ${EndIf}

  MessageBox MB_OK|MB_ICONINFORMATION \
    "Установка Σuler.SC 1.3.0 успешно завершена!$\r$\n$\r$\n\
     • Программа добавлена в меню Пуск$\r$\n\
     • Ярлык на рабочий стол $DesktopStatus$\r$\n\
     • Папка данных: $DataDir$\r$\n$\r$\n\
     Ollama настроится автоматически при первом запуске."
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Σuler.SC.lnk"
  Delete "$SMPROGRAMS\Σuler.SC\Σuler.SC.lnk"
  RMDir "$SMPROGRAMS\Σuler.SC"
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Σuler.SC"
  DeleteRegKey HKCU "Software\Σuler.SC"
SectionEnd