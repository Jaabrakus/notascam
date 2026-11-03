// Read the real game definitions without launching or modifying the game.
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'../../remastered/art/gear3d'),context=vm.createContext({});
for(const name of ['skills.js','work.js','deaths.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context,{timeout:2000});
const source=vm.runInContext('({defs:SK.defs,causes:DZDEF,weapons:SKWEAPON})',context);
fs.writeFileSync(path.join(__dirname,'source-clips.json'),JSON.stringify(source,null,2));
