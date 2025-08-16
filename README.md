# Neko Bot

## Variables de Entorno

### Necesarias
```
API_ID = Ingrese su API ID para acceder a Telegram.
API_HASH = Ingrese la API HASH de su API ID
TOKEN =  Ingrese el Token de su bot
ADMINS = Ingrese el User ID de los administradores del bot
USERS = Ingrese el User ID de los usuarios del bot
```

### Extras
```
BOT_IS_PUBLIC = Coloque el valor "True" para que cualquiera pueda usar el bot (Aún asi, coloque 0 en USERS)
CODEWORD = Coloque una contraseña para que otros usen el comanndo /access
PROTECT_CONTENT = Escribe True para bloquear el renvio y descarga de multimedia de el bot
VIP_USERS = Coloca User IDs de usuarios que podran renviar contenido (No es necesario colocar a ADMINS)
MAIL_ADMIN = Coloque el @ del administrador general del bot para varias acciones.
MAILDIR = Coloque un correo de electrónico para el bot
MAILPASS = Coloque la contraseña del correo anterior
MAIL_SERVER = Coloque la configuración del smtp de la manera servidor_smtp:puerto:seguridad , ejemplo, con un correo @disroot.org colocar disroot.org:587:tls
MAIL_MB = Cloque un límite hasta de 20MB para el envio de multimedia en el bot, cada usuario puede cambiar este valor luego para ellos. Si el limite se supera, la multimedia se comprime en partes.
MAIL_DELAY = Establece una duración en segundos del delay entre el envio de partes de archivos al bot.
MAIL_CONFIRMED: Establece una lista de confianza de correos a usuarios de confianza, estos no tendrán que verificar su correo, llenar de la manera "UserID1=correo@user.uno;correo2@user.uno,UserID2=correo@user.dos"
IMGAPI = Coloque su API de Imgchest para publicar fotos con el comando /imgchest
```

### Activar comandos

Las variables de entorno **ACTIVE_CMD** o **ADMIN_CMD** no son necesarias para el arranque del bot, pero sin ellas el bot es inutil.
Introdusca en esta variable, separado por comas, los nombres de los archivos de la carpeta [command](https://github.com/nakigeplayer/nekobot-pyrogram/tree/main/command)  para que el bot use estos comandos.
Los **ACTIVE_CMD** son comandos para todos mientras **ADMIN_CMD** son comandos para admin

```
all - permite el uso de todos los comandos
videotools - permite el uso de /convert y /calidad
mailtools - permite el uso de /sendmail y /setmail
filetools - permite el uso de /rename, /compress y /setsize
htools - permite el uso de /nh , /3h , /covernh y /cover3h
webtools - permite el comando de /scan , /multiscan y /resumecodes
imgtools - permite el uso del comando /imgchest
```


## Comandos del bot

Envie esto a BotFather para configurar los comandos:
```
start - Comprobar actividad  
setsize - Defina el tamaño en Mb para /compress (Default: 10MB)  
compress - Comprimir un archivo en partes  
rename - Cambia el nombre de un archivo  
convert - Convierte un video  
calidad - Ajusta la calidad de /convert  
setmail - Configure su correo para usar /send  
sendmail - Envía un archivo a su correo
verify - Verifica tu correo con un código
setfile - Define su preferencia de descarga de Hentai
nh - Descarga un manga hentai de Nhentai
3h - Descarga un manga hentai de 3Hentai
covernh - Obtener info de un manga hentai de Nhentai
cover3h - Obtener info de un manga hentai de 3Hentai
scan - Escanea los links dentro de un link indicando
resumecodes - Extrae codigos Hentai de archivos txt del scan
imgchest - Publica una imagen en Imgchest
access - Obten acceso al bot mediante una contraseña
```

## Comandos admin
```
adduser - Permite a un usuario usar el bot
remuser - Quita el acceso
addchat - Permite al chat actual el uso del bot
remchat - Quita el acceso
ban - Banea a un usuario 
unban - Desbanea a un usuario 
```
