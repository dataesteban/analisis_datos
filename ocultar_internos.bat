@echo off
cd /d "%~dp0"

echo Ocultando archivos internos...

attrib +h +s .claude /s /d 2>nul
attrib +h CLAUDE.md 2>nul
attrib +h PLAN.md 2>nul
attrib +h PROCESO.md 2>nul
attrib +h LICENSE 2>nul
attrib +h PRUEBA.TXT 2>nul
attrib +h README.md 2>nul
attrib +h .gitignore 2>nul
attrib +h .git /s /d 2>nul
attrib +h scripts /s /d 2>nul
attrib +h output /s /d 2>nul
attrib +h VisualP.Report /s /d 2>nul
attrib +h VisualP.SemanticModel /s /d 2>nul
attrib +h ocultar_internos.bat 2>nul

echo Listo. Solo quedan visibles los archivos esenciales.
pause
