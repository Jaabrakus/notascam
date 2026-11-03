#import <Cocoa/Cocoa.h>
#import <signal.h>
#import "LauncherOutcome.h"

@interface Launcher : NSObject <NSApplicationDelegate>
@property NSTask *task;
@property NSWindow *window;
@property NSString *statusPath;
@property BOOL finishing;
@property BOOL quitRequested;
@property int resultCode;
@end
@implementation Launcher
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSMenu *menu=[NSMenu new];NSMenuItem *app=[NSMenuItem new];[menu addItem:app];
    NSMenu *submenu=[NSMenu new];[submenu addItemWithTitle:@"Quit Dungeon Master" action:@selector(terminate:) keyEquivalent:@"q"];app.submenu=submenu;NSApp.mainMenu=menu;
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,420,130) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"Dungeon Master";
    NSTextField *label=[NSTextField labelWithString:@"Starting the world…"];
    label.frame=NSMakeRect(30,65,360,25);label.font=[NSFont systemFontOfSize:17];[self.window.contentView addSubview:label];
    NSProgressIndicator *spinner=[[NSProgressIndicator alloc] initWithFrame:NSMakeRect(30,28,24,24)];spinner.style=NSProgressIndicatorStyleSpinning;[spinner startAnimation:nil];[self.window.contentView addSubview:spinner];
    NSTextField *detail=[NSTextField labelWithString:@"The first launch can take a minute."];
    detail.frame=NSMakeRect(65,28,325,24);[self.window.contentView addSubview:detail];
    [self.window center];[self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
    self.statusPath=[NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"dungeon-master-%@.status",NSUUID.UUID.UUIDString]];
    self.task=[NSTask new];self.task.executableURL=[NSURL fileURLWithPath:@"/bin/zsh"];
    NSString *script=[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"launch.zsh"];
    NSMutableArray *args=[NSMutableArray arrayWithObject:script];
    for(NSString *arg in [NSProcessInfo.processInfo.arguments subarrayWithRange:NSMakeRange(1,NSProcessInfo.processInfo.arguments.count-1)]) {
        if(![arg hasPrefix:@"-psn_"]) [args addObject:arg];
    }
    self.task.arguments=args;
    NSMutableDictionary *env=[NSProcessInfo.processInfo.environment mutableCopy];env[@"DM_LAUNCH_STATUS"]=self.statusPath;self.task.environment=env;
    __weak Launcher *weakSelf=self;
    self.task.terminationHandler=^(NSTask *task){dispatch_async(dispatch_get_main_queue(),^{
        Launcher *self=weakSelf;if(!self)return;
        NSString *status=[NSString stringWithContentsOfFile:self.statusPath encoding:NSUTF8StringEncoding error:nil];
        DMLaunchOutcome outcome=DMLaunchOutcomeForExit(task.terminationStatus,self.quitRequested,status);
        self.resultCode=outcome.resultCode;
        if(outcome.showAlert){
            NSString *reason=[status hasPrefix:@"error:"] ? [[status substringFromIndex:6] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet] : nil;
            [self.window orderOut:nil];
            NSAlert *alert=[NSAlert new];alert.messageText=@"Dungeon Master needs attention.";
            alert.informativeText=[NSString stringWithFormat:@"%@The game logs are in Library/Application Support/Dungeon Master Standalone/reports.",reason.length ? [reason stringByAppendingString:@"\n\n"] : @""];
            [alert runModal];
        }
        self.finishing=YES;[[NSFileManager defaultManager] removeItemAtPath:self.statusPath error:nil];[NSApp terminate:nil];
    });};
    NSError *error=nil;if(![self.task launchAndReturnError:&error]){self.resultCode=1;NSAlert *alert=[NSAlert alertWithError:error];[alert runModal];self.finishing=YES;[NSApp terminate:nil];return;}
    [NSTimer scheduledTimerWithTimeInterval:0.5 repeats:YES block:^(NSTimer *timer){
        NSString *status=[NSString stringWithContentsOfFile:weakSelf.statusPath encoding:NSUTF8StringEncoding error:nil];
        if([status hasPrefix:@"playing"]){[weakSelf.window orderOut:nil];[timer invalidate];}
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
