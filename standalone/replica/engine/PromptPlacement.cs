using System;
using System.Runtime.InteropServices;
using SDL3;

// Imported into Robust.Client. Only OSWindow.CenterInitialPromptOnOwner queues
// this operation, after PromptWindow has applied its final scaled layout.
internal sealed class PromptPlacement {
    private readonly nint child;
    private readonly uint childId;
    private readonly nint owner;
    private readonly uint ownerId;

    public PromptPlacement(nint child,uint childId,nint owner,uint ownerId) {
        this.child=child;this.childId=childId;this.owner=owner;this.ownerId=ownerId;
    }

    public void Execute() {
        // Window commands execute in order. Validate the original SDL identity
        // again in case either window was destroyed before this command ran.
        if(child==0 || owner==0 || SDL.SDL_GetWindowFromID(childId)!=child || SDL.SDL_GetWindowFromID(ownerId)!=owner)return;
        if(WindowParent(child)!=owner)return;
        var display=DisplayForWindow(owner);
        if(display==0 || !DisplayUsableBounds(display,out var bounds))return;
        if(!SDL.SDL_GetWindowPosition(owner,out var ox,out var oy) || !SDL.SDL_GetWindowSize(owner,out var ow,out var oh))return;
        if(!SDL.SDL_GetWindowSize(child,out var w,out var h))return;
        int top=0,left=0,bottom=0,right=0;
        if(!WindowBordersSize(child,out top,out left,out bottom,out right))top=left=bottom=right=0;
        var x=CenteredAxis(ox,ow,w,left,right,bounds.x,bounds.w);
        var y=CenteredAxis(oy,oh,h,top,bottom,bounds.y,bounds.h);
        SDL.SDL_SetWindowPosition(child,x,y);
    }

    // SDL window positions/sizes and usable display bounds share desktop
    // coordinates; framebuffer pixel density must not be applied here.
    public static int CenteredAxis(int ownerOrigin,int ownerSize,int childSize,int before,int after,int usableOrigin,int usableSize) {
        var minimum=usableOrigin+Math.Max(0,before);
        var maximum=usableOrigin+usableSize-childSize-Math.Max(0,after);
        if(maximum<minimum)return minimum; // Oversize content needs UI scrolling.
        return Math.Clamp(ownerOrigin+(ownerSize-childSize)/2,minimum,maximum);
    }

    // These four SDL entry points are present in the bundled native library,
    // but were trimmed out of its managed binding. Keep their minimal ABI here;
    // byte represents SDL3's C bool and avoids platform BOOL marshalling.
    private static nint WindowParent(nint w) => OperatingSystem.IsMacOS()?MacParent(w):OperatingSystem.IsWindows()?WinParent(w):UnixParent(w);
    private static uint DisplayForWindow(nint w) => OperatingSystem.IsMacOS()?MacDisplay(w):OperatingSystem.IsWindows()?WinDisplay(w):UnixDisplay(w);
    private static bool DisplayUsableBounds(uint d,out SDL.SDL_Rect r) => (OperatingSystem.IsMacOS()?MacBounds(d,out r):OperatingSystem.IsWindows()?WinBounds(d,out r):UnixBounds(d,out r))!=0;
    private static bool WindowBordersSize(nint w,out int t,out int l,out int b,out int r) => (OperatingSystem.IsMacOS()?MacBorders(w,out t,out l,out b,out r):OperatingSystem.IsWindows()?WinBorders(w,out t,out l,out b,out r):UnixBorders(w,out t,out l,out b,out r))!=0;
    [DllImport("libSDL3.0.dylib",EntryPoint="SDL_GetWindowParent",CallingConvention=CallingConvention.Cdecl)]
    private static extern nint MacParent(nint w);
    [DllImport("libSDL3.0.dylib",EntryPoint="SDL_GetDisplayForWindow",CallingConvention=CallingConvention.Cdecl)]
    private static extern uint MacDisplay(nint w);
    [DllImport("libSDL3.0.dylib",EntryPoint="SDL_GetDisplayUsableBounds",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte MacBounds(uint d,out SDL.SDL_Rect r);
    [DllImport("libSDL3.0.dylib",EntryPoint="SDL_GetWindowBordersSize",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte MacBorders(nint w,out int t,out int l,out int b,out int r);
    [DllImport("SDL3",EntryPoint="SDL_GetWindowParent",CallingConvention=CallingConvention.Cdecl)]
    private static extern nint WinParent(nint w);
    [DllImport("SDL3",EntryPoint="SDL_GetDisplayForWindow",CallingConvention=CallingConvention.Cdecl)]
    private static extern uint WinDisplay(nint w);
    [DllImport("SDL3",EntryPoint="SDL_GetDisplayUsableBounds",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte WinBounds(uint d,out SDL.SDL_Rect r);
    [DllImport("SDL3",EntryPoint="SDL_GetWindowBordersSize",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte WinBorders(nint w,out int t,out int l,out int b,out int r);
    [DllImport("libSDL3.so.0",EntryPoint="SDL_GetWindowParent",CallingConvention=CallingConvention.Cdecl)]
    private static extern nint UnixParent(nint w);
    [DllImport("libSDL3.so.0",EntryPoint="SDL_GetDisplayForWindow",CallingConvention=CallingConvention.Cdecl)]
    private static extern uint UnixDisplay(nint w);
    [DllImport("libSDL3.so.0",EntryPoint="SDL_GetDisplayUsableBounds",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte UnixBounds(uint d,out SDL.SDL_Rect r);
    [DllImport("libSDL3.so.0",EntryPoint="SDL_GetWindowBordersSize",CallingConvention=CallingConvention.Cdecl)]
    private static extern byte UnixBorders(nint w,out int t,out int l,out int b,out int r);
}
