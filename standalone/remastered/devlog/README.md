# Devlogs

What each session did, in bullet points with pictures, so the user can catch up in the morning. Asked for by the user on
2026-10-24: "have them create devlogs of what their doing with reports in bulletpoints and pictures so i can see in the
morning put it in a devlog folder from now on".

## Layout

```
devlog/
  2026-10-24/                 one folder per day (the local date the work happened)
    README.md                 the coordinator's summary of the day: what landed, numbers, decisions waiting
    <session>.md              one file per session, e.g. server-cost.md, world-look.md, jobs.md
    img/<session>-<what>.png  pictures for that file
```

## Each session's file

- Start with a 2–3 line summary: what changed for the player.
- Then **Done**, **Numbers**, **In progress**, **Needs the user**, as bullet points. Plain words, no code.
- Numbers as before → after tables, with the test that measured them (units, speed, arena or real window).
- Pictures: real window captures (`screencapture -l <window id>`) or WKWebView captures of the 3D view and HUD, never the
  2D engine framebuffer (it doesn't show the 3D layer). Charts of numbers are welcome (PNG or SVG). Link them as
  `![what it shows](img/<session>-<what>.png)` and say in one line what to look at.
- Add to your file as you go (newest at the top of each section). Don't edit other sessions' files.
- Keep pictures small (under ~500 KB each; downscale with `sips -Z 1400`).
