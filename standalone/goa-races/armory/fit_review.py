"""Produce a visual equipment-fitting review using the real local renderer.

Each design is shown alone on Human, Dwarf and Kobold in front and side views.
This is a contact-sheet review aid, not a production-fit certification.
"""
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8877/index.html')
    args=parser.parse_args()
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1500,height=1100))
            errors=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            await page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(('http://127.0.0.1:8877/','data:','file:')) else route.abort())
            await page.goto(args.url)
            await page.wait_for_function('window.Armory?.ready===true')
            sheets=await page.evaluate('''()=>{
              const A=Armory,E=EquipmentEngine,items=A.catalog.items;
              const profiles=[['human',0,'Human · S'],['human',90,'Human · E'],['dwarf',0,'Dwarf · S'],['dwarf',90,'Dwarf · E'],['kobold',0,'Kobold · S'],['kobold',90,'Kobold · E']];
              const results=[];
              for(const [group,subset] of [['weapons',items.filter(i=>i.slot==='weapon')],['armor',items.filter(i=>i.slot!=='weapon')]]){
                for(let start=0;start<subset.length;start+=8){
                  const selected=subset.slice(start,start+8),out=E.canvas(1192,50+selected.length*214),c=out.getContext('2d');
                  c.fillStyle='#10191c';c.fillRect(0,0,out.width,out.height);c.fillStyle='#ead9ac';c.font='13px system-ui';
                  profiles.forEach((p,col)=>c.fillText(p[2],190+col*166+40,29));
                  selected.forEach((item,row)=>{
                    const y=50+row*214;c.fillStyle=row%2?'#19252a':'#132026';c.fillRect(0,y,out.width,214);
                    c.fillStyle='#e9dcbf';c.font='13px system-ui';c.fillText(item.id,12,y+38);c.fillStyle='#aebdb8';c.font='12px system-ui';
                    const material=item.materials.includes('iron')?'iron':item.materials[0];c.fillText(material,12,y+59);c.fillText(item.slot,12,y+80);
                    for(const [col,profile] of profiles.entries()){
                      const state={bodyId:profile[0],angle:profile[1],frame:0,motion:'idle',fits:{},loadout:Object.fromEntries(E.SLOTS.map(s=>[s,{id:'',material:''}]))};
                      state.loadout[item.slot]={id:item.id,material};
                      const x=190+col*166+83;c.save();c.translate(x-32*2.5,y+186-61*2.5);c.scale(2.5,2.5);A.engine.render(c,state,{angle:profile[1],frame:0,pose:0});c.restore();
                    }
                  });
                  results.push({file:'fit-contact-'+group+'-'+(Math.floor(start/8)+1)+'.png',items:selected.map(i=>i.id),png:out.toDataURL()});
                }
              }
              return results;
            }''')
            manifest=[]
            for sheet in sheets:
                (HERE/sheet['file']).write_bytes(base64.b64decode(sheet['png'].split(',',1)[1]))
                manifest.append({k:v for k,v in sheet.items() if k!='png'})
            assert not errors,errors
            report=dict(rendererSha256=hashlib.sha256((HERE/'equipment.js').read_bytes()).hexdigest(),
                        sampledBodies=['human','dwarf','kobold'],sampledAngles=[0,90],frame=0,
                        isolatedDesigns=sum(len(s['items']) for s in manifest),sheets=manifest,browserErrors=errors,
                        limitation='Visual contact-sheet coverage only; not a fitted-animation or material-variant approval.')
            (HERE/'fit-review-manifest.json').write_text(json.dumps(report,indent=2))
            print(json.dumps({k:v for k,v in report.items() if k!='sheets'}))
        finally:
            await browser.close()


if __name__=='__main__':
    asyncio.run(main())
