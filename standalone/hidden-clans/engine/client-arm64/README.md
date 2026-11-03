# The game window's native libraries for Apple silicon

`tools/build_app.py` puts these five in `runtime/client-arm64` in the app, with the server's arm64 `libzstd.1.dylib` and
`libe_sqlite3.dylib` (`engine/server-arm64/`, the same versions the client ships) and `Robust.Client.dll` marked arm64
(pure IL, published marked x86-64). On an arm64 Mac `mac-app/launch.zsh` lays them over the player's copy of the client
and runs the window on Apple silicon's own .NET (`runtime/dotnet-arm64`), with the arm64 WebKit bridge
(`engine/webview-webkit-arm64`, built by `tools/build_webview.py` from `mac-webview/WebKitBridge.swift`). Intel Macs run
today's window. `libswnfd.dylib` has no arm64 build; the client never loads it. Measured in load-asleep-1030
(`reports/load-asleep-1030/README.md`).

Each file is the `runtimes/osx-arm64/native/` build from the same nuget.org package as the x86-64 one the client ships
(those match byte for byte); downloaded with the owner's OK, 10-31.

| file | package | sha256 |
|---|---|---|
| `libSDL3.0.dylib` | `robust.natives.sdl3` 0.1.3-sdl3.4.8 | `cd27c27036db1f06...` |
| `libopenal.1.dylib` | `robust.natives.openal` 0.2.1-openal1.24.3 | `f2d4f978a34a05f4...` |
| `libfluidsynth.3.dylib` | `robust.natives.fluidsynth` 0.2.1-fluidsynth2.4.6 | `268559e73a759e39...` |
| `libfreetype.6.dylib` | `robust.natives.freetype` 0.2.1-freetype2.13.3 | `75290ac6b21bc28c...` |
| `libglfw.3.dylib` | `robust.natives.glfw` 0.2.1 | `0a94486b7fc61d60...` |
