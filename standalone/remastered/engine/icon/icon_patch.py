# Remastered: icon.Crop() (an upstream stub that did nothing), exec'd by tools/build_runtime.py's ICON block (--icon-crop,
# on by default since 2026-10-30). BYOND's: the box x1,y1 to x2,y2, 1,1 the bottom left; it may reach past the icon,
# which is transparent there; the icon becomes that size. Every operation so far (Blend, Shift, MapColors...) is baked in
# first, then each frame is cut, so later operations see the cut frames. The game used none before it (the race
# portraits are its first user, HUD.dm RemasterPortraitFit).
# FILES: path under src -> [(old, new, count)], applied in order.

FILES = {
    'Procs/Native/DreamProcNativeIcon.cs': [
        ('''        public static DreamValue NativeProc_Crop(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
            // TODO
            return DreamValue.Null;
        }
''', '''        public static DreamValue NativeProc_Crop(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
            // Remastered: BYOND's crop (engine/icon/icon_patch.py)
            if (!bundle.GetArgument(0, "x1").TryGetValueAsInteger(out var x1) || !bundle.GetArgument(1, "y1").TryGetValueAsInteger(out var y1) ||
                !bundle.GetArgument(2, "x2").TryGetValueAsInteger(out var x2) || !bundle.GetArgument(3, "y2").TryGetValueAsInteger(out var y2))
                return DreamValue.Null;

            ((DreamObjectIcon)src!).Icon.RmCrop(x1, y1, x2, y2);
            return DreamValue.Null;
        }
''', 1),
    ],
    'Objects/DreamIcon.cs': [
        ('''    public void ApplyOperation(IDreamIconOperation operation) {
''', '''    /// <summary>
    /// Remastered (engine/icon/icon_patch.py): icon.Crop, as BYOND's. The box x1,y1 to x2,y2 (1,1 the bottom left) of
    /// every frame, transparent where it reaches past the icon; the icon becomes that size. The operations so far are
    /// baked into the frames first (GenerateDMI), so the icon starts again from the cut frames with none pending.
    /// </summary>
    public void RmCrop(int x1, int y1, int x2, int y2) {
        if (x2 < x1) (x1, x2) = (x2, x1);
        if (y2 < y1) (y1, y2) = (y2, y1);
        int width = x2 - x1 + 1, height = y2 - y1 + 1;
        var baked = GenerateDMI();
        int oldWidth = baked.DMI.Width, oldHeight = baked.DMI.Height;
        var source = baked.Texture;
        int frameCount = 0;
        foreach (var state in States.Values)
            foreach (var frames in state.Directions.Values)
                frameCount += frames.Count;

        var cut = new Image<Rgba32>(Math.Max(width * frameCount, 1), height);   // transparent to start with
        var newStates = new List<((string Name, bool Movement) Key, IconState State)>(States.Count);
        int at = 0, current = 0;
        foreach (var (key, state) in States) {
            // where GenerateDMI put each frame: a state's frames after the last state's, its directions interleaved
            var newState = new IconState { Frames = state.Frames, Movement = state.Movement, Rewind = state.Rewind, SingleFrameDelay = state.SingleFrameDelay };
            int directions = DMIParser.GetExportedDirectionCount(state.Directions);
            for (int d = 0; d < directions; d++) {
                var dir = DMIParser.DMIFrameDirections[d];
                if (!state.Directions.TryGetValue(dir, out var frames))
                    continue;

                var newFrames = new List<IconFrame>(frames.Count);
                for (int k = 0; k < frames.Count; k++) {
                    // the box in the frame: BYOND's y counts up from the bottom, the image's down from the top
                    int frameX = (current + d + k * directions) * oldWidth;
                    int left = frameX + x1 - 1, top = oldHeight - y2, destX = at * width;
                    for (int y = 0; y < height; y++) {
                        int sy = top + y;
                        if (sy < 0 || sy >= oldHeight || sy >= source.Height) continue;
                        for (int x = 0; x < width; x++) {
                            int sx = left + x;
                            if (sx < frameX || sx >= frameX + oldWidth || sx >= source.Width) continue;
                            cut[destX + x, y] = source[sx, sy];
                        }
                    }

                    newFrames.Add(new IconFrame(cut, new ParsedDMIFrame { X = destX, Y = 0, Delay = frames[k].DMIFrame.Delay }, width, height));
                    at++;
                }

                newState.Directions[dir] = newFrames;
            }

            current += state.Frames * directions;
            newStates.Add((key, newState));
        }

        States.Clear();
        foreach (var (key, state) in newStates)
            States.Add(key, state);
        Width = width;
        Height = height;
        _operations.Clear();
        _cachedDMI = null;
    }

    public void ApplyOperation(IDreamIconOperation operation) {
''', 1),
    ],
}
