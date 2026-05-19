@echo off
setlocal enabledelayedexpansion

set "PRG=%~0"
:resolveLoop
for %%F in ("%PRG%") do (
    set "PRG_DIR=%%~dpF"
    set "PRG_NAME=%%~nxF"
)
set "PRG=%PRG_DIR%%PRG_NAME%"

cd "%PRG_DIR%\.."
set "APP_DIR=%CD%"
set "CONF_DIR=%APP_DIR%\config"
set "APP_JAR=%APP_DIR%\starter\seatunnel-starter.jar"
set "APP_MAIN=org.apache.seatunnel.core.starter.seatunnel.SeaTunnelClient"

if exist "%CONF_DIR%\seatunnel-env.cmd" call "%CONF_DIR%\seatunnel-env.cmd"

if "%~1"=="" (set "args=-h") else (set "args=%*")

if not defined HAZELCAST_CLIENT_CONFIG (set "HAZELCAST_CLIENT_CONFIG=%CONF_DIR%\hazelcast-client.yaml")
if not defined HAZELCAST_CONFIG (set "HAZELCAST_CONFIG=%CONF_DIR%\hazelcast.yaml")
if not defined SEATUNNEL_CONFIG (set "SEATUNNEL_CONFIG=%CONF_DIR%\seatunnel.yaml")

if defined JvmOption (set "JAVA_OPTS=%JAVA_OPTS% %JvmOption%")

for %%i in (%*) do (
    set "arg=%%i"
    if "!arg:~0,9!"=="JvmOption" (
        set "JVM_OPTION=!arg:~9!"
        set "JAVA_OPTS=!JAVA_OPTS! !JVM_OPTION!"
        goto :break_loop
    )
)
:break_loop

set "JAVA_OPTS=%JAVA_OPTS% -Dhazelcast.client.config=%HAZELCAST_CLIENT_CONFIG%"
set "JAVA_OPTS=%JAVA_OPTS% -Dseatunnel.config=%SEATUNNEL_CONFIG%"
set "JAVA_OPTS=%JAVA_OPTS% -Dhazelcast.config=%HAZELCAST_CONFIG%"

if exist "%CONF_DIR%\log4j2_client.properties" (
    set "JAVA_OPTS=%JAVA_OPTS% -Dlog4j2.configurationFile=%CONF_DIR%\log4j2_client.properties"
    set "JAVA_OPTS=%JAVA_OPTS% -Dseatunnel.logs.path=%APP_DIR%\logs"

    for %%i in (%args%) do (
        set "arg=%%i"
        if "!arg!"=="-m" set "is_local_mode=true"
        if "!arg!"=="--master" set "is_local_mode=true"
        if "!arg!"=="-e" set "is_local_mode=true"
        if "!arg!"=="--deploy-mode" set "is_local_mode=true"
    )

    if defined is_local_mode (
        set "JAVA_OPTS=%JAVA_OPTS% -Dseatunnel.logs.file_name=seatunnel-starter-client"
    ) else (
        set "JAVA_OPTS=%JAVA_OPTS% -Dseatunnel.logs.file_name=seatunnel-starter-client"
    )
)

set "CLASS_PATH=%APP_DIR%\lib\*;%APP_JAR%"

for /f "usebackq delims=" %%a in ("%APP_DIR%\config\jvm_client_options") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" if "!line!" neq "" (
        set "JAVA_OPTS=!JAVA_OPTS! !line!"
    )
)

java %JAVA_OPTS% -cp %CLASS_PATH% %APP_MAIN% %args%
