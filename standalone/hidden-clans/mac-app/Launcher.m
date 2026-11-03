#import <Cocoa/Cocoa.h>
#import <signal.h>
#import <libproc.h>
#import <CommonCrypto/CommonDigest.h>
#import <sys/socket.h>
#import <netinet/in.h>
#import <arpa/inet.h>
#import "LauncherOutcome.h"
#import "LauncherWorlds.h"

// --- Discord sign-in (2026-10-24; the user: "i just want the login to be link to discord") ---
// The Discord application "Banners of the Deep" is a public client: the launcher runs the OAuth2 code flow itself
// (with PKCE), catching Discord's answer on a one-shot listener at 127.0.0.1, and asks for `identify` (the
// player's Discord ID and name), plus `guilds.join` once the link service is set (to add them to the community server). No token is kept: the account file holds the ID, the names and the game name.
// The Discord ID is the account: discord-links.json maps each ID to the game name its saves are keyed by. The first
// Discord account linked on a Mac takes over that Mac's existing name, so the saves made before sign-in carry over.
static NSString *const DMDiscordClientID=@"YOUR_DISCORD_CLIENT_ID";
static NSString *const DMDiscordRedirect=@"http://127.0.0.1:53134/callback";
static const uint16_t DMDiscordPort=53134;
// The link service (services/discord-link, a Cloudflare Worker) that gives the Discord server's Player and Founder
// roles: after a sign-in the launcher tells it "this Discord account played" with the sign-in's own token, then
// forgets the token. Empty until the service is deployed (services/discord-link/README.md, step 7).
static NSString *const DMLinkService=@"";
// The community server (Discord server "Banners of the Deep"): a permanent invite that lands in #welcome.
static NSString *const DMDiscordInvite=@"https://discord.gg/dXSKx33uAg";
static NSString *DMDataDir(void){
    NSString *d=NSProcessInfo.processInfo.environment[@"DM_STANDALONE_DATA_DIR"];
    return d.length?d:[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/Hidden Clans"];
}
static id DMReadJSON(NSString *name){
    NSData *data=[NSData dataWithContentsOfFile:[DMDataDir() stringByAppendingPathComponent:name]];
    return data?[NSJSONSerialization JSONObjectWithData:data options:0 error:nil]:nil;
}
static void DMWriteJSON(NSString *name,id object){
    [[NSFileManager defaultManager] createDirectoryAtPath:DMDataDir() withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil];
    NSData *data=[NSJSONSerialization dataWithJSONObject:object options:NSJSONWritingPrettyPrinted error:nil];
    NSString *path=[DMDataDir() stringByAppendingPathComponent:name];
    [data writeToFile:path atomically:YES];[[NSFileManager defaultManager] setAttributes:@{NSFilePosixPermissions:@0600} ofItemAtPath:path error:nil];
}
// A game name the engine accepts (letters, digits, underscore; at most 32), as launch.zsh makes from the Mac account.
static NSString *DMGameName(NSString *raw){
    NSMutableString *s=[NSMutableString string];
    for(NSUInteger i=0;i<raw.length&&s.length<32;i++){unichar c=[raw characterAtIndex:i];
        if((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_')[s appendFormat:@"%C",c];else if(c=='.')[s appendString:@"_"];}
    return s;
}
static NSString *DMBase64URL(NSData *data){
    return [[[[data base64EncodedStringWithOptions:0] stringByReplacingOccurrencesOfString:@"+" withString:@"-"] stringByReplacingOccurrencesOfString:@"/" withString:@"_"] stringByReplacingOccurrencesOfString:@"=" withString:@""];
}
static NSString *DMFormEncode(NSString *s){
    NSMutableCharacterSet *ok=[NSMutableCharacterSet alphanumericCharacterSet];[ok addCharactersInString:@"-._~"];
    return [s stringByAddingPercentEncodingWithAllowedCharacters:ok];
}

// The chooser's buttons are carved plates (screens, 2026-10-26): a bronze or dark gradient, a gold rim with a thin
// inner rule, the title in the brand's face; the pointer lights them (hand cursor) and a press sinks them.
@interface DMHoverButton : NSButton
@property BOOL primary;
@property BOOL lit;
@property NSTrackingArea *hoverArea;
@end
@implementation DMHoverButton
- (void)updateTrackingAreas {
    [super updateTrackingAreas];
    if(self.hoverArea)[self removeTrackingArea:self.hoverArea];
    self.hoverArea=[[NSTrackingArea alloc] initWithRect:self.bounds options:NSTrackingMouseEnteredAndExited|NSTrackingCursorUpdate|NSTrackingActiveAlways owner:self userInfo:nil];
    [self addTrackingArea:self.hoverArea];
}
- (void)paint:(BOOL)lit {self.lit=lit;[self setNeedsDisplay:YES];}
- (void)mouseEntered:(NSEvent *)event {[self paint:YES];}
- (void)mouseExited:(NSEvent *)event {[self paint:NO];}
- (void)cursorUpdate:(NSEvent *)event {[[NSCursor pointingHandCursor] set];}
- (void)drawRect:(NSRect)dirtyRect {
    BOOL down=self.cell.isHighlighted;CGFloat k=down?0.8:(self.lit?1.2:1);
    NSColor *(^tone)(CGFloat,CGFloat,CGFloat)=^NSColor *(CGFloat r,CGFloat g,CGFloat b){return [NSColor colorWithRed:MIN(1,r*k) green:MIN(1,g*k) blue:MIN(1,b*k) alpha:1];};
    NSColor *top=self.primary?tone(0.56,0.42,0.18):tone(0.21,0.17,0.12),*bottom=self.primary?tone(0.32,0.22,0.08):tone(0.1,0.08,0.055);
    NSRect r=NSInsetRect(self.bounds,1.5,1.5);CGFloat rad=MIN(5,r.size.height/4);
    NSBezierPath *plate=[NSBezierPath bezierPathWithRoundedRect:r xRadius:rad yRadius:rad];
    [(self.isFlipped?[[NSGradient alloc] initWithStartingColor:top endingColor:bottom]:[[NSGradient alloc] initWithStartingColor:bottom endingColor:top]) drawInBezierPath:plate angle:90];
    [(self.lit?[NSColor colorWithRed:0.98 green:0.86 blue:0.52 alpha:1]:[NSColor colorWithRed:0.69 green:0.54 blue:0.24 alpha:1]) setStroke];plate.lineWidth=2;[plate stroke];
    if(r.size.height>=34){NSBezierPath *rule=[NSBezierPath bezierPathWithRoundedRect:NSInsetRect(r,4,4) xRadius:MAX(1,rad-2) yRadius:MAX(1,rad-2)];rule.lineWidth=1;
        [[NSColor colorWithRed:0.95 green:0.83 blue:0.5 alpha:self.primary?0.5:0.26] setStroke];[rule stroke];}
    NSAttributedString *t=self.attributedTitle;NSSize s=t.size;
    [t drawAtPoint:NSMakePoint(round((self.bounds.size.width-s.width)/2),round((self.bounds.size.height-s.height)/2)+(down?(self.isFlipped?1:-1):0))];
}
@end
// The starting window's parts: the picture's foot darkened under the words, and the launch's stage bar.
@interface DMShadeView : NSView
@end
@implementation DMShadeView
- (void)drawRect:(NSRect)dirtyRect {
    NSRect b=self.bounds;
    [[[NSGradient alloc] initWithStartingColor:[NSColor colorWithRed:0.05 green:0.04 blue:0.03 alpha:0.97] endingColor:[NSColor colorWithRed:0.05 green:0.04 blue:0.03 alpha:0]] drawInRect:b angle:90];
    NSColor *gold=[NSColor colorWithRed:0.66 green:0.52 blue:0.25 alpha:1];[gold setFill];
    NSRectFill(NSMakeRect(10,9,b.size.width-20,2));NSRectFill(NSMakeRect(10,9,2,b.size.height-9));NSRectFill(NSMakeRect(b.size.width-12,9,2,b.size.height-9));
    for(NSNumber *x in @[@11,@(b.size.width/2),@(b.size.width-11)]){CGFloat cx=x.doubleValue;NSBezierPath *d=[NSBezierPath bezierPath];
        [d moveToPoint:NSMakePoint(cx,4)];[d lineToPoint:NSMakePoint(cx+6,10)];[d lineToPoint:NSMakePoint(cx,16)];[d lineToPoint:NSMakePoint(cx-6,10)];[d closePath];
        [[NSColor colorWithRed:0.95 green:0.82 blue:0.48 alpha:1] setFill];[d fill];[[NSColor colorWithRed:0.05 green:0.04 blue:0.02 alpha:1] setStroke];d.lineWidth=1;[d stroke];}
}
@end
@interface DMStageBar : NSView
@property double progress;
@end
@implementation DMStageBar
- (void)drawRect:(NSRect)dirtyRect {
    NSRect b=NSInsetRect(self.bounds,1,1);NSBezierPath *track=[NSBezierPath bezierPathWithRoundedRect:b xRadius:b.size.height/2 yRadius:b.size.height/2];
    [[NSColor colorWithRed:0.06 green:0.05 blue:0.035 alpha:1] setFill];[track fill];
    NSRect f=NSInsetRect(b,1.5,1.5);f.size.width=MAX(f.size.height,f.size.width*MIN(1,MAX(0,self.progress)));
    NSBezierPath *fill=[NSBezierPath bezierPathWithRoundedRect:f xRadius:f.size.height/2 yRadius:f.size.height/2];
    [[[NSGradient alloc] initWithStartingColor:[NSColor colorWithRed:0.66 green:0.48 blue:0.18 alpha:1] endingColor:[NSColor colorWithRed:1 green:0.91 blue:0.66 alpha:1]] drawInBezierPath:fill angle:90];
    [[NSColor colorWithRed:0.66 green:0.52 blue:0.25 alpha:1] setStroke];track.lineWidth=1;[track stroke];
}
@end

// --- The world list (10-31, planning/WORLD_SELECTOR_PLAN_2026-10-31.md): Play and Host open it over the art; a dark
// plate with a gold rim, a row per world (race picture, name, facts, last played), the picked one lit. ---
@protocol DMWorldOwner
- (void)pickWorld:(NSInteger)index;
- (void)moveWorldPick:(NSInteger)step;
- (void)worldGo:(id)sender;
@end
@interface DMPanelView : NSView
@end
@implementation DMPanelView
- (void)drawRect:(NSRect)dirtyRect {
    NSRect r=NSInsetRect(self.bounds,1,1);NSBezierPath *plate=[NSBezierPath bezierPathWithRoundedRect:r xRadius:6 yRadius:6];
    [[NSColor colorWithRed:0.07 green:0.05 blue:0.035 alpha:0.93] setFill];[plate fill];
    [[NSColor colorWithRed:0.69 green:0.54 blue:0.24 alpha:1] setStroke];plate.lineWidth=2;[plate stroke];
    NSBezierPath *rule=[NSBezierPath bezierPathWithRoundedRect:NSInsetRect(r,5,5) xRadius:3 yRadius:3];rule.lineWidth=1;
    [[NSColor colorWithRed:0.95 green:0.83 blue:0.5 alpha:0.22] setStroke];[rule stroke];
}
@end
// the art darkened from its middle down, under the list
@interface DMDimView : NSView
@end
@implementation DMDimView
- (void)drawRect:(NSRect)dirtyRect {
    NSColor *ink=[NSColor colorWithRed:0.04 green:0.03 blue:0.02 alpha:1];
    [[[NSGradient alloc] initWithColorsAndLocations:[ink colorWithAlphaComponent:0.75],0.0,[ink colorWithAlphaComponent:0.55],0.54,[ink colorWithAlphaComponent:0],0.66,nil] drawInRect:self.bounds angle:90];
}
@end
@interface DMWorldRow : NSView
@property NSInteger index;
@property BOOL picked;
@property (weak) id<DMWorldOwner> owner;
@end
@implementation DMWorldRow
- (BOOL)isFlipped {return YES;}
- (NSView *)hitTest:(NSPoint)point {return [super hitTest:point]?self:nil;}   // the labels and the picture click as the row
- (void)resetCursorRects {[self addCursorRect:self.bounds cursor:NSCursor.pointingHandCursor];}
- (void)mouseDown:(NSEvent *)event {[self.owner pickWorld:self.index];if(event.clickCount==2)[self.owner worldGo:self];}
- (void)drawRect:(NSRect)dirtyRect {
    CGFloat in=self.picked?1:0.5;NSBezierPath *p=[NSBezierPath bezierPathWithRoundedRect:NSInsetRect(self.bounds,in,in) xRadius:5 yRadius:5];
    NSColor *top=self.picked?[NSColor colorWithRed:0.43 green:0.32 blue:0.14 alpha:0.55]:[NSColor colorWithRed:0.21 green:0.17 blue:0.12 alpha:0.75];
    NSColor *bottom=self.picked?[NSColor colorWithRed:0.23 green:0.16 blue:0.06 alpha:0.6]:[NSColor colorWithRed:0.1 green:0.08 blue:0.055 alpha:0.75];
    [[[NSGradient alloc] initWithStartingColor:top endingColor:bottom] drawInBezierPath:p angle:90];
    [(self.picked?[NSColor colorWithRed:0.98 green:0.86 blue:0.52 alpha:1]:[NSColor colorWithRed:0.69 green:0.54 blue:0.24 alpha:0.35]) setStroke];p.lineWidth=self.picked?2:1;[p stroke];
}
@end
// the rows' page: up and down move the pick (Return plays it, Escape goes back: the plates' keys)
@interface DMWorldList : NSView
@property (weak) id<DMWorldOwner> owner;
@end
@implementation DMWorldList
- (BOOL)isFlipped {return YES;}
- (BOOL)acceptsFirstResponder {return YES;}
- (void)keyDown:(NSEvent *)event {
    if(event.keyCode==125||event.keyCode==126)[self.owner moveWorldPick:event.keyCode==125?1:-1];else [super keyDown:event];
}
@end
// A company's race picture from the race cards' sheet (world-races.png: art/hud/src/assets/screens-races.png, 192x128 a
// cell), drawn pixel-sharp at 72x48; nil for a world with no company of yours.
static NSImage *DMRacePicture(NSString *race) {
    static NSImage *sheet;static dispatch_once_t once;
    dispatch_once(&once,^{NSString *p=[NSBundle.mainBundle pathForResource:@"world-races" ofType:@"png"];sheet=p?[[NSImage alloc] initWithContentsOfFile:p]:nil;});
    NSInteger i=DMWorldRaceIndex(race);if(!sheet||i==NSNotFound)return nil;
    NSSize s=sheet.size;CGFloat ch=s.width*128/192;if((i+1)*ch>s.height+0.5)return nil;
    NSRect from=NSMakeRect(0,s.height-(i+1)*ch,s.width,ch);
    return [NSImage imageWithSize:NSMakeSize(72,48) flipped:NO drawingHandler:^BOOL(NSRect dst){
        NSGraphicsContext.currentContext.imageInterpolation=NSImageInterpolationNone;
        [sheet drawInRect:dst fromRect:from operation:NSCompositingOperationSourceOver fraction:1];return YES;}];
}

@interface Launcher : NSObject <NSApplicationDelegate,DMWorldOwner>
@property NSTask *task;
@property NSView *mainView;          // the chooser's three big buttons and their notes
@property NSButton *playButton;
@property NSView *worldView;         // the world list, over the art (nil when the big buttons show)
@property NSArray<NSDictionary *> *worlds;
@property NSArray<DMWorldRow *> *worldRows;
@property NSInteger pickedWorld;
@property BOOL hostMode;             // the list opened by Host for friends
@property NSWindow *window;
@property NSString *statusPath;
@property BOOL finishing;
@property BOOL quitRequested;
@property int resultCode;
@property NSView *accountRow;       // the chooser's Discord line: "Sign in with Discord", or who is signed in
@property int listenSocket;          // the sign-in's one-shot listener, -1 when none
@property NSAlert *waitingAlert;
@end
@implementation Launcher
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSMenu *menu=[NSMenu new];NSMenuItem *app=[NSMenuItem new];[menu addItem:app];
    NSMenu *submenu=[NSMenu new];[submenu addItemWithTitle:@"Quit Hidden Clans" action:@selector(terminate:) keyEquivalent:@"q"];app.submenu=submenu;NSApp.mainMenu=menu;
    // Edit menu so Cmd+V / Cmd+C work in the address and password fields.
    NSMenuItem *edit=[NSMenuItem new];[menu addItem:edit];NSMenu *editMenu=[[NSMenu alloc] initWithTitle:@"Edit"];edit.submenu=editMenu;
    [editMenu addItemWithTitle:@"Cut" action:@selector(cut:) keyEquivalent:@"x"];[editMenu addItemWithTitle:@"Copy" action:@selector(copy:) keyEquivalent:@"c"];
    [editMenu addItemWithTitle:@"Paste" action:@selector(paste:) keyEquivalent:@"v"];[editMenu addItemWithTitle:@"Select All" action:@selector(selectAll:) keyEquivalent:@"a"];
    self.listenSocket=-1;
    NSMutableArray *passed=[NSMutableArray array];
    for(NSString *arg in [NSProcessInfo.processInfo.arguments subarrayWithRange:NSMakeRange(1,NSProcessInfo.processInfo.arguments.count-1)]) if(![arg hasPrefix:@"-psn_"]) [passed addObject:arg];
    // Started with options (package checks, scripts): go straight in. Otherwise ask how to play.
    if(passed.count){[self startWith:passed password:nil];return;}
    [self showChooser];
}
// --- The Dungeon Master launcher: art, Play / Host for friends / Join a friend. ---
- (NSButton *)bigButton:(NSString *)title detail:(NSString *)detail action:(SEL)action frame:(NSRect)frame in:(NSView *)view primary:(BOOL)primary {
    DMHoverButton *b=[[DMHoverButton alloc] initWithFrame:frame];b.primary=primary;b.bordered=NO;b.focusRingType=NSFocusRingTypeNone;b.target=self;b.action=action;
    NSFont *font=[NSFont fontWithName:@"Luminari-Regular" size:22]?:[NSFont boldSystemFontOfSize:20];
    NSShadow *ink=[NSShadow new];ink.shadowColor=[NSColor colorWithWhite:0 alpha:0.85];ink.shadowOffset=NSMakeSize(0,-1);ink.shadowBlurRadius=2;
    b.attributedTitle=[[NSAttributedString alloc] initWithString:title attributes:@{NSFontAttributeName:font,NSForegroundColorAttributeName:[NSColor colorWithRed:0.97 green:0.86 blue:0.55 alpha:1],NSShadowAttributeName:ink}];
    [view addSubview:b];
    NSTextField *d=[NSTextField wrappingLabelWithString:detail];d.alignment=NSTextAlignmentCenter;d.font=[NSFont systemFontOfSize:12];
    d.textColor=[NSColor colorWithRed:0.84 green:0.79 blue:0.68 alpha:1];d.frame=NSMakeRect(frame.origin.x,frame.origin.y-40,frame.size.width,34);[view addSubview:d];
    return b;
}
// The footer's small plates (Discord, Saves & logs, Quit, Sign out): the same carved look, in the system face.
- (NSButton *)smallButton:(NSString *)title action:(SEL)action target:(id)target frame:(NSRect)frame in:(NSView *)view {
    DMHoverButton *b=[[DMHoverButton alloc] initWithFrame:frame];b.bordered=NO;b.focusRingType=NSFocusRingTypeNone;b.target=target;b.action=action;
    b.attributedTitle=[[NSAttributedString alloc] initWithString:title attributes:@{NSFontAttributeName:[NSFont systemFontOfSize:12 weight:NSFontWeightMedium],NSForegroundColorAttributeName:[NSColor colorWithRed:0.93 green:0.86 blue:0.68 alpha:1]}];
    [view addSubview:b];return b;
}
- (void)showChooser {
    CGFloat W=920,H=600;
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,W,H) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskFullSizeContentView backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"Hidden Clans";self.window.titlebarAppearsTransparent=YES;self.window.titleVisibility=NSWindowTitleHidden;
    self.window.appearance=[NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    NSView *v=self.window.contentView;v.wantsLayer=YES;v.layer.backgroundColor=[NSColor colorWithRed:0.086 green:0.067 blue:0.047 alpha:1].CGColor;
    NSString *art=[NSBundle.mainBundle pathForResource:@"launcher-art" ofType:@"png"];
    // screens (2026-10-26): the art is the whole window (the painted world, the title, the frame: 920x600 at 2x)
    if(art){NSImageView *iv=[NSImageView imageViewWithImage:[[NSImage alloc] initWithContentsOfFile:art]];iv.imageScaling=NSImageScaleAxesIndependently;iv.frame=NSMakeRect(0,0,W,H);[v addSubview:iv];}
    else{NSTextField *t=[NSTextField labelWithString:@"Hidden Clans"];t.font=[NSFont fontWithName:@"Luminari-Regular" size:56]?:[NSFont boldSystemFontOfSize:48];t.textColor=[NSColor colorWithRed:0.95 green:0.83 blue:0.5 alpha:1];t.frame=NSMakeRect(0,H-200,W,80);t.alignment=NSTextAlignmentCenter;[v addSubview:t];}
    CGFloat bw=250,gap=26,x0=(W-3*bw-2*gap)/2,by=142;
    NSView *main=[[NSView alloc] initWithFrame:v.bounds];self.mainView=main;[v addSubview:main];
    NSButton *play=[self bigButton:@"Play" detail:@"Your own worlds on this Mac." action:@selector(choosePlay:) frame:NSMakeRect(x0,by,bw,62) in:main primary:YES];play.keyEquivalent=@"\r";self.playButton=play;
    [self bigButton:@"Host for friends" detail:@"One of your worlds, open to friends on the same network." action:@selector(chooseHost:) frame:NSMakeRect(x0+bw+gap,by,bw,62) in:main primary:NO];
    [self bigButton:@"Join a friend" detail:@"Play in a friend's world: their address and password." action:@selector(chooseJoin:) frame:NSMakeRect(x0+2*(bw+gap),by,bw,62) in:main primary:NO];
    [self refreshAccountRow];
    // the build number only (owner 10-28: "remove the version and put the build number", "remove the based on")
    NSString *build=[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"]?:@"";
    NSTextField *foot=[NSTextField labelWithString:build.length?[NSString stringWithFormat:@"Build %@",build]:@""];
    foot.font=[NSFont systemFontOfSize:11];foot.textColor=[NSColor colorWithRed:0.66 green:0.6 blue:0.5 alpha:1];foot.frame=NSMakeRect(34,31,W-34-400,16);foot.lineBreakMode=NSLineBreakByTruncatingMiddle;[v addSubview:foot];
    [self smallButton:@"Join our Discord" action:@selector(openCommunity:) target:self frame:NSMakeRect(W-386,26,132,26) in:v];
    [self smallButton:@"Saves & logs" action:@selector(openFolder:) target:self frame:NSMakeRect(W-246,26,112,26) in:v];
    [self smallButton:@"Quit" action:@selector(terminate:) target:NSApp frame:NSMakeRect(W-126,26,92,26) in:v];
    [self.window center];[self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
}
- (void)openCommunity:(id)sender {[[NSWorkspace sharedWorkspace] openURL:[NSURL URLWithString:DMDiscordInvite]];}
- (void)openFolder:(id)sender {
    NSString *dir=DMDataDir();   // the same folder the game uses (DM_STANDALONE_DATA_DIR in checks)
    [[NSFileManager defaultManager] createDirectoryAtPath:dir withIntermediateDirectories:YES attributes:nil error:nil];
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:dir]];
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {return !self.task;}
// Play: the world list; with no world yet, straight into the first one, as before the list.
- (void)choosePlay:(id)sender {
    if(DMListWorlds(DMDataDir()).count){[self showWorlds:NO pick:nil];return;}
    [self.window orderOut:nil];[self startWith:[self withAccount:@[]] password:nil];
}
// The name saves are kept by: the signed-in Discord account's game name, else launch.zsh's (the app's player-name, or
// the Mac account's name in letters and digits); the list finds "your" company by it.
- (NSString *)gameName {
    NSString *name=DMReadJSON(@"discord-account.json")[@"game_name"];if([name isKindOfClass:NSString.class]&&name.length)return name;
    NSString *fixed=DMWorldText([NSString stringWithContentsOfFile:[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"game/player-name"] encoding:NSUTF8StringEncoding error:nil]);
    if(fixed.length&&![fixed isEqualToString:@"@login"])return fixed;
    NSString *mac=[NSUserName() stringByReplacingOccurrencesOfString:@"[^A-Za-z0-9]" withString:@"" options:NSRegularExpressionSearch range:NSMakeRange(0,NSUserName().length)];
    return mac.length?mac:@"Player";
}
- (NSTextField *)worldLabel:(NSString *)text font:(NSFont *)font color:(NSColor *)color frame:(NSRect)frame in:(NSView *)view {
    NSTextField *t=[NSTextField labelWithString:text?:@""];t.font=font;t.textColor=color;t.frame=frame;t.lineBreakMode=NSLineBreakByTruncatingTail;[view addSubview:t];return t;
}
- (DMHoverButton *)plate:(NSString *)title primary:(BOOL)primary color:(NSColor *)color action:(SEL)action frame:(NSRect)frame in:(NSView *)view {
    DMHoverButton *b=[[DMHoverButton alloc] initWithFrame:frame];b.primary=primary;b.bordered=NO;b.focusRingType=NSFocusRingTypeNone;b.target=self;b.action=action;
    NSFont *font=primary?([NSFont fontWithName:@"Luminari-Regular" size:18]?:[NSFont boldSystemFontOfSize:16]):[NSFont systemFontOfSize:13 weight:NSFontWeightMedium];
    NSShadow *ink=[NSShadow new];ink.shadowColor=[NSColor colorWithWhite:0 alpha:0.85];ink.shadowOffset=NSMakeSize(0,-1);ink.shadowBlurRadius=2;
    b.attributedTitle=[[NSAttributedString alloc] initWithString:title attributes:@{NSFontAttributeName:font,NSForegroundColorAttributeName:color?:[NSColor colorWithRed:0.93 green:0.86 blue:0.68 alpha:1],NSShadowAttributeName:ink}];
    [view addSubview:b];return b;
}
// The list in the chooser's window: the big buttons and the Discord line hide under it; Back brings them again.
// pick: the folder to have picked (after a rename), else the world played last.
- (void)showWorlds:(BOOL)host pick:(NSString *)pick {
    self.hostMode=host;self.worlds=DMListWorlds(DMDataDir());
    if(!self.worlds.count){[self worldBack:nil];if(host)[self askHostPasswordFor:nil];return;}
    NSView *v=self.window.contentView;[self.worldView removeFromSuperview];
    // just above the big buttons: the footer (Discord, Saves & logs, Quit) stays above it, lit and clickable
    NSView *wv=[[NSView alloc] initWithFrame:v.bounds];self.worldView=wv;[v addSubview:wv positioned:NSWindowAbove relativeTo:self.mainView];
    [wv addSubview:[[DMDimView alloc] initWithFrame:wv.bounds]];
    DMPanelView *panel=[[DMPanelView alloc] initWithFrame:NSMakeRect(100,64,720,274)];[wv addSubview:panel];
    NSColor *gold=[NSColor colorWithRed:0.98 green:0.86 blue:0.52 alpha:1],*dim=[NSColor colorWithRed:0.79 green:0.73 blue:0.61 alpha:1],*faint=[NSColor colorWithRed:0.66 green:0.6 blue:0.5 alpha:1];
    NSShadow *ink=[NSShadow new];ink.shadowColor=[NSColor colorWithWhite:0 alpha:0.9];ink.shadowOffset=NSMakeSize(0,-1);ink.shadowBlurRadius=2;
    NSTextField *title=[self worldLabel:host?@"Host for friends: choose a world":@"Choose a world" font:[NSFont fontWithName:@"Luminari-Regular" size:21]?:[NSFont boldSystemFontOfSize:19] color:gold frame:NSMakeRect(18,230,460,30) in:panel];title.shadow=ink;
    NSDictionary *acct=DMReadJSON(@"discord-account.json");NSString *shown=DMWorldText(acct[@"global_name"]);if(!shown.length)shown=DMWorldText(acct[@"username"]);
    if(acct[@"id"]&&shown.length){NSTextField *who=[self worldLabel:[@"Signed in with Discord as " stringByAppendingString:shown] font:[NSFont systemFontOfSize:12] color:faint frame:NSMakeRect(420,236,282,16) in:panel];who.alignment=NSTextAlignmentRight;}
    // the rows, in a scroll view when there are more than three
    NSScrollView *scroll=[[NSScrollView alloc] initWithFrame:NSMakeRect(16,54,688,174)];scroll.drawsBackground=NO;scroll.borderType=NSNoBorder;
    scroll.hasVerticalScroller=YES;scroll.autohidesScrollers=YES;scroll.scrollerStyle=NSScrollerStyleOverlay;
    CGFloat rw=688,rh=54,step=60;
    DMWorldList *list=[[DMWorldList alloc] initWithFrame:NSMakeRect(0,0,rw,MAX(174,self.worlds.count*step-(step-rh)))];list.owner=self;
    NSMutableArray *rows=[NSMutableArray array];NSString *me=[self gameName];NSDate *now=NSDate.date;
    [self.worlds enumerateObjectsUsingBlock:^(NSDictionary *w,NSUInteger i,BOOL *stop){
        DMWorldRow *row=[[DMWorldRow alloc] initWithFrame:NSMakeRect(0,i*step,rw,rh)];row.index=i;row.owner=self;[list addSubview:row];[rows addObject:row];
        NSView *box=[[NSView alloc] initWithFrame:NSMakeRect(6,3,72,48)];box.wantsLayer=YES;box.layer.backgroundColor=[NSColor colorWithWhite:0 alpha:0.35].CGColor;box.layer.cornerRadius=3;[row addSubview:box];
        NSImage *pic=DMRacePicture(DMWorldRace(w,me));
        if(pic){NSImageView *iv=[NSImageView imageViewWithImage:pic];iv.frame=box.bounds;iv.imageScaling=NSImageScaleNone;[box addSubview:iv];}
        else{NSTextField *flag=[self worldLabel:@"⚑" font:[NSFont systemFontOfSize:20] color:[NSColor colorWithRed:0.69 green:0.54 blue:0.24 alpha:1] frame:NSMakeRect(0,11,72,26) in:box];flag.alignment=NSTextAlignmentCenter;}
        NSFont *nameFont=[NSFont fontWithName:@"Luminari-Regular" size:17]?:[NSFont boldSystemFontOfSize:15];
        NSMutableAttributedString *name=[[NSMutableAttributedString alloc] initWithString:w[@"label"] attributes:@{NSFontAttributeName:nameFont,NSForegroundColorAttributeName:gold,NSShadowAttributeName:ink}];
        if([w[@"land"] length]&&![w[@"land"] isEqualToString:w[@"label"]])
            [name appendAttributedString:[[NSAttributedString alloc] initWithString:[@"   " stringByAppendingString:w[@"land"]] attributes:@{NSFontAttributeName:[NSFont systemFontOfSize:11],NSForegroundColorAttributeName:faint}]];
        NSTextField *nl=[self worldLabel:@"" font:nameFont color:gold frame:NSMakeRect(90,5,rw-90-128,24) in:row];nl.attributedStringValue=name;
        [self worldLabel:DMWorldFacts(w,me) font:[NSFont systemFontOfSize:13] color:dim frame:NSMakeRect(90,31,rw-90-128,18) in:row];
        NSString *when=DMWorldWhen(w[@"lastPlayed"],now);
        if(when.length){
            NSTextField *wl=[self worldLabel:when font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold] color:[NSColor colorWithRed:0.93 green:0.89 blue:0.79 alpha:1] frame:NSMakeRect(rw-124,9,112,16) in:row];wl.alignment=NSTextAlignmentRight;
            NSTextField *wl2=[self worldLabel:@"last played" font:[NSFont systemFontOfSize:12] color:faint frame:NSMakeRect(rw-124,26,112,16) in:row];wl2.alignment=NSTextAlignmentRight;
        }
    }];
    self.worldRows=rows;scroll.documentView=list;[panel addSubview:scroll];
    NSColor *plain=nil,*warn=[NSColor colorWithRed:0.94 green:0.76 blue:0.66 alpha:1];
    DMHoverButton *go=[self plate:host?@"Host this world":@"Continue" primary:YES color:[NSColor colorWithRed:0.97 green:0.86 blue:0.55 alpha:1] action:@selector(worldGo:) frame:NSMakeRect(16,12,host?176:150,34) in:panel];go.keyEquivalent=@"\r";
    CGFloat x=16+go.frame.size.width+10;
    for(NSArray *p in @[@[@"New world",@"worldNew:",@112,plain?:NSNull.null],@[@"Rename",@"worldRename:",@96,NSNull.null],@[@"Move to Trash",@"worldTrash:",@128,warn]]){
        [self plate:p[0] primary:NO color:[p[3] isKindOfClass:NSColor.class]?p[3]:nil action:NSSelectorFromString(p[1]) frame:NSMakeRect(x,12,[p[2] doubleValue],34) in:panel];x+=[p[2] doubleValue]+10;
    }
    DMHoverButton *back=[self plate:@"Back" primary:NO color:nil action:@selector(worldBack:) frame:NSMakeRect(720-16-90,12,90,34) in:panel];back.keyEquivalent=@"\033";
    self.mainView.hidden=YES;self.accountRow.hidden=YES;self.playButton.keyEquivalent=@"";
    NSUInteger at=pick?[[self.worlds valueForKey:@"folder"] indexOfObject:pick]:NSNotFound;
    [self pickWorld:at==NSNotFound?0:(NSInteger)at];
    [self.window makeFirstResponder:list];
}
- (void)pickWorld:(NSInteger)index {
    if(index<0||index>=(NSInteger)self.worldRows.count)return;
    self.pickedWorld=index;
    for(DMWorldRow *row in self.worldRows){row.picked=row.index==index;[row setNeedsDisplay:YES];}
    [self.worldRows[index] scrollRectToVisible:self.worldRows[index].bounds];
}
- (void)moveWorldPick:(NSInteger)step {[self pickWorld:MAX(0,MIN((NSInteger)self.worldRows.count-1,self.pickedWorld+step))];}
- (NSDictionary *)pickedWorldEntry {return self.pickedWorld>=0&&self.pickedWorld<(NSInteger)self.worlds.count?self.worlds[self.pickedWorld]:nil;}
- (void)worldBack:(id)sender {
    [self.worldView removeFromSuperview];self.worldView=nil;self.worldRows=nil;
    self.mainView.hidden=NO;self.accountRow.hidden=NO;self.playButton.keyEquivalent=@"\r";
}
- (void)worldNotice:(NSString *)message detail:(NSString *)detail {
    NSAlert *a=[NSAlert new];a.messageText=message;a.informativeText=detail?:@"";[a beginSheetModalForWindow:self.window completionHandler:nil];
}
- (void)worldGo:(id)sender {NSDictionary *w=[self pickedWorldEntry];if(w)[self playWorld:w];}
// Plays (or, from Host for friends, hosts) a world: its last played time, then launch.zsh with --world.
- (void)playWorld:(NSDictionary *)world {
    if(self.hostMode){[self askHostPasswordFor:world];return;}
    DMWorldSetMeta(world,@"last_played",DMWorldStamp(NSDate.date));
    [self.window orderOut:nil];[self startWith:[self withAccount:@[@"--world",world[@"folder"]]] password:nil];
}
- (void)worldNew:(id)sender {
    NSAlert *a=[NSAlert new];a.messageText=@"New world";
    a.informativeText=@"The same land, fresh and empty, with its own name and history. Your settings, achievements and saved designs come with you.";
    NSView *box=[[NSView alloc] initWithFrame:NSMakeRect(0,0,300,24)];
    NSTextField *name=[self field:@"Name (or leave empty: the land names itself)" secure:NO value:nil y:0 in:box];a.accessoryView=box;
    [a addButtonWithTitle:self.hostMode?@"Make and host":@"Make and play"];[a addButtonWithTitle:@"Back"];a.window.initialFirstResponder=name;
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r!=NSAlertFirstButtonReturn)return;
        NSString *clean=DMWorldNameClean(name.stringValue);
        if(!clean){[self worldNotice:@"That name is too long." detail:@"Use at most 40 characters, on one line."];return;}
        NSDictionary *w=DMCreateWorld(DMDataDir(),clean,NSDate.date);
        if(!w){[self worldNotice:@"The new world could not be made." detail:@"Check that the disk has room, then try again."];return;}
        [self playWorld:w];
    }];
}
- (void)worldRename:(id)sender {
    NSDictionary *w=[self pickedWorldEntry];if(!w)return;
    NSAlert *a=[NSAlert new];a.messageText=@"Rename this world";
    a.informativeText=[w[@"land"] length]?[NSString stringWithFormat:@"The name the list shows. In the game the land stays “%@”. Leave it empty to show the land's name.",w[@"land"]]:@"The name the list shows.";
    NSView *box=[[NSView alloc] initWithFrame:NSMakeRect(0,0,300,24)];
    NSTextField *name=[self field:[w[@"land"] length]?w[@"land"]:@"Name" secure:NO value:DMWorldText(w[@"meta"][@"label"]) y:0 in:box];a.accessoryView=box;
    [a addButtonWithTitle:@"Rename"];[a addButtonWithTitle:@"Back"];a.window.initialFirstResponder=name;
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r!=NSAlertFirstButtonReturn)return;
        NSString *clean=DMWorldNameClean(name.stringValue);
        if(!clean){[self worldNotice:@"That name is too long." detail:@"Use at most 40 characters, on one line."];return;}
        if(!DMWorldSetMeta(w,@"label",clean)){[self worldNotice:@"The name could not be saved." detail:@"Check that the disk has room, then try again."];return;}
        [self showWorlds:self.hostMode pick:w[@"folder"]];
    }];
}
// Move to Trash: the whole world folder into the Trash (never deleted for good); Put Back brings it into the list again.
- (void)worldTrash:(id)sender {
    NSDictionary *w=[self pickedWorldEntry];if(!w)return;NSString *data=DMDataDir();
    if(DMGameRunning(data)){[self worldNotice:@"Close the game first." detail:@"A world can't go to the Trash while Hidden Clans is running."];return;}
    if(!DMWorldTrashable(data,w)){[self worldNotice:@"This world can't go to the Trash from here." detail:@"Saves & logs opens its folder."];return;}
    unsigned long long bytes=DMWorldSavesSize(w);   // a world never saved has none: no "(Zero KB)"
    NSString *size=bytes?[NSString stringWithFormat:@" (%@)",[NSByteCountFormatter stringFromByteCount:(long long)bytes countStyle:NSByteCountFormatterCountStyleFile]]:@"";
    NSAlert *a=[NSAlert new];a.messageText=[NSString stringWithFormat:@"Move “%@” to the Trash?",w[@"label"]];
    a.informativeText=[NSString stringWithFormat:@"Its companies, buildings and history go with it%@. You can put it back from the Trash until the Trash is emptied.",size];
    NSButton *trash=[a addButtonWithTitle:@"Move to Trash"];trash.hasDestructiveAction=YES;trash.keyEquivalent=@"";
    NSButton *cancel=[a addButtonWithTitle:@"Cancel"];cancel.keyEquivalent=@"\r";
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r!=NSAlertFirstButtonReturn)return;
        NSError *error=nil;
        if(![[NSFileManager defaultManager] trashItemAtURL:[NSURL fileURLWithPath:w[@"path"]] resultingItemURL:nil error:&error]){
            [self worldNotice:@"The world could not be moved to the Trash." detail:error.localizedDescription];return;}
        [self showWorlds:self.hostMode pick:nil];
    }];
}
// The signed-in Discord account plays under its linked game name (its saves); without one, launch.zsh's Mac-account name.
- (NSArray *)withAccount:(NSArray *)passed {
    NSString *name=DMReadJSON(@"discord-account.json")[@"game_name"];
    return name.length?[@[@"--username",name] arrayByAddingObjectsFromArray:passed]:passed;
}
- (void)refreshAccountRow {
    if(!self.window.contentView)return;
    [self.accountRow removeFromSuperview];
    NSView *v=self.window.contentView;CGFloat W=v.bounds.size.width;
    // between the buttons' notes and the footer
    NSView *row=[[NSView alloc] initWithFrame:NSMakeRect(0,62,W,28)];self.accountRow=row;[v addSubview:row];
    NSDictionary *acct=DMReadJSON(@"discord-account.json");
    if(acct[@"id"]){
        NSString *shown=[acct[@"global_name"] isKindOfClass:NSString.class]&&[acct[@"global_name"] length]?acct[@"global_name"]:acct[@"username"];
        NSTextField *who=[NSTextField labelWithString:[NSString stringWithFormat:@"Signed in with Discord as %@",shown]];
        who.font=[NSFont systemFontOfSize:13];who.textColor=[NSColor colorWithRed:0.93 green:0.89 blue:0.79 alpha:1];[who sizeToFit];
        CGFloat ow=84,total=who.frame.size.width+12+ow,x=(W-total)/2;
        who.frame=NSMakeRect(x,5,who.frame.size.width,18);[row addSubview:who];
        [self smallButton:@"Sign out" action:@selector(discordSignOut:) target:self frame:NSMakeRect(x+who.frame.size.width+12,1,ow,26) in:row];
    }else{
        DMHoverButton *b=[[DMHoverButton alloc] initWithFrame:NSMakeRect((W-260)/2,0,260,28)];b.primary=NO;b.bordered=NO;b.focusRingType=NSFocusRingTypeNone;
        b.target=self;b.action=@selector(discordSignIn:);
        b.attributedTitle=[[NSAttributedString alloc] initWithString:@"Sign in with Discord" attributes:@{NSFontAttributeName:[NSFont systemFontOfSize:13 weight:NSFontWeightSemibold],NSForegroundColorAttributeName:[NSColor colorWithRed:0.95 green:0.83 blue:0.5 alpha:1]}];
        [row addSubview:b];
    }
}
- (void)discordSignOut:(id)sender {
    [[NSFileManager defaultManager] removeItemAtPath:[DMDataDir() stringByAppendingPathComponent:@"discord-account.json"] error:nil];
    [self refreshAccountRow];
}
- (void)discordFail:(NSString *)message {
    [self stopListening];
    if(self.waitingAlert){[self.window endSheet:self.waitingAlert.window];self.waitingAlert=nil;}
    NSAlert *a=[NSAlert new];a.messageText=@"Discord sign-in didn't finish.";a.informativeText=message;[a beginSheetModalForWindow:self.window completionHandler:nil];
}
- (void)stopListening {int fd=self.listenSocket;self.listenSocket=-1;if(fd>=0){shutdown(fd,SHUT_RDWR);close(fd);}}
- (void)discordSignIn:(id)sender {
    if(self.listenSocket>=0)return;
    int fd=socket(AF_INET,SOCK_STREAM,0);int yes=1;setsockopt(fd,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof yes);
    struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_port=htons(DMDiscordPort);addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if(fd<0||bind(fd,(struct sockaddr *)&addr,sizeof addr)!=0||listen(fd,4)!=0){if(fd>=0)close(fd);
        [self discordFail:@"Another program is using the sign-in port (53134). Close other copies of the game and try again."];return;}
    self.listenSocket=fd;
    NSString *state=[NSUUID.UUID.UUIDString stringByReplacingOccurrencesOfString:@"-" withString:@""];
    NSString *verifier=[[NSUUID.UUID.UUIDString stringByAppendingString:NSUUID.UUID.UUIDString] stringByReplacingOccurrencesOfString:@"-" withString:@""];
    NSData *v=[verifier dataUsingEncoding:NSUTF8StringEncoding];unsigned char hash[CC_SHA256_DIGEST_LENGTH];CC_SHA256(v.bytes,(CC_LONG)v.length,hash);
    NSString *challenge=DMBase64URL([NSData dataWithBytes:hash length:sizeof hash]);
    // With the link service online, the sign-in also asks "join servers for you" so the service can add the player to
    // the community server (with their Player/Founder roles); without it, only who they are.
    NSString *scope=DMLinkService.length?@"identify guilds.join":@"identify";
    NSString *url=[NSString stringWithFormat:@"https://discord.com/oauth2/authorize?client_id=%@&response_type=code&scope=%@&redirect_uri=%@&state=%@&code_challenge=%@&code_challenge_method=S256",
        DMDiscordClientID,DMFormEncode(scope),DMFormEncode(DMDiscordRedirect),state,challenge];
    __weak Launcher *weakSelf=self;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        // One answer is all it waits for: Discord sends the browser back to /callback?code=...&state=...
        int c=accept(fd,NULL,NULL);
        if(c<0){dispatch_async(dispatch_get_main_queue(),^{[weakSelf stopListening];});return;}
        struct timeval tv={10,0};setsockopt(c,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof tv);
        char buf[8192];ssize_t n=recv(c,buf,sizeof buf-1,0);buf[n>0?n:0]=0;
        NSString *req=[NSString stringWithUTF8String:buf]?:@"";NSString *line=[[req componentsSeparatedByString:@"\r\n"] firstObject];
        NSArray *parts=[line componentsSeparatedByString:@" "];NSString *target=parts.count>1?parts[1]:@"";
        NSURLComponents *uc=[NSURLComponents componentsWithString:[@"http://127.0.0.1" stringByAppendingString:target]];
        NSMutableDictionary *q=[NSMutableDictionary dictionary];for(NSURLQueryItem *it in uc.queryItems)if(it.value)q[it.name]=it.value;
        BOOL good=[uc.path isEqualToString:@"/callback"]&&[q[@"state"] isEqualToString:state]&&q[@"code"];
        NSString *body=[NSString stringWithFormat:@"<!doctype html><meta charset=utf-8><title>Banners of the Deep</title><body style=\"background:#16110c;color:#eee2c4;font:17px -apple-system,sans-serif;text-align:center;padding-top:18vh\"><h1 style=\"color:#f2d27a;font:44px Luminari,Georgia,serif\">Banners of the Deep</h1><p>%@</p></body>",
            good?@"You're signed in. Close this tab and go back to the game.":@"Sign-in was cancelled or didn't match. Go back to the game and try again."];
        NSData *bd=[body dataUsingEncoding:NSUTF8StringEncoding];
        NSString *head=[NSString stringWithFormat:@"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %lu\r\nConnection: close\r\n\r\n",(unsigned long)bd.length];
        NSMutableData *out=[[head dataUsingEncoding:NSUTF8StringEncoding] mutableCopy];[out appendData:bd];
        send(c,out.bytes,out.length,0);close(c);
        dispatch_async(dispatch_get_main_queue(),^{
            Launcher *self=weakSelf;if(!self)return;[self stopListening];
            if(!good){[self discordFail:q[@"error_description"]?:(q[@"error"]?:@"Discord's answer didn't match this sign-in. Try again.")];return;}
            [self discordExchange:q[@"code"] verifier:verifier];
        });
    });
    NSAlert *a=[NSAlert new];a.messageText=@"Sign in with Discord";
    a.informativeText=@"Your browser has opened Discord. Approve Banners of the Deep there, then come back here.";
    [a addButtonWithTitle:@"Cancel"];self.waitingAlert=a;
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){Launcher *self=weakSelf;if(self.waitingAlert==a){self.waitingAlert=nil;[self stopListening];}}];
    [[NSWorkspace sharedWorkspace] openURL:[NSURL URLWithString:url]];
}
- (void)discordExchange:(NSString *)code verifier:(NSString *)verifier {
    NSMutableURLRequest *req=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:@"https://discord.com/api/oauth2/token"]];req.HTTPMethod=@"POST";
    [req setValue:@"application/x-www-form-urlencoded" forHTTPHeaderField:@"Content-Type"];
    req.HTTPBody=[[NSString stringWithFormat:@"client_id=%@&grant_type=authorization_code&code=%@&redirect_uri=%@&code_verifier=%@",
        DMDiscordClientID,DMFormEncode(code),DMFormEncode(DMDiscordRedirect),DMFormEncode(verifier)] dataUsingEncoding:NSUTF8StringEncoding];
    __weak Launcher *weakSelf=self;
    [[NSURLSession.sharedSession dataTaskWithRequest:req completionHandler:^(NSData *data,NSURLResponse *resp,NSError *err){
        NSDictionary *tok=data?[NSJSONSerialization JSONObjectWithData:data options:0 error:nil]:nil;
        NSString *access=[tok isKindOfClass:NSDictionary.class]?tok[@"access_token"]:nil;
        if(!access){NSString *why=err.localizedDescription?:([tok isKindOfClass:NSDictionary.class]?(tok[@"error_description"]?:tok[@"error"]):nil)?:@"Discord didn't accept the sign-in.";
            dispatch_async(dispatch_get_main_queue(),^{[weakSelf discordFail:[NSString stringWithFormat:@"%@",why]];});return;}
        NSMutableURLRequest *me=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:@"https://discord.com/api/users/@me"]];
        [me setValue:[@"Bearer " stringByAppendingString:access] forHTTPHeaderField:@"Authorization"];
        [[NSURLSession.sharedSession dataTaskWithRequest:me completionHandler:^(NSData *d2,NSURLResponse *r2,NSError *e2){
            NSDictionary *user=d2?[NSJSONSerialization JSONObjectWithData:d2 options:0 error:nil]:nil;
            dispatch_async(dispatch_get_main_queue(),^{
                Launcher *self=weakSelf;if(!self)return;
                if(![user isKindOfClass:NSDictionary.class]||![user[@"id"] isKindOfClass:NSString.class]){[self discordFail:e2.localizedDescription?:@"Discord didn't say who you are. Try again."];return;}
                [self discordLink:user access:access];
            });
        }] resume];
    }] resume];
}
// The Discord ID owns the game name: an ID seen before keeps its name; the first ID on this Mac takes the Mac's own
// name (the saves made before sign-in); any later one gets its Discord username, made unique.
- (void)discordLink:(NSDictionary *)user access:(NSString *)access {
    NSMutableDictionary *links=[DMReadJSON(@"discord-links.json") mutableCopy]?:[NSMutableDictionary dictionary];
    NSString *uid=user[@"id"],*name=links[uid];
    if(!name.length){
        NSString *base=links.count?DMGameName(user[@"username"]?:@""):[NSUserName() stringByReplacingOccurrencesOfString:@"[^A-Za-z0-9]" withString:@"" options:NSRegularExpressionSearch range:NSMakeRange(0,NSUserName().length)];
        if(!base.length)base=@"Player";
        name=base;NSSet *taken=[NSSet setWithArray:links.allValues];
        for(int i=2;[taken containsObject:name];i++)name=[NSString stringWithFormat:@"%@%d",[base substringToIndex:MIN(base.length,(NSUInteger)29)],i];
        links[uid]=name;DMWriteJSON(@"discord-links.json",links);
    }
    id global=user[@"global_name"];
    DMWriteJSON(@"discord-account.json",@{@"id":uid,@"username":user[@"username"]?:@"",@"global_name":[global isKindOfClass:NSString.class]?global:@"",
        @"game_name":name,@"signed_in":[NSISO8601DateFormatter stringFromDate:NSDate.date timeZone:NSTimeZone.localTimeZone formatOptions:NSISO8601DateFormatWithInternetDateTime]});
    if(DMLinkService.length&&access.length){   // best effort: a failed report only delays the Discord roles
        NSMutableURLRequest *r=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:[DMLinkService stringByAppendingString:@"/played"]]];r.HTTPMethod=@"POST";
        [r setValue:[@"Bearer " stringByAppendingString:access] forHTTPHeaderField:@"Authorization"];[r setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
        r.HTTPBody=[NSJSONSerialization dataWithJSONObject:@{@"game_name":name} options:0 error:nil];
        [[NSURLSession.sharedSession dataTaskWithRequest:r completionHandler:^(NSData *d,NSURLResponse *resp,NSError *e){}] resume];
    }
    if(self.waitingAlert){[self.window endSheet:self.waitingAlert.window];self.waitingAlert=nil;}
    [self refreshAccountRow];
    [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
}
- (NSTextField *)field:(NSString *)placeholder secure:(BOOL)secure value:(NSString *)value y:(CGFloat)y in:(NSView *)view {
    NSTextField *f=secure?[NSSecureTextField new]:[NSTextField new];f.frame=NSMakeRect(0,y,300,24);f.placeholderString=placeholder;if(value)f.stringValue=value;[view addSubview:f];return f;
}
// Host for friends: the world list (its button "Host this world"), then the password; with no world yet, the password
// and the first world, as before the list.
- (void)chooseHost:(id)sender {
    if(DMListWorlds(DMDataDir()).count){[self showWorlds:YES pick:nil];return;}
    [self askHostPasswordFor:nil];
}
- (void)askHostPasswordFor:(NSDictionary *)world {
    NSAlert *a=[NSAlert new];a.messageText=world?[NSString stringWithFormat:@"Host “%@” for friends",world[@"label"]]:@"Host for friends";
    a.informativeText=@"Choose a password your friends will type to join. Once the world is open, the Realm tab shows the address to give them. macOS may ask to allow incoming connections: allow it.";
    NSView *box=[[NSView alloc] initWithFrame:NSMakeRect(0,0,300,24)];
    NSTextField *pw=[self field:@"Password (at least 4 characters)" secure:YES value:nil y:0 in:box];a.accessoryView=box;
    [a addButtonWithTitle:@"Open my world"];[a addButtonWithTitle:@"Back"];a.window.initialFirstResponder=pw;
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r!=NSAlertFirstButtonReturn)return;
        NSString *p=[pw.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if(p.length<4){NSAlert *e=[NSAlert new];e.messageText=@"The password needs at least 4 characters.";[e beginSheetModalForWindow:self.window completionHandler:nil];return;}
        if(world)DMWorldSetMeta(world,@"last_played",DMWorldStamp(NSDate.date));
        [self.window orderOut:nil];[self startWith:[self withAccount:world?@[@"--host",@"--world",world[@"folder"]]:@[@"--host"]] password:p];
    }];
}
- (void)chooseJoin:(id)sender {
    NSAlert *a=[NSAlert new];a.messageText=@"Join a friend";
    a.informativeText=@"Enter the address your friend sees in their Realm tab (for example 192.168.1.20) and their password. You both need to be on the same network.";
    NSView *box=[[NSView alloc] initWithFrame:NSMakeRect(0,0,300,56)];
    NSString *last=[NSUserDefaults.standardUserDefaults stringForKey:@"lastJoinAddress"];
    NSTextField *addr=[self field:@"Friend's address" secure:NO value:last y:32 in:box];
    NSTextField *pw=[self field:@"Password" secure:YES value:nil y:0 in:box];a.accessoryView=box;
    [a addButtonWithTitle:@"Join"];[a addButtonWithTitle:@"Back"];a.window.initialFirstResponder=last.length?pw:addr;
    [a beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse r){
        if(r!=NSAlertFirstButtonReturn)return;
        NSString *ad=[addr.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        NSString *p=[pw.stringValue stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        NSRegularExpression *ok=[NSRegularExpression regularExpressionWithPattern:@"^[A-Za-z0-9.:-]+$" options:0 error:nil];
        if(!ad.length||![ok firstMatchInString:ad options:0 range:NSMakeRange(0,ad.length)]){NSAlert *e=[NSAlert new];e.messageText=@"That address does not look right.";e.informativeText=@"Use the address your friend sees in their Realm tab, for example 192.168.1.20.";[e beginSheetModalForWindow:self.window completionHandler:nil];return;}
        [NSUserDefaults.standardUserDefaults setObject:ad forKey:@"lastJoinAddress"];
        [self.window orderOut:nil];[self startWith:[self withAccount:@[@"--join",ad]] password:p];
    }];
}
- (void)startWith:(NSArray *)passed password:(NSString *)password {
    // The starting window (screens, 2026-10-26): the chooser's art cut to its title, the launch's stage in the brand's
    // face and a bar that moves only with launch.zsh's own stages (preparing, starting, playing, the game window up).
    CGFloat SW=560,SH=264;
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,SW,SH) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskFullSizeContentView backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"Hidden Clans";self.window.titlebarAppearsTransparent=YES;self.window.titleVisibility=NSWindowTitleHidden;
    self.window.appearance=[NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    NSView *lv=self.window.contentView;lv.wantsLayer=YES;lv.layer.backgroundColor=[NSColor colorWithRed:0.086 green:0.067 blue:0.047 alpha:1].CGColor;
    NSString *art=[NSBundle.mainBundle pathForResource:@"launcher-art" ofType:@"png"];NSImage *full=art?[[NSImage alloc] initWithContentsOfFile:art]:nil;
    if(full.size.width>0){NSSize is=full.size;CGFloat ch=is.width*SH/SW;
        NSImage *crop=[NSImage imageWithSize:NSMakeSize(SW,SH) flipped:NO drawingHandler:^BOOL(NSRect dst){[full drawInRect:dst fromRect:NSMakeRect(0,MAX(0,is.height-ch),is.width,MIN(ch,is.height)) operation:NSCompositingOperationCopy fraction:1];return YES;}];
        NSImageView *iv=[NSImageView imageViewWithImage:crop];iv.imageScaling=NSImageScaleAxesIndependently;iv.frame=NSMakeRect(0,0,SW,SH);[lv addSubview:iv];}
    else{NSTextField *brand=[NSTextField labelWithString:@"Hidden Clans"];brand.lineBreakMode=NSLineBreakByClipping;brand.font=[NSFont fontWithName:@"Luminari-Regular" size:30]?:[NSFont boldSystemFontOfSize:26];
        brand.textColor=[NSColor colorWithRed:0.95 green:0.83 blue:0.5 alpha:1];brand.alignment=NSTextAlignmentCenter;brand.frame=NSMakeRect(0,SH-90,SW,40);[lv addSubview:brand];}
    [lv addSubview:[[DMShadeView alloc] initWithFrame:NSMakeRect(0,0,SW,104)]];
    NSShadow *ink=[NSShadow new];ink.shadowColor=[NSColor colorWithWhite:0 alpha:0.9];ink.shadowOffset=NSMakeSize(0,-1);ink.shadowBlurRadius=2;
    NSTextField *label=[NSTextField labelWithString:[passed containsObject:@"--join"]?@"Joining your friend’s world…":@"Starting the world…"];
    label.frame=NSMakeRect(0,60,SW,26);label.font=[NSFont fontWithName:@"Luminari-Regular" size:18]?:[NSFont systemFontOfSize:15];label.alignment=NSTextAlignmentCenter;label.textColor=[NSColor colorWithRed:0.97 green:0.86 blue:0.55 alpha:1];label.shadow=ink;[lv addSubview:label];
    DMStageBar *bar=[[DMStageBar alloc] initWithFrame:NSMakeRect((SW-320)/2,46,320,10)];bar.progress=0.06;[lv addSubview:bar];
    NSTextField *detail=[NSTextField labelWithString:@"The first launch can take a minute."];detail.font=[NSFont systemFontOfSize:12];detail.alignment=NSTextAlignmentCenter;
    detail.textColor=[NSColor colorWithRed:0.78 green:0.72 blue:0.6 alpha:1];detail.frame=NSMakeRect(20,22,SW-40,18);[lv addSubview:detail];
    [self.window center];[self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
    self.statusPath=[NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"dungeon-master-%@.status",NSUUID.UUID.UUIDString]];
    self.task=[NSTask new];self.task.executableURL=[NSURL fileURLWithPath:@"/bin/zsh"];
    NSString *script=[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"launch.zsh"];
    NSMutableArray *args=[NSMutableArray arrayWithObject:script];[args addObjectsFromArray:passed];
    self.task.arguments=args;
    // The join password travels in the environment, never on the command line.
    NSMutableDictionary *env=[NSProcessInfo.processInfo.environment mutableCopy];env[@"DM_LAUNCH_STATUS"]=self.statusPath;if(password.length)env[@"DM_JOIN_PASSWORD"]=password;self.task.environment=env;
    __weak Launcher *weakSelf=self;
    self.task.terminationHandler=^(NSTask *task){dispatch_async(dispatch_get_main_queue(),^{
        Launcher *self=weakSelf;if(!self)return;
        NSString *status=[NSString stringWithContentsOfFile:self.statusPath encoding:NSUTF8StringEncoding error:nil];
        DMLaunchOutcome outcome=DMLaunchOutcomeForExit(task.terminationStatus,self.quitRequested,status);
        self.resultCode=outcome.resultCode;
        if(outcome.showAlert){
            NSString *reason=[status hasPrefix:@"error:"] ? [[status substringFromIndex:6] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet] : nil;
            [self.window orderOut:nil];
            NSAlert *alert=[NSAlert new];alert.messageText=@"Hidden Clans needs attention.";
            alert.informativeText=[NSString stringWithFormat:@"%@The game logs are in Library/Application Support/Hidden Clans/reports.",reason.length ? [reason stringByAppendingString:@"\n\n"] : @""];
            [alert runModal];
        }
        self.finishing=YES;[[NSFileManager defaultManager] removeItemAtPath:self.statusPath error:nil];[NSApp terminate:nil];
    });};
    NSError *error=nil;if(![self.task launchAndReturnError:&error]){self.resultCode=1;NSAlert *alert=[NSAlert alertWithError:error];[alert runModal];self.finishing=YES;[NSApp terminate:nil];return;}
    // The window stays until the game's own window is on screen (the client takes a few seconds to open it after the
    // status says "playing"; hiding at once left nothing on screen), and says what stage it is at (playtest polish).
    __block NSDate *playingSince=nil;
    // the bar: a quarter per stage reached, creeping inside the stage it waits on, never past the next one
    __block int stage=0;__block NSDate *stageSince=[NSDate date];
    [NSTimer scheduledTimerWithTimeInterval:0.5 repeats:YES block:^(NSTimer *timer){
        NSString *status=[NSString stringWithContentsOfFile:weakSelf.statusPath encoding:NSUTF8StringEncoding error:nil];
        int now=[status hasPrefix:@"playing"]?3:[status hasPrefix:@"starting"]?2:[status hasPrefix:@"preparing"]?1:0;
        if(now>stage){stage=now;stageSince=[NSDate date];}
        bar.progress=(stage+0.85*(1-exp(-[[NSDate date] timeIntervalSinceDate:stageSince]/12.0)))/4.0;[bar setNeedsDisplay:YES];
        if([status hasPrefix:@"preparing"])detail.stringValue=@"Getting the world ready…";
        else if([status hasPrefix:@"starting"])detail.stringValue=@"Waking the world. The first launch can take a minute.";
        if(![status hasPrefix:@"playing"])return;
        if(!playingSince){playingSince=[NSDate date];detail.stringValue=@"Opening the game window…";}
        // the game window: a big window of a process the launch script started (owner and size need no permission)
        BOOL shown=NO;pid_t script=weakSelf.task.processIdentifier;
        NSArray *wins=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly|kCGWindowListExcludeDesktopElements,kCGNullWindowID));
        for(NSDictionary *w in wins){
            if([w[(id)kCGWindowLayer] intValue]!=0||[w[(id)kCGWindowBounds][@"Width"] doubleValue]<=600)continue;
            struct proc_bsdinfo info;pid_t owner=[w[(id)kCGWindowOwnerPID] intValue];
            if(proc_pidinfo(owner,PROC_PIDTBSDINFO,0,&info,sizeof info)==sizeof info&&(pid_t)info.pbi_ppid==script){shown=YES;break;}
        }
        if(shown){bar.progress=1;[bar display];}
        if(shown||-[playingSince timeIntervalSinceNow]>45){[weakSelf.window orderOut:nil];[timer invalidate];}
    }];
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if(!self.task)return NSTerminateNow;
    DMLaunchTermination decision=DMLaunchTerminationForRequest(self.finishing,self.quitRequested,self.task.running);
    if(decision.terminateNow)return NSTerminateNow;
    if(decision.signalChild){self.quitRequested=YES;kill(self.task.processIdentifier,SIGTERM);}
    return NSTerminateCancel;
}
@end
int main(int argc,const char *argv[]){@autoreleasepool{[NSApplication sharedApplication];Launcher *delegate=[Launcher new];NSApp.delegate=delegate;[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];[NSApp run];return delegate.resultCode;}}
