// Load an HTML page in a real WKWebView (the engine the game's HUD runs in) and print its script errors, then the
// value of a JavaScript expression. For pages that run in headless Chrome but not in the game (rts-feel, 2026-10-22).
//   swiftc -O tools/rts_feel/wkcheck.swift -o /tmp/wkcheck && /tmp/wkcheck page.html "typeof rfStats" [seconds]
import AppKit
import WebKit

final class Catcher: NSObject, WKScriptMessageHandler {
    var lines: [String] = []
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) { lines.append("\(m.body)") }
}

// The HUD talks to the game through byond:// links. Without a navigation delegate WebKit hands them to macOS, which
// shows a "no application set to open the URL byond://" dialog for every one (88 piled up on the user's screen on
// the night of 2026-10-22). Only the page's own file/about/data loads go through; the rest are printed as NAV lines.
final class Nav: NSObject, WKNavigationDelegate {
    let catcher: Catcher
    init(_ c: Catcher) { catcher = c }
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let scheme = a.request.url?.scheme?.lowercased() ?? ""
        if ["file", "about", "data", "blob"].contains(scheme) { decisionHandler(.allow); return }
        catcher.lines.append("NAV " + String((a.request.url?.absoluteString ?? "").prefix(200)))
        decisionHandler(.cancel)
    }
}

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: wkcheck page.html expression [seconds]"); exit(2) }
let url = URL(fileURLWithPath: args[1])
let expr = args[2]
let secs = args.count > 3 ? Double(args[3]) ?? 3 : 3
let app = NSApplication.shared
let catcher = Catcher()
let cfg = WKWebViewConfiguration()
let hook = """
window.addEventListener('error',e=>{try{window.webkit.messageHandlers.log.postMessage('ERROR '+e.message+' @'+(e.filename||'').split('/').pop()+':'+e.lineno+':'+e.colno)}catch(_){}});
(function(){const o=console.error;console.error=function(...a){try{window.webkit.messageHandlers.log.postMessage('console.error '+a.map(x=>x&&x.stack||String(x)).join(' ').slice(0,400))}catch(_){}return o.apply(console,a)}})();
"""
cfg.userContentController.addUserScript(WKUserScript(source: hook, injectionTime: .atDocumentStart, forMainFrameOnly: true))
cfg.userContentController.add(catcher, name: "log")
app.setActivationPolicy(.prohibited)   // never takes focus from the game windows other checks drive
let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 720), styleMask: [.titled], backing: .buffered, defer: false)
let web = WKWebView(frame: win.contentView!.bounds, configuration: cfg)
win.contentView!.addSubview(web)
let nav = Nav(catcher)   // navigationDelegate is weak: keep it here
web.navigationDelegate = nav
if ProcessInfo.processInfo.environment["WK_SHOW"] != nil { win.orderBack(nil) }   // on screen behind everything: animation frames run (slowly)
web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
DispatchQueue.main.asyncAfter(deadline: .now() + secs) {
    web.evaluateJavaScript(expr) { value, error in
        for l in catcher.lines { print(l) }
        print("RESULT \(value.map { "\($0)" } ?? "nil") \(error.map { "error: \($0)" } ?? "")")
        exit(0)
    }
}
app.run()
