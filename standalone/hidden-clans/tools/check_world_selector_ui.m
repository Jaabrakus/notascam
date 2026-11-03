// tools/check_world_selector.py --ui: the launcher's own code (mac-app/Launcher.m, included below) driven with no window
// on screen and no input: windows never come forward, sheets are answered from a queue, a launch is recorded instead of
// run, the Trash is a folder under the test's own. Prints PASS/FAIL lines and DONE; saves pictures of the window.
//   world_ui_test <data folder made by the check> <trash folder> <pictures folder>
#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>
#define main launcher_main
#include "Launcher.m"
#undef main

static int failures=0;
static void check(NSString *name,BOOL ok,NSString *detail) {
    if(!ok)failures++;
    printf("%s %s%s\n",ok?"PASS":"FAIL",name.UTF8String,ok||!detail.length?"":[[NSString stringWithFormat:@"  (%@)",[detail stringByReplacingOccurrencesOfString:@"\n" withString:@" "]] UTF8String]);
}

static NSMutableArray *answers;      // each: @[field text or NSNull, @(NSModalResponse)]
static NSMutableArray *sheets;       // the message of every sheet begun
static NSArray *launched;            // the last startWith:'s arguments
static NSString *launchedPassword;
static NSString *trashFolder;

@implementation NSWindow (WorldUITest)
- (void)wt_makeKeyAndOrderFront:(id)sender {}
@end
@implementation NSApplication (WorldUITest)
- (void)wt_activateIgnoringOtherApps:(BOOL)flag {}
@end
@implementation NSAlert (WorldUITest)
- (void)wt_beginSheetModalForWindow:(NSWindow *)window completionHandler:(void (^)(NSModalResponse))handler {
    [sheets addObject:self.messageText?:@""];
    NSArray *a=answers.count?answers.firstObject:@[NSNull.null,@(NSAlertSecondButtonReturn)];if(answers.count)[answers removeObjectAtIndex:0];
    if([a[0] isKindOfClass:NSString.class])for(NSView *v in self.accessoryView.subviews)if([v isKindOfClass:NSTextField.class]){((NSTextField *)v).stringValue=a[0];break;}
    if(handler)handler([a[1] integerValue]);
}
@end
@implementation Launcher (WorldUITest)
- (void)wt_startWith:(NSArray *)passed password:(NSString *)password {launched=passed;launchedPassword=password;}
@end
@implementation NSFileManager (WorldUITest)
- (BOOL)wt_trashItemAtURL:(NSURL *)url resultingItemURL:(NSURL **)out error:(NSError **)error {
    return [self moveItemAtPath:url.path toPath:[trashFolder stringByAppendingPathComponent:url.lastPathComponent] error:error];
}
@end
static void swap(Class c,SEL a,SEL b) {method_exchangeImplementations(class_getInstanceMethod(c,a),class_getInstanceMethod(c,b));}

static void snap(NSView *v,NSString *path) {
    [v layoutSubtreeIfNeeded];
    NSBitmapImageRep *rep=[v bitmapImageRepForCachingDisplayInRect:v.bounds];[v cacheDisplayInRect:v.bounds toBitmapImageRep:rep];
    [[rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:path atomically:YES];
}
static NSArray *texts(NSView *v) {
    NSMutableArray *out=[NSMutableArray array];
    if([v isKindOfClass:NSTextField.class])[out addObject:((NSTextField *)v).stringValue];
    if([v isKindOfClass:NSButton.class])[out addObject:((NSButton *)v).title];
    for(NSView *s in v.subviews)[out addObjectsFromArray:texts(s)];
    return out;
}
static BOOL has(NSView *v,NSString *text) {
    for(NSString *t in texts(v))if([t rangeOfString:text].location!=NSNotFound)return YES;
    return NO;
}
static NSString *joined(NSArray *a) {return [a componentsJoinedByString:@" "];}
static NSString *meta(NSString *data,NSString *folder,NSString *key) {
    return DMWorldReadJSON([[data stringByAppendingPathComponent:folder] stringByAppendingPathComponent:DMWorldMetaFile])[key];
}

int main(int argc,const char *argv[]) {@autoreleasepool{
    if(argc<4){printf("usage: world_ui_test <data> <trash> <pictures>\n");return 2;}
    NSString *data=[NSString stringWithUTF8String:argv[1]],*shots=[NSString stringWithUTF8String:argv[3]];trashFolder=[NSString stringWithUTF8String:argv[2]];
    setenv("DM_STANDALONE_DATA_DIR",argv[1],1);
    [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
    swap(NSWindow.class,@selector(makeKeyAndOrderFront:),@selector(wt_makeKeyAndOrderFront:));
    swap(NSApplication.class,@selector(activateIgnoringOtherApps:),@selector(wt_activateIgnoringOtherApps:));
    swap(NSAlert.class,@selector(beginSheetModalForWindow:completionHandler:),@selector(wt_beginSheetModalForWindow:completionHandler:));
    swap(Launcher.class,@selector(startWith:password:),@selector(wt_startWith:password:));
    swap(NSFileManager.class,@selector(trashItemAtURL:resultingItemURL:error:),@selector(wt_trashItemAtURL:resultingItemURL:error:));
    answers=[NSMutableArray array];sheets=[NSMutableArray array];
    Launcher *L=[Launcher new];NSApp.delegate=L;L.listenSocket=-1;
    NSFileManager *fm=NSFileManager.defaultManager;

    // No world yet: Play goes straight in, as before the list.
    NSString *empty=[data stringByAppendingString:@"-empty"];setenv("DM_STANDALONE_DATA_DIR",empty.UTF8String,1);
    [L showChooser];
    [L choosePlay:nil];
    check(@"no world: Play starts the first world at once",launched&&![launched containsObject:@"--world"]&&!L.worldView,joined(launched));
    launched=nil;[L showChooser];
    [answers addObject:@[@"abcd",@(NSAlertFirstButtonReturn)]];
    [L chooseHost:nil];
    check(@"no world: Host asks the password, then the first world",[launched containsObject:@"--host"]&&![launched containsObject:@"--world"]&&[launchedPassword isEqualToString:@"abcd"],joined(launched));

    // Three worlds (made by the check): the list.
    setenv("DM_STANDALONE_DATA_DIR",data.UTF8String,1);launched=nil;
    [L showChooser];snap(L.window.contentView,[shots stringByAppendingPathComponent:@"1-chooser.png"]);
    [L choosePlay:nil];
    snap(L.window.contentView,[shots stringByAppendingPathComponent:@"2-list.png"]);
    check(@"Play opens the list",L.worldView&&L.mainView.hidden&&L.accountRow.hidden&&!launched,nil);
    check(@"three rows, the last played picked",L.worldRows.count==3&&L.pickedWorld==0&&L.worldRows[0].picked&&[L.worlds[0][@"folder"] isEqualToString:@"world"],joined([L.worlds valueForKey:@"folder"]));
    check(@"row texts",has(L.worldView,@"Mountains of the Hidden Temple")&&has(L.worldView,@"Your company: 63 Dwarves")&&has(L.worldView,@"Fall of 975")
          &&has(L.worldView,@"Friday nights")&&has(L.worldView,@"1 friend's company")&&has(L.worldView,@"No company of yours here yet")&&has(L.worldView,@"last played"),joined(texts(L.worldView)));
    check(@"title and buttons",has(L.worldView,@"Choose a world")&&has(L.worldView,@"Continue")&&has(L.worldView,@"New world")&&has(L.worldView,@"Rename")&&has(L.worldView,@"Move to Trash")&&has(L.worldView,@"Back"),nil);
    check(@"signed-in name shown",has(L.worldView,@"Signed in with Discord as Kiwi"),nil);
    check(@"Play's Return goes to the list's button",[L.playButton.keyEquivalent isEqualToString:@""],nil);
    NSInteger pics=0;for(DMWorldRow *r in L.worldRows)for(NSView *s in r.subviews)for(NSView *t in s.subviews)if([t isKindOfClass:NSImageView.class])pics++;
    check(@"race pictures for your companies",pics==2,[NSString stringWithFormat:@"%ld",(long)pics]);

    // Keys: down moves the pick; Return plays the picked world.
    DMWorldList *list=(DMWorldList *)L.worldRows[0].superview;
    NSEvent *down=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:L.window.windowNumber context:nil characters:@"" charactersIgnoringModifiers:@"" isARepeat:NO keyCode:125];
    [list keyDown:down];
    check(@"down arrow picks the next world",L.pickedWorld==1&&L.worldRows[1].picked&&!L.worldRows[0].picked,nil);
    [list keyDown:down];[list keyDown:down];
    check(@"the pick stops at the last world",L.pickedWorld==2,nil);
    [L pickWorld:1];
    NSEvent *ret=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:0 timestamp:0 windowNumber:L.window.windowNumber context:nil characters:@"\r" charactersIgnoringModifiers:@"\r" isARepeat:NO keyCode:36];
    BOOL took=[L.window performKeyEquivalent:ret];
    NSString *second=L.worlds[1][@"folder"];
    check(@"Return plays the picked world",took&&[launched containsObject:@"--world"]&&[launched containsObject:second]&&[launched containsObject:@"--username"]&&[launched containsObject:@"Kiwi"],joined(launched));
    check(@"its last played is written",DMWorldStampDate(meta(data,second,@"last_played"))!=nil,nil);

    // Rename: the label only; the pick stays on the renamed world; too long refused.
    [L showChooser];[L choosePlay:nil];
    check(@"the world just played is first now",[L.worlds[0][@"folder"] isEqualToString:second],nil);
    [L pickWorld:1];NSString *renamed=L.worlds[1][@"folder"];
    [answers addObject:@[@"  Old home ",@(NSAlertFirstButtonReturn)]];
    [L worldRename:nil];
    check(@"rename: label saved, trimmed",[meta(data,renamed,@"label") isEqualToString:@"Old home"],meta(data,renamed,@"label"));
    check(@"rename: the list shows it, still picked",has(L.worldView,@"Old home")&&[L.worlds[L.pickedWorld][@"folder"] isEqualToString:renamed],nil);
    snap(L.window.contentView,[shots stringByAppendingPathComponent:@"3-renamed.png"]);
    [answers addObject:@[[@"" stringByPaddingToLength:41 withString:@"x" startingAtIndex:0],@(NSAlertFirstButtonReturn)]];
    [sheets removeAllObjects];[L worldRename:nil];
    check(@"rename: too long refused",[sheets.lastObject isEqualToString:@"That name is too long."]&&[meta(data,renamed,@"label") isEqualToString:@"Old home"],joined(sheets));
    [answers addObject:@[@"Never",@(NSAlertSecondButtonReturn)]];
    [L worldRename:nil];
    check(@"rename: Back changes nothing",[meta(data,renamed,@"label") isEqualToString:@"Old home"],nil);

    // New world: made, then played.
    NSUInteger before=[[fm contentsOfDirectoryAtPath:[data stringByAppendingPathComponent:@"worlds"] error:nil] count];launched=nil;
    [answers addObject:@[@"Test realm",@(NSAlertFirstButtonReturn)]];
    [L worldNew:nil];
    NSArray *made=[fm contentsOfDirectoryAtPath:[data stringByAppendingPathComponent:@"worlds"] error:nil];
    NSString *fresh=nil;for(NSString *n in made)if([meta(data,[@"worlds/" stringByAppendingString:n],@"label") isEqualToString:@"Test realm"])fresh=[@"worlds/" stringByAppendingString:n];
    check(@"new world: folder and name",made.count==before+1&&fresh&&DMWorldFolderOK(fresh),joined(made));
    check(@"new world: played at once",[launched containsObject:fresh],joined(launched));

    // Move to Trash: refused while the game runs; asks; into the Trash; Put Back brings it again.
    [L showChooser];[L choosePlay:nil];
    NSUInteger at=[[L.worlds valueForKey:@"folder"] indexOfObject:fresh];[L pickWorld:(NSInteger)at];
    [fm createDirectoryAtPath:[data stringByAppendingPathComponent:@"launcher.lock"] withIntermediateDirectories:YES attributes:nil error:nil];
    [[NSString stringWithFormat:@"%d\n",getpid()] writeToFile:[data stringByAppendingPathComponent:@"launcher.lock/pid"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    [sheets removeAllObjects];[L worldTrash:nil];
    check(@"trash: refused while the game runs",[sheets.lastObject isEqualToString:@"Close the game first."]&&[fm fileExistsAtPath:[data stringByAppendingPathComponent:fresh]],joined(sheets));
    [fm removeItemAtPath:[data stringByAppendingPathComponent:@"launcher.lock"] error:nil];
    [answers addObject:@[NSNull.null,@(NSAlertSecondButtonReturn)]];
    [sheets removeAllObjects];[L worldTrash:nil];
    check(@"trash: Cancel keeps it",[sheets.lastObject hasPrefix:@"Move “Test realm” to the Trash?"]&&[fm fileExistsAtPath:[data stringByAppendingPathComponent:fresh]],joined(sheets));
    NSUInteger rows=L.worldRows.count;
    [answers addObject:@[NSNull.null,@(NSAlertFirstButtonReturn)]];
    [L worldTrash:nil];
    check(@"trash: moved to the Trash, gone from the list",![fm fileExistsAtPath:[data stringByAppendingPathComponent:fresh]]&&[fm fileExistsAtPath:[trashFolder stringByAppendingPathComponent:fresh.lastPathComponent]]&&L.worldRows.count==rows-1,nil);
    [fm moveItemAtPath:[trashFolder stringByAppendingPathComponent:fresh.lastPathComponent] toPath:[data stringByAppendingPathComponent:fresh] error:nil];
    [L showWorlds:NO pick:nil];
    check(@"put back: listed again",L.worldRows.count==rows&&[[L.worlds valueForKey:@"folder"] containsObject:fresh],nil);

    // Host for friends: the list in host mode, then the password for that world.
    [L worldBack:nil];
    check(@"Back: the big buttons again",!L.worldView&&!L.mainView.hidden&&!L.accountRow.hidden&&[L.playButton.keyEquivalent isEqualToString:@"\r"],nil);
    launched=nil;[L chooseHost:nil];
    check(@"Host opens the list in host mode",L.hostMode&&has(L.worldView,@"Host for friends: choose a world")&&has(L.worldView,@"Host this world"),nil);
    snap(L.window.contentView,[shots stringByAppendingPathComponent:@"4-host.png"]);
    [L pickWorld:1];NSString *hosted=L.worlds[1][@"folder"];
    [answers addObject:@[@"ab",@(NSAlertFirstButtonReturn)]];[sheets removeAllObjects];
    [L worldGo:nil];
    check(@"host: a short password refused",!launched&&[sheets.lastObject isEqualToString:@"The password needs at least 4 characters."],joined(sheets));
    [answers addObject:@[@"secret",@(NSAlertFirstButtonReturn)]];[sheets removeAllObjects];
    [L worldGo:nil];
    check(@"host: that world, with the password",[launched containsObject:@"--host"]&&[launched containsObject:hosted]&&[launchedPassword isEqualToString:@"secret"]&&[sheets.firstObject hasPrefix:@"Host “"],joined(launched));

    printf("DONE %d failed\n",failures);
    return failures?1:0;
}}
