# The server's native libraries for Apple silicon

`tools/build_app.py` builds `runtime/server-arm64` in the app from `runtime/server`. These two libraries replace that
folder's x86-64 builds, and `Robust.Server.dll` and `Robust.Packaging.dll` are marked arm64 (they are pure IL, published
marked x86-64). `mac-app/launch.zsh` runs the server from it, on Apple silicon's own .NET (`runtime/dotnet-arm64`), when
the Mac is arm64. Intel Macs run today's server. Measured in load-asleep-1030 (`reports/load-asleep-1030/README.md`).

| file | from (nuget.org, the owner's OK 10-31) | sha256 |
|---|---|---|
| `libzstd.1.dylib` | `robust.natives.zstd` 0.1.1-zstd1.5.7, `runtimes/osx-arm64/native/` (the version the bundled server uses) | `cf0b84cae16a45b9...` |
| `libe_sqlite3.dylib` | `sourcegear.sqlite3` 3.50.4.2, `runtimes/osx-arm64/native/` (the version the bundled server uses) | `7b319cd32435ab28...` |
