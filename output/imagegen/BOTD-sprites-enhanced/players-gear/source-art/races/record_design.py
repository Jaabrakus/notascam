"""Record an explicitly reviewed AI design and proportional native-height export."""
import sys,json,shutil
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(BASE/'_tools'))
from export_sprite_height import export_height
race,generated=sys.argv[1:3]
cell=int(sys.argv[3]) if len(sys.argv)>3 else 0
source=Path(generated); im=Image.open(source).convert('RGBA');alpha=im.getchannel('A')
# Crop coordinates must be supplied after review. No alpha threshold retouch.
crop=tuple(map(int,sys.argv[4].split(','))) if len(sys.argv)>4 else None
raw=BASE/'players-gear/source-art/races'/race/'standing-front-original.png';raw.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,raw)
out=BASE/'players-gear/ai-designs/races'/race/'standing-front.png'
report=export_height(raw,out,native_source=Path.cwd()/'standalone/remastered/game/Icons/Remastered/Races64'/(race+'.dmi'),cell_index=cell,source_crop=crop)
r=json.load(open(report));m=BASE/'_meta/players-races-ai-batch.json';batch=json.load(open(m));batch['assets'][race]={'status':'complete_base_design','original':str(raw),'output':str(out),'export_report':str(report),'prompt':str(BASE/'_meta/prompts/players-races'/(race+'.txt')),'visible_height':r['placement']['actual_visible_height'],'canvas_size':r['placement']['canvas_size'],'native_cell_index':cell,'native_state':r['native_reference']['state_name'],'discarded_maximum_alpha':r['source']['discarded_maximum_alpha'],'quality':'Reviewed generated front-standing base design; intact limbs and native race colors. Concept design, not complete animation atlas.'};m.write_text(json.dumps(batch,indent=2)+'\n');print(json.dumps(batch['assets'][race]))
