# Required prompt selection audit

The installed client at the start of this audit could leave the real Potion and Guard menus stuck after tapping the already selected first option. A private candidate fixes this in `ListPrompt` only. It has not been promoted by the sprite agent; the lead owns installation.

## Reproduction and result

The real Potion menu starts with **Drop** selected. The real Guard menu starts with **Guard On** selected. Robust `ItemList` single-selection mode toggles that selection off when tapped again. `ListPrompt.OkButtonClicked()` then finds no selected row and sends no result. The original game handler remains suspended. Explicitly choosing another row, including Cancel, still works.

| Same private native fixture | Result |
| --- | --- |
| Installed client `9a0a190a` | 45/51 checks pass; both default-row selections, exact selected index checks, and requested game effects fail |
| Candidate client `5481500f` | 51/51 checks pass |

The candidate completes the real `RemasterInventoryUse` Drop handler and real Guard On handler after tapping the default row and pressing OK. It also verifies Potion Inspect and Cancel, Guard Off through the original `TextSubmit` handler, scrolled Guard Cancel, Rename accept/cancel, Crown No, nullable-list Cancel, number-input Cancel, and empty-list early return. Selecting a row does not submit the prompt. Active and pending order objects, paused state, and selection survive these interactions as expected.

Both runs have zero client, server, or world-log errors. No OS keyboard or mouse event was injected or observed, no save was created, and both private client/server pairs stopped. Only internal UI hit-testing/focus/click callbacks targeted the isolated native window. Text replacement uses the existing setter; Enter is tested at the `ItemList.KeyBindDown(TextSubmit)` boundary. These are not claims of physical typing, mobile OS touch routing, or native keyboard dispatch parity.

Evidence: [before checks](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/prompt-selection-before-checks.json), [candidate checks](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/prompt-selection-candidate-checks.json), [retained runner](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_prompt_touch.py), and [real-handler fixture](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/prompt_selection_probe.dm). The earlier minimal [verified reproduction](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/prompt-touch-verified-checks.json) is preserved separately.

## Narrow candidate

[PatchPromptSelection.cs](/tmp/dm-runtime-audit/prompt-touch-release/engine/PatchPromptSelection.cs) attaches one deselection callback to a `ListPrompt` only when `canCancel` is false. If deselection leaves no selected row, it restores that same row. When switching rows, the new row is already selected before the previous row's deselection event, so the previous row stays deselected. The static prompt never removes or disables its rows after construction.

No global `ItemList` code, numeric response index, OK callback, nullable prompt behavior, or game handler changes. No callback invokes `FinishPrompt` or a verb. Nullable lists retain their existing cancellation path. The original constructor default, keyboard-submit handler, and text focus fixes remain in the full retained client patch chain. Independent teammate source review found no blocker in this event ordering or lifetime.

The candidate is built from the upstream client through every retained compatibility patch, with this patch added after the context-menu fix. Its shared assembly is byte-identical to the installed `9d35743a` shared assembly. The server remains `783f6ad2`. Exact source, artifact, and test hashes are in the [staging manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/prompt-selection-staging.json); [source diff](/tmp/dm-runtime-audit/prompt-touch-release/release/source.patch) is self-contained. Canonical source and installed artifacts remained unchanged during the audit.

## Remaining measured limits

- At UI scale 1, native list rows are 26 pixels high and buttons 29 pixels high. The Potion prompt is 300×196; Guard is 300×300 and its final Cancel row requires scrolling. This candidate does not resize native controls for touch.
- Calling `OSWindow.Close()` on nullable Rename leaves the unfinished prompt open; its explicit Cancel works. This is preserved and reported as a separate existing behavior.
- This test does not establish arrow-key navigation, physical touch behavior, invalid-number validation, or all prompt types. No broader prompt redesign is included.

## Re-run

Use a fresh report label and a free private port. The candidate DLL is substituted only in a copied client ZIP, and the diagnostic module is copied into the private run. The normal profile is never opened.

```sh
python3 standalone/remastered/tools/check_prompt_touch.py \
  --module /tmp/dm-runtime-audit/prompt-touch-stage/module \
  --client /tmp/dm-runtime-audit/prompt-touch-release/build/OpenDreamClient.dll \
  --selection-contract --label prompt-selection-rerun --port 12197
```

Omit `--client` to test the currently installed client. The private diagnostic source is retained in [reference/prompt-touch/selection](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/prompt-touch/selection). It adds only opt-in kind-20 prompt callbacks under `DM_NATIVE_UI_PROBE`, with an exact private-window title check. It is not an app module installation candidate.
