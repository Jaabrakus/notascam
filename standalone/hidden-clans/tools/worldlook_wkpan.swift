// world-look pan probe in a real WKWebView (the engine the game's 3D view runs in): load an http page, run an async
// script body, print its result, save a snapshot. Like hud-craft's wkshot, with a long timeout for minute-long probes.
//   swiftc -O tools/worldlook_wkpan.swift -o wkpan ; wkpan URL W H script.js out.png [timeout-seconds]
// (tools/check_pan_frames.py builds and runs it)
import AppKit
import WebKit

final class Catcher: NSObject, WKScriptMessageHandler {
    var lines: [String] = []
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) { lines.append("\(m.body)") }
}
final class Nav: NSObject, WKNavigationDelegate {
    let catcher: Catcher
    init(_ c: Catcher) { catcher = c }
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let scheme = a.request.url?.scheme?.lowercased() ?? ""
        if ["http", "file", "about", "data", "blob"].contains(scheme) { decisionHandler(.allow); return }
        catcher.lines.append("NAV " + String((a.request.url?.absoluteString ?? "").prefix(200)))
        decisionHandler(.cancel)
    }
}
let a = CommandLine.arguments
guard a.count >= 6 else { print("usage: wkpan URL W H script.js out.png [timeout]"); exit(2) }
let url = URL(string: a[1])!, W = CGFloat(Double(a[2])!), H = CGFloat(Double(a[3])!)
let script = try! String(contentsOfFile: a[4], encoding: .utf8), out = URL(fileURLWithPath: a[5])
let limit = a.count > 6 ? Double(a[6]) ?? 300 : 300
let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
let catcher = Catcher()
let cfg = WKWebViewConfiguration()
let hook = """
window.addEventListener('error',e=>{try{window.webkit.messageHandlers.log.postMessage('ERROR '+e.message+' @'+(e.filename||'').split('/').pop()+':'+e.lineno)}catch(_){}});
(function(){const o=console.error;console.error=function(...x){try{window.webkit.messageHandlers.log.postMessage('console.error '+x.map(v=>v&&v.stack||String(v)).join(' ').slice(0,300))}catch(_){}return o.apply(console,x)}})();
"""
cfg.userContentController.addUserScript(WKUserScript(source: hook, injectionTime: .atDocumentStart, forMainFrameOnly: true))
cfg.userContentController.add(catcher, name: "log")
let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: W, height: H), styleMask: [.borderless], backing: .buffered, defer: false)
let web = WKWebView(frame: NSRect(x: 0, y: 0, width: W, height: H), configuration: cfg)
let nav = Nav(catcher); web.navigationDelegate = nav
win.contentView!.addSubview(web)
// on screen but behind every window (desktop level), and never counted as covered: a hidden or covered page has its
// timers held to ~1 s, so the probe's 60 Hz pacing would stretch to minutes. Nothing shows in front of the user.
for s in ["_setWindowOcclusionDetectionEnabled:"] { let sel = NSSelectorFromString(s); if web.responds(to: sel) { web.perform(sel, with: nil) } else { print("no \(s)") } }
for s in ["_setHiddenPageDOMTimerThrottlingEnabled:", "_setPageVisibilityBasedProcessSuppressionEnabled:"] { let sel = NSSelectorFromString(s); if cfg.preferences.responds(to: sel) { cfg.preferences.perform(sel, with: nil) } else { print("no \(s)") } }
win.level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.desktopWindow)))
win.setFrameOrigin(NSPoint(x: 0, y: 0)); win.orderFrontRegardless()
web.load(URLRequest(url: url))
DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
    web.callAsyncJavaScript(script, arguments: [:], in: nil, in: .page) { result in
        var probe = "nil"
        switch result { case .success(let v): probe = "\(v)"; case .failure(let e): probe = "SCRIPT-ERROR \(e)" }
        let sc = WKSnapshotConfiguration(); sc.rect = NSRect(x: 0, y: 0, width: W, height: H)
        web.takeSnapshot(with: sc) { img, err in
            if let img = img, let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
               let png = rep.representation(using: .png, properties: [:]) { try? png.write(to: out) }
            for l in catcher.lines { print(l) }
            print("PROBE \(probe)")
            if let err = err { print("SNAPSHOT-ERROR \(err)") }
            exit(0)
        }
    }
}
DispatchQueue.main.asyncAfter(deadline: .now() + limit) { for l in catcher.lines { print(l) }; print("TIMEOUT"); exit(3) }
app.run()
