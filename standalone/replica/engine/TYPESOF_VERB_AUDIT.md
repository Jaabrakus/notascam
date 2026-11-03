# Original verb-group grants

The shared runtime omitted the commands returned by `typesof(/Targeting/verb/)` during the original Login. It also omitted the datum-like Admin, Clan, TurfCreate, and MiscCreate groups. Mob-based groups incorrectly included inherited commands. This is an engine enumeration defect; no Login workaround or permission change is needed.

## Reference evidence

BYOND documents `typesof()` as a way to list types, procs, and verbs, including the pattern of adding a command group's verbs at runtime. [Official DM reference](https://www.byond.com/docs/ref/info.html#/proc/typesof).

The same isolated fixtures run in BYOND 516.1655 and the replacement engine establish the details used by this fix:

- A verb group returns its directly declared verbs, excluding inherited verbs and overrides of existing parent verbs.
- A proc group returns directly declared non-verb procs. It must not include verbs.
- Path constants and equivalent strings produce the same enumeration. A trailing slash is accepted. Missing paths, null, lists, numbers, and a single explicit proc/verb reference produce empty lists.
- Multiple arguments preserve their order and repeated results. Ordinary type and object-instance descendant enumeration is unchanged.

The current compiler already lowers `ConstantProcStub` to a string. There is no separate runtime ProcStub value to support. Extra `/Targeting/verb` type entries in compiled JSON do not establish the representation used by this call. The actual proc metadata retains `IsVerb=true`, while `ObjectDefinition.Verbs` is the list of automatically granted instance verbs and can be absent for a datum-like command group.

Actual source groups compare exactly, including order:

| Group | BYOND | Previous runtime | Candidate |
| --- | ---: | ---: | ---: |
| Targeting | 1 | 0 | 1 |
| Admin | 44 | 0 | 44 |
| Clan | 2 | 0 | 2 |
| TurfCreate | 34 | 0 | 34 |
| mob/Spawn | 21 | 69 | 21 |
| MiscCreate | 23 | 0 | 23 |
| mob/Developer | 4 | 52 | 4 |

The original `P.verbs += typesof(/Targeting/verb/)` expression now adds `/Targeting/verb/SetTarget` without explicit game-side insertion. Original role checks still decide whether the admin and clan expressions run.

## Narrow implementation

Only the string group branch of `NativeProc_typesof` changes. It enumerates `ObjectDefinition.Procs.Values` filtered by the proc's `IsVerb` flag, excluding the inherited auto-grant table and `OverridingProcs`. Trailing slashes are normalized, retaining the ordinary one-character `/` path. Invalid strings yield no entries. The compiler, object-tree loader, client, game Login, and original grant conditions remain unchanged.

Private candidate runtime: `f81a365897c80b9cbb748ba821d6c6a4e3f77760465fee17c18c62fba87d060d`.

The [focused checker](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_typesof.py) retains 48 behavioral comparisons plus source/runtime/no-save checks. The [baseline](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/typesof-before-verified-checks.json) fails 38 comparisons; the [final candidate](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/typesof-final-candidate-checks.json) passes all 52 reported checks with no server/world errors (headless, no client launched). BYOND reference runs and exact fixtures are retained under [reference/typesof](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/typesof).

The fixture renames the unused older duplicate `StopAll` definition in both private real-game copies solely because BYOND rejects that existing duplicate. It replaces world startup for the headless enumeration fixture. All declarations being enumerated remain original. The separate native acceptance keeps original Login and world startup.

## Native original-Login acceptance

The final candidate passes [15/15 native checks](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/typesof-login-verified-checks.json) with all four original maps, original Login, original admin declarations, and original world startup unchanged. The existing opt-in race smoke driver invokes Restart and answers its original Human prompt through internal client callbacks. The resulting three starting Humans have no magic target assigned.

The observer confirms that Login grants SetTarget. The native client reports it as executable and as valid for the genuine Human target. Constructing and opening the original `VerbMenuPopup` produces its **SetTarget** button; [native framebuffer](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/typesof-login-verified-menu.png). The observer does not select that button or invoke the verb.

This ordinary player remains `GM=0`, `DE=0`, and not a clan leader, with zero admin or clan verbs granted. Client, server, and world error scans are empty. No OS input or incidental map callback occurred, no private save was created, and all private processes stopped. The native inspection is not a claim of OS right-click delivery; that client path is covered by the separate retained context-menu tests.

Exact handoff paths and hashes: [staging manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/typesof-staging.json). The private diagnostic module is test-only and must not replace the product WebView module. The only product source candidate is the retained runtime builder patch, with its resulting runtime DLL; client/shared assemblies remain unchanged.

## Explicit limit

Root-level `/proc` enumeration remains incomplete and is excluded from the 48 behavioral pass claims. The oracle returns the user global proc declarations; this runtime returns an empty list. No included game call uses that form. This increment fixes original command-group grants without expanding into global-proc registration metadata.

## Re-run

```sh
python3 standalone/replica/tools/check_typesof.py \
  --server /tmp/dm-runtime-audit/typesof-server \
  --label typesof-rerun --port 12193 \
  --reuse-reference standalone/replica/reference/typesof/before-verified
```

Omit `--reuse-reference` to rerun the local BYOND reference container. The [native Login checker](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_typesof_login.py) uses a private full map, profile, runtime copy, and diagnostic module; no OS input or normal save path is used.
