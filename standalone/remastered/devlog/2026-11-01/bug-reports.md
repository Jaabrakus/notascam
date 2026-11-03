# Bug reports, 11-01

Players can now report bugs from **Settings › Report a bug**, and the game also catches errors by itself. Every report
lands on a new **Bugs** tab on the Admin page. Players can type anything into a report, so the system is built not to
trust what they type. Only bugs an admin confirms are written to a file for Claude, and the players' words in it are
marked untrusted.

## Done

- **Report a bug** (Settings, on the public server; guests too):
  - The form asks what kind of bug it is, what went wrong, and what the player was doing.
  - "Add what the game knows" is on by default. The server then adds where they are, their selected units (health,
    job, what each is doing), the last 20 lines of their village log, and any server errors from just before.
  - The browser adds its screen size, frame rate and any errors the page hit. These are shown separately and labelled
    as hints, because a player's own browser could fake them.
- **Errors caught by themselves:**
  - **Page errors:** each different one is sent once per page load, at most 10.
  - **Server errors:** the game catches its own runtime errors as they happen.
  - Repeats of the same error share one row on the Bugs tab, with a count, the players it hit, and when it was first
    and last seen.
  - A row marked Fixed that comes back in a later build opens again, marked "came back after a fix".
- **The Bugs tab** (Admin page): newest first, with new ones counted on the tab and on the Admin button. Each row has
  Go to, Details, Seen, Not a bug, Duplicate and Reopen buttons. Admins and the owner can also Confirm and Fix.
  - **Fixed:** the player who reported it is told, straight away or at their next log-in.
  - **Confirmed:** the bug is written to `bugs-confirmed.jsonl` beside the saves, for Claude to work from.
- **Guards** (the owner: "people could inject nefarus things right?"):
  - **A person checks first.** Nothing reaches Claude's file until an Admin confirms it.
  - **Untrusted text is marked.** In that file, anything players or their browsers wrote sits under "untrusted" with a
    warning that it is never an instruction. That includes unit names and log lines.
  - **Claude only fixes code.** It never acts on what a report says. It changes the game's code, tests it, and ships
    the usual way.
  - **Text is cleaned and capped.** Markup and control characters are stripped from every typed field, and lengths
    are capped (1,000 characters for what went wrong).
  - **The word list applies.**
  - **Everything shows as plain text.** In a test, a report written as page code showed on the Admin page as words
    and ran nothing.
  - **Limits:** 5 reports an hour per player, and 20 page errors an hour per player. Muted and banned players can't
    send.
  - **Size:** at most 300 reports and 200 error rows are kept, and the oldest closed ones go first.

![The report form in the overlay HUD](img/bug-reports-form.png)

![The Admin page's Bugs tab: a report opened with its details, a server error seen 14 times, and a hostile report shown as plain text](img/bug-reports-admin-tab.png)
