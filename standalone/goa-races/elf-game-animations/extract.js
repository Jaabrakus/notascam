// Snapshot definitions from the scripts actually included in the installed game.
const fs=require('fs'),vm=require('vm'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'../../..'),game=path.join(root,'standalone/remastered'),runtime=fs.readFileSync(path.join(game,'game/Interface/gear3d.js'),'utf8');
const installed=fs.readFileSync(path.join(game,'Banners of the Deep.app/Contents/Resources/game/world/Interface/gear3d.js'),'utf8');
if(runtime!==installed)throw Error('Installed app and working runtime differ; select reference explicitly');
const context=vm.createContext({}),hashes={};
for(const name of ['skills.js','deaths.js','work.js','game.js','ragdoll.js']){
 const rel='standalone/remastered/art/gear3d/'+name,code=fs.readFileSync(path.join(root,rel),'utf8');
 if(!runtime.includes(code))throw Error('Runtime does not contain current '+name);
 hashes[rel]=crypto.createHash('sha256').update(code).digest('hex');
 if(['skills.js','deaths.js','work.js'].includes(name))vm.runInContext(code,context,{timeout:2000});
}
for(const rel of ['standalone/remastered/game/Interface/gear3d.js','standalone/remastered/game/Interface/remastered.html','standalone/remastered/game/Code/Remastered/Gear3D.dm','standalone/remastered/game/Code/Remastered/View3D.dm'])hashes[rel]=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,rel))).digest('hex');
const source=vm.runInContext('({defs:SK.defs,causes:DZDEF,weapons:SKWEAPON})',context);
const flags=fs.readFileSync(path.join(game,'game/Code/Remastered/Gear3D.dm'),'utf8');
source.flags=Object.fromEntries([...flags.matchAll(/var\/(rm_g3_\w+)\s*=\s*(\d+)/g)].map(m=>[m[1],Number(m[2])]));
const compiled=JSON.parse(fs.readFileSync(path.join(game,'Banners of the Deep.app/Contents/Resources/game/world/Cave Crawlers.json'),'utf8')).Globals;
source.installedFlags={};
for(const [name,value] of Object.entries(source.flags)){
 const index=compiled.Names.indexOf(name),actual=compiled.Globals[index];
 if(actual!==value)throw Error('Installed game flag differs: '+name);
 source.installedFlags[name]=actual;
}
source.hashes=hashes;source.installedRuntimeMatches=true;
fs.writeFileSync(path.join(__dirname,'runtime-source.json'),JSON.stringify(source,null,2));
console.log(JSON.stringify({keyedDefinitions:Object.keys(source.defs).length,deathSequences:Object.keys(source.causes).length,flags:source.flags,installedRuntimeMatches:true}));
