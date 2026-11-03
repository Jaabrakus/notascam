// tools/check_world_selector.py compiles this against mac-app/LauncherWorlds.h and runs it on a temporary folder
// (argv[1]); it prints PASS/FAIL lines and DONE. Every folder it makes is under argv[1].
#import <Foundation/Foundation.h>
#import "LauncherWorlds.h"

static int failures=0;
static void check(NSString *name,BOOL ok,NSString *detail) {
    if(!ok)failures++;
    printf("%s %s%s\n",ok?"PASS":"FAIL",name.UTF8String,ok||!detail.length?"":[[NSString stringWithFormat:@"  (%@)",detail] UTF8String]);
}
static void put(NSString *path,NSString *text) {
    [[NSFileManager defaultManager] createDirectoryAtPath:path.stringByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:nil];
    [text writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
}
static void touch(NSString *path,NSDate *when) {
    [[NSFileManager defaultManager] setAttributes:@{NSFileModificationDate:when} ofItemAtPath:path error:nil];
}
static NSArray *folders(NSArray *worlds) {return [worlds valueForKey:@"folder"];}

int main(int argc,const char *argv[]) {@autoreleasepool{
    if(argc<2){printf("usage: test <empty folder>\n");return 2;}
    NSString *root=[NSString stringWithUTF8String:argv[1]];
    NSDate *now=[NSDate date];

    // Folder names
    for(NSString *ok in @[@"world",@"worlds/20261031-0912",@"worlds/a_b-C9"])check([@"folder ok " stringByAppendingString:ok],DMWorldFolderOK(ok),nil);
    for(NSString *bad in @[@"",@"world2",@"worlds/",@"worlds/..",@"worlds/a/b",@"../world",@"/tmp",@"worlds/a b",[@"worlds/" stringByPaddingToLength:48 withString:@"x" startingAtIndex:0]])
        check([NSString stringWithFormat:@"folder refused '%@'",bad],!DMWorldFolderOK(bad),nil);

    // An empty data folder, and one with only an unplayed first world (made by a join): no worlds.
    NSString *data=[root stringByAppendingPathComponent:@"empty"];
    check(@"empty: no worlds",DMListWorlds(data).count==0,nil);
    [[NSFileManager defaultManager] createDirectoryAtPath:[data stringByAppendingPathComponent:@"world/Code"] withIntermediateDirectories:YES attributes:nil error:nil];
    check(@"unplayed first world not listed",DMListWorlds(data).count==0,nil);

    // Today's layout: the first world with a save, no facts yet.
    data=[root stringByAppendingPathComponent:@"legacy"];
    put([data stringByAppendingPathComponent:@"world/units/remaster_world.sav"],@"{}");
    touch([data stringByAppendingPathComponent:@"world/units/remaster_world.sav"],[now dateByAddingTimeInterval:-3*86400]);
    NSArray *w=DMListWorlds(data);
    check(@"legacy: one world",w.count==1&&[w[0][@"folder"] isEqualToString:@"world"],[folders(w) description]);
    check(@"legacy: label",[w[0][@"label"] isEqualToString:@"Your first world"],w[0][@"label"]);
    check(@"legacy: facts wait for a save",[DMWorldFacts(w[0],@"Kiwi") isEqualToString:@"Its details appear after your next save"],DMWorldFacts(w[0],@"Kiwi"));
    check(@"legacy: last played from the save",fabs([w[0][@"lastPlayed"] timeIntervalSinceDate:[now dateByAddingTimeInterval:-3*86400]])<2,[w[0][@"lastPlayed"] description]);

    // Facts: the first world after a save under the new build (key as the engine writes it, "localhost@Kiwi_2").
    put([data stringByAppendingPathComponent:@"world/world-info.json"],@"{\"version\":1,\"name\":\" Mountains of the Hidden Temple\",\"season\":\"Fall\",\"year\":975,\"age\":\"Age of the Burning Dragon\","
        "\"players\":{\"localhost@kiwi2\":{\"key\":\"localhost@Kiwi_2\",\"race\":\"Dwarf\",\"units\":63},\"localhost@friend\":{\"key\":\"Friend\",\"race\":\"Elf\",\"units\":4}}}");
    w=DMListWorlds(data);
    check(@"facts: land name trimmed as label",[w[0][@"label"] isEqualToString:@"Mountains of the Hidden Temple"],w[0][@"label"]);
    NSString *facts=DMWorldFacts(w[0],@"Kiwi_2");
    check(@"facts: your company",[facts isEqualToString:@"Your company: 63 Dwarves · Fall of 975 · Age of the Burning Dragon · 1 friend's company"],facts);
    check(@"facts: race picture",[DMWorldRace(w[0],@"kiwi_2") isEqualToString:@"Dwarf"]&&DMWorldRaceIndex(@"Dwarf")==1&&DMWorldRaceIndex(@"Illithid")==13,nil);
    facts=DMWorldFacts(w[0],@"Stranger");
    check(@"facts: no company of yours",[facts hasPrefix:@"No company of yours here yet · Fall of 975"]&&[facts hasSuffix:@"2 friends' companies"],facts);
    check(@"facts: no race picture for a stranger",DMWorldRace(w[0],@"Stranger")==nil,nil);
    put([data stringByAppendingPathComponent:@"world/world-info.json"],@"{\"season\":\"Winter\",\"year\":12,\"players\":{\"localhost@kiwi\":{\"key\":\"Kiwi\",\"race\":\"Elf\",\"units\":0}}}");
    facts=DMWorldFacts(DMListWorlds(data)[0],@"Kiwi");
    check(@"facts: none left",[facts isEqualToString:@"Your company: none left · Winter of 12"],facts);
    put([data stringByAppendingPathComponent:@"world/world-info.json"],@"{\"players\":{\"localhost@kiwi\":{\"key\":\"Kiwi\",\"race\":\"Elf\",\"units\":1}}}");
    facts=DMWorldFacts(DMListWorlds(data)[0],@"Kiwi");
    check(@"facts: one unit",[facts isEqualToString:@"Your company: 1 Elf"],facts);
    put([data stringByAppendingPathComponent:@"world/world-info.json"],@"{\"name\":\"broken");
    w=DMListWorlds(data);
    check(@"facts: a broken file only shows less",w.count==1&&[w[0][@"label"] isEqualToString:@"Your first world"],[w description]);
    check(@"plurals",[DMWorldRacePlural(@"Lizardman") isEqualToString:@"Lizardmen"]&&[DMWorldRacePlural(@"Orc") isEqualToString:@"Orcs"]&&[DMWorldRacePlural(@"Svartalfar") isEqualToString:@"Svartalfar"],nil);

    // New worlds, names, last played order, rename.
    NSString *name=DMWorldNameClean(@"  Friday nights \n");
    check(@"name trimmed",[name isEqualToString:@"Friday nights"],name);
    check(@"name empty allowed",[DMWorldNameClean(@"   ") isEqualToString:@""],nil);
    check(@"name too long refused",DMWorldNameClean([@"" stringByPaddingToLength:41 withString:@"a" startingAtIndex:0])==nil,nil);
    check(@"name with a tab refused",DMWorldNameClean(@"a\tb")==nil,nil);
    touch([data stringByAppendingPathComponent:@"world/world-info.json"],[now dateByAddingTimeInterval:-2*86400]);   // last saved two days ago
    NSDictionary *a=DMCreateWorld(data,name,now),*b=DMCreateWorld(data,@"",now);
    check(@"create: two folders from one moment",a&&b&&![a[@"folder"] isEqualToString:b[@"folder"]]&&[b[@"folder"] hasSuffix:@"-2"],[NSString stringWithFormat:@"%@ %@",a[@"folder"],b[@"folder"]]);
    check(@"create: folder ok and meta written",DMWorldFolderOK(a[@"folder"])&&[[NSFileManager defaultManager] fileExistsAtPath:[a[@"path"] stringByAppendingPathComponent:DMWorldMetaFile]],nil);
    check(@"create: unnamed shows as a new world",[b[@"label"] isEqualToString:@"A new world"]&&[DMWorldFacts(b,@"Kiwi") isEqualToString:@"Nothing saved yet"],b[@"label"]);
    DMWorldSetMeta(b,@"last_played",DMWorldStamp([now dateByAddingTimeInterval:60]));
    w=DMListWorlds(data);
    check(@"order: last played first",w.count==3&&[w[0][@"folder"] isEqualToString:b[@"folder"]]&&[w[1][@"folder"] isEqualToString:a[@"folder"]]&&[w[2][@"folder"] isEqualToString:@"world"],[folders(w) description]);
    DMWorldSetMeta(w[2],@"label",@"Old home");
    w=DMListWorlds(data);
    check(@"rename: the first world's label",[[w filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"folder == 'world'"]].firstObject[@"label"] isEqualToString:@"Old home"],nil);
    check(@"rename: its saves untouched",[[NSString stringWithContentsOfFile:[data stringByAppendingPathComponent:@"world/units/remaster_world.sav"] encoding:NSUTF8StringEncoding error:nil] isEqualToString:@"{}"],nil);

    // Trash safety: only a world's own real folder inside the data folder; never while the game runs.
    check(@"trashable: a world",DMWorldTrashable(data,a)&&DMWorldTrashable(data,w[2]),nil);
    check(@"trashable: not a made-up folder",!DMWorldTrashable(data,@{@"folder":@"worlds/../world"})&&!DMWorldTrashable(data,@{@"folder":@"worlds/nothere"}),nil);
    NSString *outside=[root stringByAppendingPathComponent:@"outside"];
    [[NSFileManager defaultManager] createDirectoryAtPath:outside withIntermediateDirectories:YES attributes:nil error:nil];
    [[NSFileManager defaultManager] createSymbolicLinkAtPath:[data stringByAppendingPathComponent:@"worlds/link"] withDestinationPath:outside error:nil];
    put([outside stringByAppendingPathComponent:DMWorldMetaFile],@"{}");
    check(@"trashable: not a link out",!DMWorldTrashable(data,@{@"folder":@"worlds/link"}),nil);
    check(@"not running without a lock",!DMGameRunning(data),nil);
    put([data stringByAppendingPathComponent:@"launcher.lock/pid"],[NSString stringWithFormat:@"%d\n",getpid()]);
    check(@"running with a live lock",DMGameRunning(data),nil);
    put([data stringByAppendingPathComponent:@"launcher.lock/pid"],@"999999\n");
    check(@"not running with a dead lock",!DMGameRunning(data),nil);
    put([a[@"path"] stringByAppendingPathComponent:@"units/x.sav"],[@"" stringByPaddingToLength:1000 withString:@"x" startingAtIndex:0]);
    put([a[@"path"] stringByAppendingPathComponent:@"Code/World.dm"],[@"" stringByPaddingToLength:5000 withString:@"x" startingAtIndex:0]);
    check(@"saves size counts saves only",DMWorldSavesSize(a)==1000,[NSString stringWithFormat:@"%llu",DMWorldSavesSize(a)]);

    // A world put back from the Trash comes back; one without the launcher's file is not a world.
    [[NSFileManager defaultManager] createDirectoryAtPath:[data stringByAppendingPathComponent:@"worlds/stray"] withIntermediateDirectories:YES attributes:nil error:nil];
    NSUInteger before=DMListWorlds(data).count;
    [[NSFileManager defaultManager] moveItemAtPath:a[@"path"] toPath:[root stringByAppendingPathComponent:@"trash-a"] error:nil];
    check(@"gone from the list",DMListWorlds(data).count==before-1,nil);
    [[NSFileManager defaultManager] moveItemAtPath:[root stringByAppendingPathComponent:@"trash-a"] toPath:a[@"path"] error:nil];
    check(@"put back: listed again",DMListWorlds(data).count==before,nil);
    check(@"a stray folder without the launcher's file is not a world",[[folders(DMListWorlds(data)) filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"SELF == 'worlds/stray'"]] count]==0,nil);

    // Dates as the row shows them.
    NSCalendar *cal=NSCalendar.currentCalendar;NSDate *noon=[cal dateBySettingHour:12 minute:0 second:0 ofDate:now options:0];
    NSDate *morning=[cal dateBySettingHour:9 minute:12 second:0 ofDate:now options:0];
    check(@"when: today",[DMWorldWhen(morning,noon) isEqualToString:@"Today, 09:12"],DMWorldWhen(morning,noon));
    check(@"when: yesterday",[DMWorldWhen([morning dateByAddingTimeInterval:-86400],noon) isEqualToString:@"Yesterday, 09:12"],DMWorldWhen([morning dateByAddingTimeInterval:-86400],noon));
    check(@"when: never",[DMWorldWhen([NSDate distantPast],noon) isEqualToString:@""],nil);
    NSDate *lastYear=[cal dateByAddingUnit:NSCalendarUnitYear value:-1 toDate:noon options:0];
    check(@"when: another year",[DMWorldWhen(lastYear,noon) rangeOfString:@", 20"].location!=NSNotFound,DMWorldWhen(lastYear,noon));

    printf("DONE %d failed\n",failures);
    return failures?1:0;
}}
