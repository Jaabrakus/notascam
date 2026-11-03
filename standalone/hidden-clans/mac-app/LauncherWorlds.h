#import <Foundation/Foundation.h>
#import <signal.h>

// The launcher's world list (planning/WORLD_SELECTOR_PLAN_2026-10-31.md), kept apart from the window so
// tools/check_world_selector.py can test it. A world is a folder in the data folder: "world" (the first one, where every
// world was before 10-31) or "worlds/<id>". Each has botd-world.json (the launcher's: label, created, last played, seed)
// and, after its first save, world-info.json (the game's facts, WorldSave.dm RmWorldInfo). The big saves are never read.

static NSString *const DMWorldMetaFile=@"botd-world.json";
static NSString *const DMWorldInfoFile=@"world-info.json";

// The order of the race card's pictures (art/hud/src/assets/screens-races.png, 192x128 a cell; make_screens_art.py).
static inline NSInteger DMWorldRaceIndex(NSString *race) {
    NSArray *order=@[@"Human",@"Dwarf",@"Elf",@"Orc",@"Goblin",@"Lizardman",@"Frogman",@"Kobold",@"Ratman",@"Dragon",@"Spider",@"Devourer",@"Svartalfar",@"Illithid"];
    return [race isKindOfClass:NSString.class]?(NSInteger)[order indexOfObject:race]:NSNotFound;
}
static inline NSString *DMWorldRacePlural(NSString *race) {
    NSDictionary *odd=@{@"Dwarf":@"Dwarves",@"Elf":@"Elves",@"Lizardman":@"Lizardmen",@"Frogman":@"Frogmen",@"Ratman":@"Ratmen",@"Svartalfar":@"Svartalfar"};
    if(![race isKindOfClass:NSString.class]||!race.length)return @"people";
    return odd[race]?:[race stringByAppendingString:@"s"];
}

// A folder the launcher may use: "world" or "worlds/" + 1-40 of letters, digits, - and _ (launch.zsh checks the same).
static inline BOOL DMWorldFolderOK(NSString *folder) {
    if(![folder isKindOfClass:NSString.class])return NO;
    if([folder isEqualToString:@"world"])return YES;
    return [folder rangeOfString:@"^worlds/[A-Za-z0-9_-]{1,40}$" options:NSRegularExpressionSearch].location!=NSNotFound;
}

static inline NSDictionary *DMWorldReadJSON(NSString *path) {
    NSData *data=[NSData dataWithContentsOfFile:path];
    id object=data?[NSJSONSerialization JSONObjectWithData:data options:0 error:nil]:nil;
    return [object isKindOfClass:NSDictionary.class]?object:nil;
}
static inline BOOL DMWorldWriteJSON(NSString *path,NSDictionary *object) {
    NSData *data=[NSJSONSerialization dataWithJSONObject:object options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:nil];
    if(!data||![data writeToFile:path atomically:YES])return NO;
    [[NSFileManager defaultManager] setAttributes:@{NSFilePosixPermissions:@0600} ofItemAtPath:path error:nil];
    return YES;
}
static inline NSString *DMWorldText(id value) {
    return [value isKindOfClass:NSString.class]?[value stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet]:@"";
}

static inline NSString *DMWorldStamp(NSDate *date) {
    return [NSISO8601DateFormatter stringFromDate:date timeZone:NSTimeZone.localTimeZone formatOptions:NSISO8601DateFormatWithInternetDateTime];
}
static inline NSDate *DMWorldStampDate(id value) {
    return [value isKindOfClass:NSString.class]?[[NSISO8601DateFormatter new] dateFromString:value]:nil;
}
static inline NSDate *DMWorldModified(NSString *path) {
    return [[NSFileManager defaultManager] attributesOfItemAtPath:path error:nil][NSFileModificationDate];
}

// A typed world name as kept: no line breaks or control characters, spaces trimmed, at most 40 characters. nil when
// too long or not printable; "" when empty (New world: the land names itself).
static inline NSString *DMWorldNameClean(NSString *typed) {
    NSString *name=DMWorldText(typed);
    if(name.length>40)return nil;
    if([name rangeOfCharacterFromSet:NSCharacterSet.controlCharacterSet].location!=NSNotFound)return nil;
    return name;
}

// One world as the list shows it: folder, path, label (Rename's, else the land's name), land, info (world-info.json or
// nil), lastPlayed, first (YES for "world").
static inline NSDictionary *DMWorldEntry(NSString *data,NSString *folder) {
    NSString *path=[data stringByAppendingPathComponent:folder];
    NSDictionary *meta=DMWorldReadJSON([path stringByAppendingPathComponent:DMWorldMetaFile])?:@{};
    NSDictionary *info=DMWorldReadJSON([path stringByAppendingPathComponent:DMWorldInfoFile]);
    BOOL first=[folder isEqualToString:@"world"];
    NSString *land=DMWorldText(info[@"name"]),*label=DMWorldText(meta[@"label"]);
    if(!label.length)label=land.length?land:(first?@"Your first world":@"A new world");
    NSDate *played=DMWorldStampDate(meta[@"last_played"])?:DMWorldModified([path stringByAppendingPathComponent:DMWorldInfoFile])
        ?:DMWorldModified([path stringByAppendingPathComponent:@"units/remaster_world.sav"])?:DMWorldStampDate(meta[@"created"])?:DMWorldModified(path)?:[NSDate distantPast];
    NSMutableDictionary *e=[@{@"folder":folder,@"path":path,@"label":label,@"land":land,@"lastPlayed":played,@"first":@(first),@"meta":meta} mutableCopy];
    if(info)e[@"info"]=info;
    return e;
}

// Every world in the data folder, last played first. The first world counts once it has been played (a save, its
// facts or the launcher's file); "worlds/<id>" counts when it has the launcher's file, so one put back from the Trash
// comes back on its own.
static inline NSArray<NSDictionary *> *DMListWorlds(NSString *data) {
    NSFileManager *fm=[NSFileManager defaultManager];NSMutableArray *found=[NSMutableArray array];
    NSString *first=[data stringByAppendingPathComponent:@"world"];
    for(NSString *f in @[DMWorldMetaFile,DMWorldInfoFile,@"units/remaster_world.sav",@"units/remaster_world.sav.bak"])
        if([fm fileExistsAtPath:[first stringByAppendingPathComponent:f]]){[found addObject:DMWorldEntry(data,@"world")];break;}
    NSString *more=[data stringByAppendingPathComponent:@"worlds"];
    for(NSString *name in [fm contentsOfDirectoryAtPath:more error:nil]){
        NSString *folder=[@"worlds/" stringByAppendingString:name];
        if(DMWorldFolderOK(folder)&&[fm fileExistsAtPath:[[more stringByAppendingPathComponent:name] stringByAppendingPathComponent:DMWorldMetaFile]])
            [found addObject:DMWorldEntry(data,folder)];
    }
    [found sortUsingComparator:^NSComparisonResult(NSDictionary *a,NSDictionary *b){
        NSComparisonResult r=[b[@"lastPlayed"] compare:a[@"lastPlayed"]];
        return r!=NSOrderedSame?r:[a[@"folder"] compare:b[@"folder"]];
    }];
    return found;
}

// A key as the engine keys saves ("localhost@Kiwi" -> "kiwi"): the part after the last @, letters and digits, lowercase.
static inline NSString *DMWorldKey(NSString *key) {
    if(![key isKindOfClass:NSString.class])return @"";
    NSRange at=[key rangeOfString:@"@" options:NSBackwardsSearch];
    if(at.location!=NSNotFound)key=[key substringFromIndex:at.location+1];
    NSMutableString *s=[NSMutableString string];
    for(NSUInteger i=0;i<key.length;i++){unichar c=[key characterAtIndex:i];
        if((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9'))[s appendFormat:@"%C",(unichar)tolower(c)];}
    return s;
}
// Your company's entry in a world's facts ({key, race, units}), or nil.
static inline NSDictionary *DMWorldCompany(NSDictionary *info,NSString *gameName) {
    NSDictionary *players=[info[@"players"] isKindOfClass:NSDictionary.class]?info[@"players"]:nil;NSString *me=DMWorldKey(gameName);
    if(!me.length)return nil;
    for(NSString *ckey in players){NSDictionary *p=players[ckey];
        if([p isKindOfClass:NSDictionary.class]&&([DMWorldKey(p[@"key"]) isEqualToString:me]||[DMWorldKey(ckey) isEqualToString:me]))return p;}
    return nil;
}
// The race of your company there, for its picture (nil: none yet).
static inline NSString *DMWorldRace(NSDictionary *world,NSString *gameName) {
    NSString *race=DMWorldText(DMWorldCompany(world[@"info"],gameName)[@"race"]);
    return race.length?race:nil;
}

// The row's second line: "Your company: 63 Dwarves · Fall of 975 · Age of the Burning Dragon · 2 friends' companies".
static inline NSString *DMWorldFacts(NSDictionary *world,NSString *gameName) {
    NSDictionary *info=world[@"info"];
    if(!info)return [world[@"first"] boolValue]?@"Its details appear after your next save":@"Nothing saved yet";
    NSMutableArray *parts=[NSMutableArray array];
    NSDictionary *mine=DMWorldCompany(info,gameName);NSString *race=DMWorldText(mine[@"race"]);
    long units=[mine[@"units"] isKindOfClass:NSNumber.class]?[mine[@"units"] longValue]:0;
    if(!mine||(!race.length&&units<=0))[parts addObject:@"No company of yours here yet"];
    else if(units<=0)[parts addObject:@"Your company: none left"];
    else [parts addObject:[NSString stringWithFormat:@"Your company: %ld %@",units,units==1&&race.length?race:DMWorldRacePlural(race)]];
    NSString *season=DMWorldText(info[@"season"]);id year=info[@"year"];
    NSString *when=[year isKindOfClass:NSNumber.class]?[NSString stringWithFormat:@"%@%@%@",season,season.length?@" of ":@"Year ",year]:season;
    if(when.length)[parts addObject:when];
    NSString *age=DMWorldText(info[@"age"]);if(age.length)[parts addObject:age];
    NSUInteger others=0;NSDictionary *players=[info[@"players"] isKindOfClass:NSDictionary.class]?info[@"players"]:@{};
    for(NSString *k in players)if(players[k]!=mine)others++;
    if(others)[parts addObject:others==1?@"1 friend's company":[NSString stringWithFormat:@"%lu friends' companies",(unsigned long)others]];
    return [parts componentsJoinedByString:@" · "];
}

// "Today, 09:12", "Yesterday, 21:40", "Oct 28", "Oct 28, 2025"; "" for a world never played.
static inline NSString *DMWorldWhen(NSDate *date,NSDate *now) {
    if(!date||[date isEqualToDate:[NSDate distantPast]])return @"";
    NSCalendar *cal=NSCalendar.currentCalendar;NSDateFormatter *f=[NSDateFormatter new];f.locale=[NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
    f.dateFormat=@"HH:mm";NSString *time=[f stringFromDate:date];
    if([cal isDate:date inSameDayAsDate:now])return [@"Today, " stringByAppendingString:time];
    if([cal isDate:date inSameDayAsDate:[now dateByAddingTimeInterval:-86400]])return [@"Yesterday, " stringByAppendingString:time];
    f.dateFormat=[cal component:NSCalendarUnitYear fromDate:date]==[cal component:NSCalendarUnitYear fromDate:now]?@"MMM d":@"MMM d, yyyy";
    return [f stringFromDate:date];
}

// A new world's folder: "worlds/yyyyMMdd-HHmmss", with -2, -3... if that one is taken. Never from typed text.
static inline NSString *DMNewWorldFolder(NSString *data,NSDate *now) {
    NSDateFormatter *f=[NSDateFormatter new];f.locale=[NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];f.dateFormat=@"yyyyMMdd-HHmmss";
    NSString *base=[@"worlds/" stringByAppendingString:[f stringFromDate:now]],*folder=base;
    for(int i=2;[[NSFileManager defaultManager] fileExistsAtPath:[data stringByAppendingPathComponent:folder]];i++)folder=[NSString stringWithFormat:@"%@-%d",base,i];
    return folder;
}
// Makes the world: its folder and botd-world.json (launch.zsh adds the game files on its first start). nil on failure.
static inline NSDictionary *DMCreateWorld(NSString *data,NSString *label,NSDate *now) {
    NSString *folder=DMNewWorldFolder(data,now),*path=[data stringByAppendingPathComponent:folder];
    if(![[NSFileManager defaultManager] createDirectoryAtPath:path withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil])return nil;
    if(!DMWorldWriteJSON([path stringByAppendingPathComponent:DMWorldMetaFile],@{@"version":@1,@"label":label?:@"",@"created":DMWorldStamp(now),@"seed":NSNull.null}))return nil;
    return DMWorldEntry(data,folder);
}
// Changes one field of a world's botd-world.json (made if missing: the first world's, on its first rename or play).
static inline BOOL DMWorldSetMeta(NSDictionary *world,NSString *key,id value) {
    NSString *file=[world[@"path"] stringByAppendingPathComponent:DMWorldMetaFile];
    NSMutableDictionary *meta=[DMWorldReadJSON(file) mutableCopy]?:[@{@"version":@1,@"seed":NSNull.null} mutableCopy];
    meta[key]=value;
    return DMWorldWriteJSON(file,meta);
}

// The game is running on this data folder (launch.zsh's lock with a live pid): a world must not be deleted then.
static inline BOOL DMGameRunning(NSString *data) {
    NSString *pid=DMWorldText([NSString stringWithContentsOfFile:[data stringByAppendingPathComponent:@"launcher.lock/pid"] encoding:NSUTF8StringEncoding error:nil]);
    return pid.intValue>0&&kill(pid.intValue,0)==0;
}
// Only a world's own folder may go to the Trash: a known folder name, a real folder (not a link), inside the data folder.
static inline BOOL DMWorldTrashable(NSString *data,NSDictionary *world) {
    NSString *folder=world[@"folder"];if(!DMWorldFolderOK(folder))return NO;
    NSString *path=[data stringByAppendingPathComponent:folder];
    NSDictionary *a=[[NSFileManager defaultManager] attributesOfItemAtPath:path error:nil];
    if(![a[NSFileType] isEqualToString:NSFileTypeDirectory])return NO;
    NSString *real=[path stringByResolvingSymlinksInPath],*root=[[data stringByResolvingSymlinksInPath] stringByAppendingString:@"/"];
    return [real hasPrefix:root]&&[[real substringFromIndex:root.length] isEqualToString:folder];
}
// The size of a world's own saves (what Move to Trash takes away; the game files are clones of the app's).
static inline unsigned long long DMWorldSavesSize(NSDictionary *world) {
    unsigned long long total=0;NSFileManager *fm=[NSFileManager defaultManager];
    for(NSString *sub in @[@"units",@"players"]){NSString *dir=[world[@"path"] stringByAppendingPathComponent:sub];
        for(NSString *f in [fm enumeratorAtPath:dir])total+=[[fm attributesOfItemAtPath:[dir stringByAppendingPathComponent:f] error:nil] fileSize];}
    return total;
}
