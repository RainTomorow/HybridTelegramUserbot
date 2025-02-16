# HybridTelegramUserbot

_Disclaimer: this software is provided AS IS and was built completely for my own personal needs and uploaded in a convenient (for me) form_
_Still it's quite readable, self-explaining, editable, portable etc_

The main idea of this software is to combine two telegram userbot libraries:

* [Telethon](https://github.com/LonamiWebs/Telethon)
* [Pyrogram (I use this fork)](https://github.com/KurimuzonAkuma/pyrogram)

As I live in Ukraine, I needed a bot that reads text from air raid monitoring channels and alerts me when there is a treat for my city, so I can afford Sleep.
But neither Telethon nor Pyrogram could worked well:
* Telethon is very stable but have a lot of seconds delay in receiving messages, which can be quite dangerous
* Pyrogram have great speed of message receiving, but just stops working from time to time and needs to be restarted

That's why I combined them - Pyrogram is doing the main work as it's very fast (sometimes I hear alert before Telegram's GUI displays the message), and Telethon is like a watchdog that temporarily replaces Pyrogram when it's down and restarts it.
And the implemented logic makes them to works as a single program without duplicating the alerts.
Feel free to share the ideas on improvements, to remake them for your own purposes etc.

Here is an example of keyword filters in Google Sheets:
![image](https://github.com/user-attachments/assets/0f273972-e3eb-47ee-bae5-db5fef7071c2)
