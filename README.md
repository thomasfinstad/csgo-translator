# Installation / Usage
Download the binary from the releases page and place it into your "Counter-Strike Global Offensive" folder.
Default locations:
* Linux: `~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/`
* Windows: `C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive`

Put this in your autoexec.cfg file, or typing it into the console, or adding it as a launch option: `con_logfile console.log`

To view the translated text type this into your console: `exec csgo-translate`

To make it easier to view translated text you can bind it to a key:

`
alias trans "exec csgo-translate; toggleconsole"
bind "F5" "trans"
`

To start the translator either doubleclick it, or run it in a terminal window.

This might not work on windows, but on windows you can just create a shortcut on your desktop and start it before you start the game.

To autostart it by using launch parameters on csgo: `csgo-translator &; %command%;`
Steam will replace %command% with the command used to start the game, so if you wish to have launch options enabled simply all them after that eg: `csgo-translator &; %command% -novid -console +con_logfile console.log;`


# CHANGELOG:
## beta1
initial commit and flowing changes until it has an ok level of bugs
