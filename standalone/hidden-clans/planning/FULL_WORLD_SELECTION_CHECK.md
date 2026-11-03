# Full-world selection and movement evidence

The October 17 [verified report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-selection-verified-checks.json) passes **23/23 assertions** using all four original maps, the unmodified copied DME/game source, original world startup, and the original three-Human starting army. The private compile had 288 existing warnings and no errors. No server/client errors, unexpected native input, threat interruption or source changes occurred during the accepted recording.

The recorded client dispatch selected exactly the intended Human. Its original `mob.dmi` selection marker appeared in the real map framebuffer: 39 additional red marker pixels over that unit, zero over the other two. A second dispatch hit the intended ground turf. The selected Human moved north one tile, while the other two remained in place without receiving work. The renderer recorded four actual glide samples with walking frames 1 and 2, followed by 167 stationary samples holding North, frame 0 and movement inactive. The other two units held their original facing. The marker remained attached to the selected unit after arrival.

## What the input proof covers

[NativeUiProbe.cs](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/mac-webview/NativeUiProbe.cs:58) adds an opt-in diagnostic action that targets the private client's actual `ControlMap.OnViewportKeyBindEvent`. Down/up reach the original `MouseInputSystem`, rendered pixel hit map and network `AtomClickedEvent` path. The probe checks the expected entity/turf before dispatch and records a receipt. The two accepted hit receipts are in the report and [raw click log](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-selection-fixed-map-clicks.jsonl).

This is **client map callback input**, with no direct game procedure calls for selection or movement. It bypasses physical OS event delivery and focus handling; it is not a physical mouse or mobile-touch test. The existing startup smoke driver invokes the original Restart command and answers the original race prompt using client callbacks. No production DM fixture, constructor override, AI freeze or defense override is used. All state, renderer frames and client-image observations are read-only.

The module was built only at `/tmp/dm-runtime-audit/full-world-webview` and mounted by the private client. Its source includes the current unchanged `MacWebViewManager.cs`. The canonical module, packaged app and normal saves were untouched. The private client/server are stopped and port 12183 is released.

## Preserved failures and reanalysis

The older [full-game report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-game-selection-checks.json) is inconclusive: it used global AppKit focus/mouse input, its eventual selection changed to all three units, and a Chop task appeared away from the requested move. Those observations cannot establish a clean one-unit move.

The replacement's [first run](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-selection-internal-checks.json) safely rejected its move before sending it because the harness incorrectly expected zero-based turf coordinates. The renderer's turf coordinates match DM coordinates; that expectation is corrected.

The [second native recording](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-selection-fixed-checks.json) observed the successful move, but its old completion check waited for the literal display text `Idle`. Completed Move deliberately retains `Arrived` while active/pending work is empty. The corrected harness checks target position, no active/pending work, and no pause/block. The verified report reanalyzes the preserved [HUD/renderer evidence](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-selection-fixed-animation.jsonl); no additional native run was needed. Both original reports remain unchanged, and the verified report records the source report's hash and the analysis harness hash.

The focused [harness](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_full_game_selection.py) requires every named assertion, uses actual viewport dimensions, and distinguishes a world threat interruption from an unexplained idle/input failure. Normal defense remains enabled. It checks the gameplay and renderer in a copied full world; packaged launcher and save/reload lifecycle have separate tests.

For the next integrated run, use a fresh label; the harness refuses to overwrite an existing label's artifacts:

```sh
python3 standalone/remastered/tools/check_full_game_selection.py \
  --label full-world-selection-integrated \
  --webview-dir /tmp/dm-runtime-audit/full-world-webview \
  --port 12183
```

Optional `--server-dir`, `--client-zip` and `--client-assemblies-dir` accept staged candidate runtime/client artifacts. The server, selected client package and WebView module are copied privately; client assembly overrides change only the copied ZIP. A mismatched client/server Shared DLL is rejected before launch. `--reanalyze SOURCE_LABEL --label NEW_LABEL` reads preserved evidence without launching anything; its narrow recovery supports the documented `Arrived` display-status mismatch only.

Recorded artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Runtime | `42ae02df4875cc96f12d5818280bd12be2551a6fe94643d0728a7969eb1e7299` |
| Shared | `9d35743ac9936e5c18e7f1a8a3d526f554aac7e892378e7806c820b0722237f0` |
| Mounted client DLL | `c591a024a2990fe5b9c5d6d1c8c4c5e5d2017f61f883efb3144be93349ccea30` |
| Staged diagnostic WebView | `a1e402420655450cebc3ba0c8118c32b997856058a5d5fcfc0d93dadd702b5af` |
| Verified report | `0d83fa60f426337c827896c8fdb29cadad52b9d55ff41152193407798c1937b0` |
