import AppKit
import WebKit
import Darwin

public typealias EventCallback = @convention(c) (Int64, Int32, Int64, UnsafePointer<CChar>?) -> Void
private var callback: EventCallback?
private var panels: [Int64: Panel] = [:]
private var nextPanel: Int64 = 0
private typealias GetWindow = @convention(c) (UInt32) -> UnsafeMutableRawPointer?
private typealias GetProperties = @convention(c) (UnsafeMutableRawPointer?) -> UInt32
private typealias GetPointer = @convention(c) (UInt32, UnsafePointer<CChar>?, UnsafeMutableRawPointer?) -> UnsafeMutableRawPointer?
private var getWindow: GetWindow?
private var getProperties: GetProperties?
private var getPointer: GetPointer?
private typealias WarpMouse = @convention(c) (UnsafeMutableRawPointer?, Float, Float) -> Void
private var warpMouse: WarpMouse?

private func emit(_ panel: Int64, _ kind: Int32, _ request: Int64, _ text: String) {
    text.withCString { callback?(panel, kind, request, $0) }
}
private func originalURL(_ url: URL) -> String {
    let value = url.absoluteString
    return value.hasPrefix("dm-resource:") ? "http:" + value.dropFirst("dm-resource:".count) : value
}
private func browserURL(_ text: String) -> URL? {
    let value = text.hasPrefix("http://127.0.0.1/") ? "dm-resource:" + text.dropFirst("http:".count) : text
    return URL(string: value)
}

private final class Panel: NSObject, WKNavigationDelegate, WKUIDelegate, WKURLSchemeHandler {
    let id: Int64
    var view: WKWebView!
    var ownedWindow: NSWindow?
    var tasks: [Int64: WKURLSchemeTask] = [:]
    var taskSerial: Int64 = 0
    var allowedURL: String?
    var pendingURL: String?
    var lastTitle = ""
    var lastRect = NSRect.zero
    var lastVisible = false
    var lastFocused = false

    init(_ id: Int64, _ width: Int32, _ height: Int32) {
        self.id = id
        super.init()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.setURLSchemeHandler(self, forURLScheme: "dm-resource")
        config.preferences.javaScriptCanOpenWindowsAutomatically = true
        view = WKWebView(frame: NSRect(x: 0, y: 0, width: Int(width), height: Int(height)), configuration: config)
        view.navigationDelegate = self
        view.uiDelegate = self
        view.isHidden = true
        if width > 0 && height > 0 {
            let window = NSWindow(contentRect: view.frame, styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
            window.title = "Browser"
            window.isReleasedWhenClosed = false
            window.contentView = view
            view.isHidden = false
            window.makeKeyAndOrderFront(nil)
            ownedWindow = window
        }
    }

    func load(_ value: String) {
        guard let url = browserURL(value) else { return }
        allowedURL = url.absoluteString
        view.load(URLRequest(url: url))
    }

    func attach(_ windowID: UInt32, _ pixelWidth: Double, _ pixelHeight: Double, _ x: Double, _ y: Double, _ width: Double, _ height: Double, _ visible: Bool) {
        guard ownedWindow == nil else { return }
        // SDL window lookup and AppKit operations both stay on the main thread.
        // Lookup by ID also protects against a window destroyed before this job.
        guard let sdl = getWindow?(windowID), let properties = getProperties?(sdl),
              let pointer = "SDL.window.cocoa.window".withCString({ getPointer?(properties, $0, nil) }),
              pixelWidth > 0, pixelHeight > 0 else {
            view.isHidden = true
            return
        }
        let window = Unmanaged<NSWindow>.fromOpaque(pointer).takeUnretainedValue()
        guard let parent = window.contentView else { return }
        let sx = parent.bounds.width / pixelWidth
        let sy = parent.bounds.height / pixelHeight
        let frame = NSRect(x: x * sx, y: parent.bounds.height - (y + height) * sy,
                           width: max(0, width * sx), height: max(0, height * sy))
        if view.superview !== parent { view.removeFromSuperview(); parent.addSubview(view, positioned: .above, relativeTo: nil) }
        if view.frame != frame { view.frame = frame }
        view.isHidden = !visible || width <= 0 || height <= 0
        if window.title != lastTitle || frame != lastRect || visible != lastVisible {
            lastTitle = window.title; lastRect = frame; lastVisible = visible
            emit(id, 5, 0, "attached title=\(window.title) frame=\(frame) parent=\(parent.bounds) visible=\(!view.isHidden)")
        }
        let focused = !view.isHidden && ((window.firstResponder as? NSView)?.isDescendant(of: view) ?? false)
        if focused != lastFocused {
            lastFocused = focused
            emit(id, 6, 0, focused ? "1" : "0")
        }
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        taskSerial += 1
        tasks[taskSerial] = task
        emit(id, 1, taskSerial, originalURL(url))
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {
        for (key, value) in tasks where value === task { tasks.removeValue(forKey: key) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.absoluteString == allowedURL || url.absoluteString == "about:blank" {
            allowedURL = nil
            decisionHandler(.allow)
        } else {
            decisionHandler(.cancel)
            emit(id, 2, 0, originalURL(url))
        }
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url { emit(id, 2, 0, originalURL(url)) }
        return nil
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        webView.evaluateJavaScript("JSON.stringify({title:document.title,text:document.body?document.body.innerText:'',images:Array.from(document.images).map(i=>({src:i.getAttribute('src'),loaded:i.complete&&i.naturalWidth>0}))})") { result, error in
            emit(self.id, 3, 0, (result as? String) ?? "")
        }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        emit(id, 4, 0, error.localizedDescription)
    }
}

@_cdecl("dm_web_initialize")
public func initialize(_ event: @escaping EventCallback, _ library: UnsafePointer<CChar>) {
    callback = event
    guard let handle = dlopen(library, RTLD_NOW),
          let window = dlsym(handle, "SDL_GetWindowFromID"),
          let properties = dlsym(handle, "SDL_GetWindowProperties"),
          let pointer = dlsym(handle, "SDL_GetPointerProperty") else { return }
    getWindow = unsafeBitCast(window, to: GetWindow.self)
    getProperties = unsafeBitCast(properties, to: GetProperties.self)
    getPointer = unsafeBitCast(pointer, to: GetPointer.self)
    if let warp = dlsym(handle, "SDL_WarpMouseInWindow") { warpMouse = unsafeBitCast(warp, to: WarpMouse.self) }
    DispatchQueue.main.async { installFocusReturn() }
}

// Dream Seeker takes the keyboard back from a browser control when the player
// clicks the map or any other non-browser area. AppKit leaves the web view as
// first responder, so keys kept going to the page (arrows scrolled it, typing
// never reached the game). Return the responder to the game view on such clicks.
private var focusMonitor: Any?
private func installFocusReturn() {
    guard focusMonitor == nil else { return }
    focusMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { event in
        guard let window = event.window, let content = window.contentView else { return event }
        let point = content.convert(event.locationInWindow, from: nil)
        let windowPanels = panels.values.filter { $0.view.window === window && !$0.view.isHidden }
        if windowPanels.contains(where: { $0.view.frame.contains(point) }) { return event }
        guard let responder = window.firstResponder as? NSView,
              windowPanels.contains(where: { responder.isDescendant(of: $0.view) }) else { return event }
        if !window.makeFirstResponder(content) { window.makeFirstResponder(nil) }
        for panel in windowPanels where panel.lastFocused {
            panel.lastFocused = false
            emit(panel.id, 6, 0, "0")
        }
        return event
    }
}

@_cdecl("dm_web_create")
public func create(_ width: Int32, _ height: Int32) -> Int64 {
    nextPanel += 1
    let id = nextPanel
    DispatchQueue.main.async { panels[id] = Panel(id, width, height) }
    return id
}

// Test-only resize of a real native window. Input tests use SDL's event queue.
@_cdecl("dm_ui_test_focus")
public func uiTestFocus(_ windowID: UInt32, _ x: Double, _ y: Double) {
    guard ProcessInfo.processInfo.environment["DM_NATIVE_UI_PROBE"] != nil else { return }
    DispatchQueue.main.async {
        guard let sdl = getWindow?(windowID), let properties = getProperties?(sdl),
              let pointer = "SDL.window.cocoa.window".withCString({ getPointer?(properties, $0, nil) }) else { return }
        let window = Unmanaged<NSWindow>.fromOpaque(pointer).takeUnretainedValue()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        if x >= 0, y >= 0, let view = window.contentView {
            warpMouse?(sdl, Float(x * view.bounds.width), Float(y * view.bounds.height))
        }
    }
}
private func cocoaWindow(_ windowID: UInt32) -> NSWindow? {
    guard let sdl = getWindow?(windowID), let properties = getProperties?(sdl),
          let pointer = "SDL.window.cocoa.window".withCString({ getPointer?(properties, $0, nil) }) else { return nil }
    return Unmanaged<NSWindow>.fromOpaque(pointer).takeUnretainedValue()
}
// Test-only: queue real AppKit events, so they take the same window/first-responder
// route as a physical keyboard and mouse (SDL injection bypasses AppKit focus).
@_cdecl("dm_ui_test_native_key")
public func uiTestNativeKey(_ windowID: UInt32, _ keyCode: UInt16, _ text: UnsafePointer<CChar>, _ flags: UInt) {
    guard ProcessInfo.processInfo.environment["DM_NATIVE_UI_PROBE"] != nil else { return }
    let characters = String(cString: text)
    DispatchQueue.main.async {
        guard let window = cocoaWindow(windowID) else { return }
        for type in [NSEvent.EventType.keyDown, .keyUp] {
            if let event = NSEvent.keyEvent(with: type, location: .zero, modifierFlags: NSEvent.ModifierFlags(rawValue: flags),
                                            timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                                            context: nil, characters: characters, charactersIgnoringModifiers: characters,
                                            isARepeat: false, keyCode: keyCode) {
                NSApp.postEvent(event, atStart: false)
            }
        }
    }
}
@_cdecl("dm_ui_test_native_click")
public func uiTestNativeClick(_ windowID: UInt32, _ x: Double, _ y: Double) {
    guard ProcessInfo.processInfo.environment["DM_NATIVE_UI_PROBE"] != nil else { return }
    DispatchQueue.main.async {
        guard let window = cocoaWindow(windowID), let view = window.contentView else { return }
        let point = view.convert(NSPoint(x: x * view.bounds.width, y: view.bounds.height - y * view.bounds.height), to: nil)
        // A real click is preceded by pointer motion; without it the engine keeps the old pointer position.
        for type in [NSEvent.EventType.mouseMoved, .leftMouseDown, .leftMouseUp] {
            if let event = NSEvent.mouseEvent(with: type, location: point, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                              windowNumber: window.windowNumber, context: nil, eventNumber: 0, clickCount: type == .mouseMoved ? 0 : 1,
                                              pressure: type == .leftMouseDown ? 1 : 0) {
                NSApp.postEvent(event, atStart: false)
            }
        }
    }
}
private var responderSnapshot = "unknown"
@_cdecl("dm_ui_test_first_responder")
public func uiTestFirstResponder(_ windowID: UInt32, _ out: UnsafeMutablePointer<CChar>, _ size: Int32) {
    // The probe runs off the AppKit thread: report the last main-thread reading.
    DispatchQueue.main.async {
        guard let window = cocoaWindow(windowID) else { responderSnapshot = "none"; return }
        let responder = window.firstResponder
        var name = "app=" + String(describing: type(of: NSApp!)) + ":" + (window.isKeyWindow ? "key:" : "notkey:") + (responder.map { String(describing: type(of: $0)) } ?? "nil")
        if let view = responder as? NSView, panels.values.contains(where: { view.isDescendant(of: $0.view) }) { name += ":webpanel" }
        for (id, panel) in panels.sorted(by: { $0.key < $1.key }) where panel.view.window === window {
            let f = panel.view.frame, h = panel.view.superview?.bounds.height ?? 0
            name += "|panel\(id) hidden=\(panel.view.isHidden) top-left=(\(Int(f.minX)),\(Int(h - f.maxY))) size=\(Int(f.width))x\(Int(f.height))"
        }
        responderSnapshot = name
    }
    _ = responderSnapshot.withCString { strncpy(out, $0, Int(size) - 1) }
    out[Int(size) - 1] = 0
}
@_cdecl("dm_ui_test_resize")
public func uiTestResize(_ windowID: UInt32, _ width: Double, _ height: Double) {
    guard ProcessInfo.processInfo.environment["DM_NATIVE_UI_PROBE"] != nil else { return }
    DispatchQueue.main.async {
        guard let sdl = getWindow?(windowID), let properties = getProperties?(sdl),
              let pointer = "SDL.window.cocoa.window".withCString({ getPointer?(properties, $0, nil) }) else { return }
        let window = Unmanaged<NSWindow>.fromOpaque(pointer).takeUnretainedValue()
        window.setContentSize(NSSize(width: width, height: height))
    }
}
@_cdecl("dm_web_load")
public func load(_ id: Int64, _ url: UnsafePointer<CChar>) {
    let value = String(cString: url)
    DispatchQueue.main.async { panels[id]?.load(value) }
}
@_cdecl("dm_web_layout")
public func layout(_ id: Int64, _ window: UInt32, _ pw: Double, _ ph: Double, _ x: Double, _ y: Double, _ w: Double, _ h: Double, _ visible: Int32) {
    DispatchQueue.main.async { panels[id]?.attach(window, pw, ph, x, y, w, h, visible != 0) }
}
@_cdecl("dm_web_respond")
public func respond(_ id: Int64, _ request: Int64, _ bytes: UnsafePointer<UInt8>?, _ length: Int32, _ mime: UnsafePointer<CChar>, _ status: Int32) {
    let data = bytes == nil ? Data() : Data(bytes: bytes!, count: Int(length))
    let contentType = String(cString: mime)
    DispatchQueue.main.async {
        guard let panel = panels[id], let task = panel.tasks.removeValue(forKey: request), let url = task.request.url else { return }
        let response = HTTPURLResponse(url: url, statusCode: Int(status), httpVersion: "HTTP/1.1",
                                       headerFields: ["Content-Type": contentType, "Content-Length": "\(data.count)"])!
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }
}
@_cdecl("dm_web_script")
public func script(_ id: Int64, _ code: UnsafePointer<CChar>) {
    let value = String(cString: code)
    DispatchQueue.main.async { panels[id]?.view.evaluateJavaScript(value, completionHandler: nil) }
}
@_cdecl("dm_web_history")
public func history(_ id: Int64, _ action: Int32) {
    DispatchQueue.main.async {
        guard let panel = panels[id] else { return }
        switch action {
        case -1:
            panel.allowedURL = panel.view.backForwardList.backItem?.url.absoluteString
            panel.view.goBack()
        case 1:
            panel.allowedURL = panel.view.backForwardList.forwardItem?.url.absoluteString
            panel.view.goForward()
        case 2:
            panel.allowedURL = panel.view.url?.absoluteString
            panel.view.reload()
        default: panel.view.stopLoading()
        }
    }
}
@_cdecl("dm_web_destroy")
public func destroy(_ id: Int64) {
    DispatchQueue.main.async {
        guard let panel = panels.removeValue(forKey: id) else { return }
        panel.view.stopLoading(); panel.view.removeFromSuperview(); panel.ownedWindow?.close()
    }
}
@_cdecl("dm_web_snapshot")
public func snapshot(_ id: Int64, _ path: UnsafePointer<CChar>) {
    let filename = String(cString: path)
    DispatchQueue.main.async {
        panels[id]?.view.takeSnapshot(with: nil) { image, error in
            guard let data = image?.tiffRepresentation, let bitmap = NSBitmapImageRep(data: data),
                  let png = bitmap.representation(using: .png, properties: [:]) else { return }
            try? png.write(to: URL(fileURLWithPath: filename))
        }
    }
}
