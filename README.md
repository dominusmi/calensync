# Calensync

Calensync was created in order to solve a simple but very annoying problem: make sure that all my (many) Google calendars were synchronized, so that myself, collaborators, and services such as Calendly could easily know when to arrange meetings.

On top of it, it was always made to be privacy-first. Events are not copied to other calendars, but instead an event named `Busy` is created instead. It's just supposed to act as a blocker, not to share all my personal information with the world!


## Contribute

### Code
You're welcome to contribute by creating a fork and, when finished, a PR.

### Request
If you have a request, please either create an issue or email at me@edoardobarp.com 

## Possible features
1. Currently it only allows one cross-sync, that is all the calendars are synced together, you can't decide to sync A+B and independently B+C.

2. It would be nice to include other calendar sources, especially Outlook. I personally don't use it but I'm sure many people do.

3. Add a "buffer" to events, possibly only on certain calendars. For example, you could imagine all events in calendar A have an automatic +15minutes buffer, but not events from calendars B and C.