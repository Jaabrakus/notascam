// The HUD page in a real WKWebView, the engine the game's HUD runs in (after rts-feel's tools/rts_feel/wkcheck.swift):
// prints script errors and console errors, then the value of a JavaScript expression evaluated after some seconds.
// The window stays off screen (it never takes focus from a real-input run) and the page's storage starts with
// `--storage key=value` pairs (e.g. rmAudio with bg:0, since an unseen window counts as "in the background").
//   swiftc -O tools/audio_wk.swift -o /tmp/audio_wk && /tmp/audio_wk page.html|http://... "expr" seconds [--storage k=v ...] [--at-start js ...]
import AppKit
import WebKit

final class Catcher: NSObject, WKScriptMessageHandler {
    var lines: [String] = []
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) { lines.append("\(m.body)") }
}

let args = CommandLine.arguments
guard args.count >= 4 else { print("usage: audio_wk page.html expression seconds [--storage k=v ...]"); exit(2) }
let url = args[1].hasPrefix("http") ? URL(string: args[1])! : URL(fileURLWithPath: args[1])   // over HTTP, the page can fetch files beside it
let expr = args[2]
let secs = Double(args[3]) ?? 5
var storage: [(String, String)] = []
var i = 4
var atStart: [String] = []
var until: String? = nil   // with --until js: evaluate the expression as soon as js is true (checked every 0.5 s), at the latest after the seconds given
while i < args.count {
    if args[i] == "--storage", i + 1 < args.count, let eq = args[i + 1].firstIndex(of: "=") { storage.append((String(args[i + 1][..<eq]), String(args[i + 1][args[i + 1].index(after: eq)...]))); i += 2 }
    else if args[i] == "--at-start", i + 1 < args.count { atStart.append(args[i + 1]); i += 2 }
    else if args[i] == "--until", i + 1 < args.count { until = args[i + 1]; i += 2 }
    else { i += 1 }
}
let app = NSApplication.shared
// an off-screen window is "not visible" to macOS: keep App Nap from throttling the page's timers and worker
let activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .idleSystemSleepDisabled, .latencyCritical], reason: "audio check")
let catcher = Catcher()
let cfg = WKWebViewConfiguration()
func js(_ s: String) -> String { let d = try! JSONSerialization.data(withJSONObject: [s], options: []); return String(data: d, encoding: .utf8)! }
var hook = """
window.addEventListener('error',e=>{try{window.webkit.messageHandlers.log.postMessage('ERROR '+e.message+' @'+(e.filename||'').split('/').pop()+':'+e.lineno+':'+e.colno)}catch(_){}});
(function(){const o=console.error;console.error=function(...a){try{window.webkit.messageHandlers.log.postMessage('console.error '+a.map(x=>x&&x.stack||String(x)).join(' ').slice(0,400))}catch(_){}return o.apply(console,a)}})();
"""
for (k, v) in storage { hook += "try{localStorage.setItem(\(js(k))[0],\(js(v))[0])}catch(_){}\n" }
for s in atStart { hook += s + "\n" }
cfg.userContentController.addUserScript(WKUserScript(source: hook, injectionTime: .atDocumentStart, forMainFrameOnly: true))
cfg.userContentController.add(catcher, name: "log")
let win = NSWindow(contentRect: NSRect(x: -4000, y: -4000, width: 1280, height: 720), styleMask: [.borderless], backing: .buffered, defer: false)
let web = WKWebView(frame: win.contentView!.bounds, configuration: cfg)
win.contentView!.addSubview(web)
if url.isFileURL { web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent()) } else { web.load(URLRequest(url: url)) }
func finish() {
    web.evaluateJavaScript(expr) { value, error in
        for l in catcher.lines { print(l) }
        print("RESULT \(value.map { "\($0)" } ?? "nil") \(error.map { "error: \($0)" } ?? "")")
        exit(0)
    }
}
let started = Date()
func poll() {
    guard let u = until, Date().timeIntervalSince(started) < secs else { finish(); return }
    web.evaluateJavaScript("!!(\(u))") { value, _ in
        if (value as? Bool) == true { finish() } else { DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { poll() } }
    }
}
if until == nil { DispatchQueue.main.asyncAfter(deadline: .now() + secs) { finish() } } else { DispatchQueue.main.asyncAfter(deadline: .now() + 1) { poll() } }
app.run()
