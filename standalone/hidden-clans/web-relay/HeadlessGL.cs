// A headless Robust client still asks OpenGL one question while preloading sprite
// sheets (GL.GetInteger(MaxTextureSize) in ResourceCache.PreloadRsis, unconditional in
// release builds). Without a window there are no bindings and start-up throws. This
// installs stub bindings: glGetIntegerv answers 4096, every other entry point does
// nothing. Nothing draws in a relay client, so nothing else should reach OpenGL.
using System;
using System.Runtime.InteropServices;
using OpenToolkit;
using OpenToolkit.Graphics.OpenGL4;

namespace Robust.Client.WebView;

internal static unsafe class HeadlessGL {
    [UnmanagedCallersOnly]
    private static void GetIntegerv(int name, int* data) {
        if (data != null) *data = 4096;
    }

    [UnmanagedCallersOnly]
    private static void Nothing() { }

    private sealed class Stub : IBindingsContext {
        public IntPtr GetProcAddress(string procName) =>
            procName == "glGetIntegerv" ? (IntPtr)(delegate* unmanaged<int, int*, void>)&GetIntegerv : (IntPtr)(delegate* unmanaged<void>)&Nothing;
    }

    public static void Install() {
        GL.LoadBindings(new Stub());
        RelayWebViewManager.Log("headless: stub OpenGL bindings installed");
    }
}
