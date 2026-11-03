"""Blender: build a separate sprite-proportioned Orc, real armature and move clips.

blender --background --factory-startup --python build_orc_3d.py -- [--preview]
"""
from pathlib import Path
import math
import sys
import json
import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'Dungeon Master Sample/GOA Orc Base Animation Sprites/orc-3d-prototype-v1'
OUT.mkdir(exist_ok=True)
(OUT/'renders').mkdir(exist_ok=True)
PREVIEW = '--preview' in sys.argv
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, rgb):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1)
    m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=1
    return m

skin=material('Orc green',(0.31,0.48,0.15))
inner=material('Ear shadow',(0.16,0.26,0.07))
ink=material('Ink',(0.012,0.018,0.008))
shorts=material('Black shorts',(0.045,0.048,0.042))
eye=material('Red eyes',(0.92,0.004,0.002))
ivory=material('Small tusks',(0.85,0.87,0.70))

arm=bpy.data.armatures.new('Orc anatomy')
rig=bpy.data.objects.new('Orc_Rig',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
rests={}
def bone(name,head,tail,parent=None):
    b=arm.edit_bones.new(name);b.head=head;b.tail=tail
    if parent:b.parent=arm.edit_bones[parent]
    rests[name]=(Vector(head),Vector(tail))

bone('root',(0,0,0),(0,0,.2))
bone('pelvis',(0,0,.43),(0,0,.66),'root')
bone('chest',(0,0,.66),(0,0,1.25),'pelvis')
bone('head',(0,0,1.25),(0,0,1.98),'chest')
for side,s in [('R',-1),('L',1)]:
    sh=(s*.51,0,1.24);el=(s*.68,-.025,.94);wr=(s*.68,-.10,.61)
    bone('upper_arm.'+side,sh,el,'chest');bone('forearm.'+side,el,wr,'upper_arm.'+side)
    bone('hand.'+side,wr,(s*.68,-.16,.48),'forearm.'+side)
    hip=(s*.22,0,.43);knee=(s*.25,-.025,.27);ankle=(s*.27,-.035,.12)
    bone('thigh.'+side,hip,knee,'pelvis');bone('shin.'+side,knee,ankle,'thigh.'+side)
    bone('foot.'+side,ankle,(s*.27,-.25,.10),'shin.'+side)
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front=True
meshes=[]

def bind(obj,name,mat,bone_name):
    obj.name=name;obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for face in obj.data.polygons:face.use_smooth=False
    group=obj.vertex_groups.new(name=bone_name);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Orc skeleton','ARMATURE');mod.object=rig
    obj.parent=rig;meshes.append(obj);return obj

def ball(name,loc,scale,mat,bone_name,segments=12,rings=6):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=loc)
    obj=bpy.context.object;obj.scale=scale
    return bind(obj,name,mat,bone_name)

def box(name,loc,scale,mat,bone_name):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object;obj.scale=scale
    bevel=obj.modifiers.new('Small hard corners','BEVEL');bevel.width=.035;bevel.segments=1
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=bevel.name)
    return bind(obj,name,mat,bone_name)

def mesh(name,verts,faces,mat,bone_name):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    return bind(obj,name,mat,bone_name)

def ring_body(name,rings,mat,bone_name):
    verts=[]
    # Beveled rectangular cross-section, front is -Y.
    section=[(-.7,-1),(.7,-1),(1,-.65),(1,.65),(.7,1),(-.7,1),(-1,.65),(-1,-.65)]
    for z,w,d,cy in rings:verts += [(x*w,y*d+cy,z) for x,y in section]
    faces=[tuple(reversed(range(8)))]
    for r in range(len(rings)-1):
        for j in range(8):faces.append((r*8+j,r*8+(j+1)%8,(r+1)*8+(j+1)%8,(r+1)*8+j))
    faces.append(tuple((len(rings)-1)*8+j for j in range(8)))
    return mesh(name,verts,faces,mat,bone_name)

def limb(name,bone_name,radius,mat):
    a,b=rests[bone_name];delta=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=10,radius1=radius*.90,radius2=radius,depth=delta.length,location=(a+b)/2)
    obj=bpy.context.object;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=delta.to_track_quat('Z','Y')
    return bind(obj,name,mat,bone_name)

ring_body('Broad torso',[(.58,.30,.20,0),(.79,.40,.24,-.015),(1.14,.46,.25,0),(1.30,.33,.21,0)],skin,'chest')
ring_body('Large angular head',[(1.25,.28,.25,-.07),(1.43,.46,.34,-.06),(1.88,.53,.36,-.04),(2.10,.39,.28,-.025),(2.15,.28,.22,0)],skin,'head')
ring_body('Black shorts waist',[(.36,.35,.22,0),(.62,.37,.24,0),(.66,.34,.22,0)],shorts,'pelvis')
for side,s in [('R',-1),('L',1)]:
    # Short shorts legs and broad feet, no human-length calves.
    box('Shorts leg '+side,(s*.21,0,.38),(.34,.43,.21),shorts,'thigh.'+side)
    limb('Thigh '+side,'thigh.'+side,.155,skin)
    limb('Shin '+side,'shin.'+side,.145,skin)
    box('Broad bare foot '+side,(s*.27,-.12,.09),(.32,.43,.18),skin,'foot.'+side)
    ball('Shoulder '+side,rests['upper_arm.'+side][0],(.23,.22,.22),skin,'upper_arm.'+side)
    limb('Upper arm '+side,'upper_arm.'+side,.18,skin)
    ball('Elbow '+side,rests['forearm.'+side][0],(.18,.18,.18),skin,'forearm.'+side)
    limb('Thick forearm '+side,'forearm.'+side,.20,skin)
    ball('Fist '+side,rests['hand.'+side][0],(.215,.22,.21),skin,'hand.'+side)
    # Wedge ears are part of the head skin, with a flat inset on the front face.
    v=[(s*.43,-.10,1.67),(s*.84,-.015,1.96),(s*.53,.08,1.54),
       (s*.43,.12,1.67),(s*.80,.10,1.96),(s*.53,.19,1.54)]
    mesh('Pointed ear '+side,v,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],skin,'head')
    mesh('Ear inset '+side,[(s*.50,-.105,1.69),(s*.73,-.025,1.89),(s*.55,.055,1.63)],[(0,1,2)],inner,'head')
    box('Eye socket '+side,(s*.23,-.398,1.68),(.17,.065,.22),ink,'head')
    box('Red eye '+side,(s*.23,-.438,1.66),(.115,.025,.15),eye,'head')
    bpy.ops.mesh.primitive_cone_add(vertices=5,radius1=.044,radius2=.012,depth=.12,location=(s*.17,-.386,1.34))
    bind(bpy.context.object,'Small tusk '+side,ivory,'head')

rig['anatomical_right']='negative X in south/front bind pose'
rig['source_reference']='Approved curated Orc; large head, short legs, green skin, red eyes, black shorts'
rig['prototype']=True

def two_bone(a,target,l1,l2,hint):
    direction=target-a;d=min(max(direction.length,.015),l1+l2-.001)
    u=direction.normalized();target=a+u*d
    along=(l1*l1-l2*l2+d*d)/(2*d)
    height=math.sqrt(max(0,l1*l1-along*along))
    bend=hint-a; bend-=u*bend.dot(u)
    if bend.length<.001:bend=Vector((0,-1,0));bend-=u*bend.dot(u)
    return a+u*along+bend.normalized()*height,target

def set_segment(name,head,tail):
    # Same bone length; target positions are solved with fixed limb lengths.
    direction=tail-head
    rig.pose.bones[name].matrix=Matrix.Translation(head)@direction.to_track_quat('Y','Z').to_matrix().to_4x4()
    bpy.context.view_layer.update()

def pose(action,index):
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    bob=0;lean=0;shift=0
    wrists={'R':Vector((-.48,-.43,1.08)),'L':Vector((.48,-.38,1.13))}
    if action=='overhead_cast':
        if index==1:wrists={s:Vector((k*.58,-.10,1.88)) for s,k in [('R',-1),('L',1)]};bob=.045
        if index==2:wrists={s:Vector((k*.28,-.66,1.40)) for s,k in [('R',-1),('L',1)]};lean=12
        if index==3:wrists={s:Vector((k*.38,-.49,1.20)) for s,k in [('R',-1),('L',1)]}
    elif action=='ground_slam':
        if index==1:wrists={s:Vector((k*.55,-.10,1.9)) for s,k in [('R',-1),('L',1)]};bob=.03
        if index==2:bob=-.15;lean=45;wrists={s:Vector((k*.28,-.67,.25)) for s,k in [('R',-1),('L',1)]}
        if index==3:bob=-.08;lean=20;wrists={s:Vector((k*.38,-.50,.75)) for s,k in [('R',-1),('L',1)]}
    elif action=='dash_strike':
        if index==1:lean=18;bob=-.05;wrists['R']=Vector((-.55,.20,1.01));wrists['L']=Vector((.43,-.43,1.08))
        if index==2:lean=28;shift=-.13;wrists['R']=Vector((-.36,-.81,1.12));wrists['L']=Vector((.65,.20,.95))
        if index==3:lean=10;wrists['R']=Vector((-.43,-.56,1.08))
    elif action=='stagger':
        if index==1:lean=-20;wrists={s:Vector((k*.70,-.06,1.14)) for s,k in [('R',-1),('L',1)]}
        if index==2:lean=-12;bob=-.08;wrists={s:Vector((k*.58,-.20,.91)) for s,k in [('R',-1),('L',1)]}
    t=Matrix.Translation((0,shift,bob))
    pivot=Vector((0,0,.66))
    upper=t@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(lean),4,'X')@Matrix.Translation(-pivot)
    rig.pose.bones['root'].matrix=t@arm.bones['root'].matrix_local
    rig.pose.bones['pelvis'].matrix=t@arm.bones['pelvis'].matrix_local
    rig.pose.bones['chest'].matrix=upper@arm.bones['chest'].matrix_local
    rig.pose.bones['head'].matrix=upper@arm.bones['head'].matrix_local
    bpy.context.view_layer.update()
    for side,s in [('R',-1),('L',1)]:
        sh=upper@rests['upper_arm.'+side][0]
        target=wrists[side]+Vector((0,shift,bob))
        l1=(rests['upper_arm.'+side][1]-rests['upper_arm.'+side][0]).length
        l2=(rests['forearm.'+side][1]-rests['forearm.'+side][0]).length
        elbow,wrist=two_bone(sh,target,l1,l2,sh+Vector((s*.6,.05,-.4)))
        set_segment('upper_arm.'+side,sh,elbow);set_segment('forearm.'+side,elbow,wrist)
        set_segment('hand.'+side,wrist,wrist+(wrist-elbow).normalized()*.14)
        hip=t@rests['thigh.'+side][0];ankle=rests['foot.'+side][0]+Vector((0,shift,0))
        l1=(rests['thigh.'+side][1]-rests['thigh.'+side][0]).length
        l2=(rests['shin.'+side][1]-rests['shin.'+side][0]).length
        knee,ankle=two_bone(hip,ankle,l1,l2,hip+Vector((s*.15,-.5,0)))
        set_segment('thigh.'+side,hip,knee);set_segment('shin.'+side,knee,ankle)
        set_segment('foot.'+side,ankle,ankle+Vector((0,-.215,-.02)))

actions={}
rig.animation_data_create()
for p in rig.pose.bones:p.rotation_mode='QUATERNION'
for name in ['guard','overhead_cast','ground_slam','dash_strike','stagger']:
    rig.animation_data.action=None
    for i,frame in enumerate([1,7,13,21]):
        pose(name,i)
        for p in rig.pose.bones:
            p.rotation_mode='QUATERNION'
            p.keyframe_insert(data_path='location',frame=frame,group=p.name)
            p.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=p.name)
            p.keyframe_insert(data_path='scale',frame=frame,group=p.name)
    action=rig.animation_data.action;action.name=name;action.use_fake_user=True;actions[name]=action

scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=scene.render.resolution_y=256;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.fps=24
scene.world.color=(.4,.4,.4)
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.65,.7,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
ld=bpy.data.lights.new('Fixed key','AREA');light=bpy.data.objects.new('Fixed key',ld);bpy.context.collection.objects.link(light)
light.location=(-3,-4,6);ld.energy=400;ld.size=4
light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Sprite orthographic camera');cam=bpy.data.objects.new('Sprite orthographic camera',camdata)
bpy.context.collection.objects.link(cam);scene.camera=cam
cam.location=(0,-8,3.3);target=Vector((0,0,1.12));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO';camdata.ortho_scale=3.45
scene.camera.data.lens=50
scene.frame_start=1;scene.frame_end=21
rig.animation_data.action=actions['guard'];scene.frame_set(1)
rig.rotation_euler=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'orc-sprite-rig.blend'))
# Export a real skinned asset with separately named clips, excluding camera/light.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for obj in meshes:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
props=bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
options={'filepath':str(OUT/'orc-sprite-rig.glb'),'export_format':'GLB','use_selection':True,
         'export_animations':True,'export_skins':True,'export_force_sampling':True,
         'export_animation_mode':'ACTIONS','export_all_armature_actions':True}
bpy.ops.export_scene.gltf(**{k:v for k,v in options.items() if k in props})
renders=[]
directions=[('south',0),('north',180),('east',90),('west',-90)]
for name in (['guard'] if PREVIEW else actions):
    rig.animation_data.action=actions[name]
    for index,frame in enumerate([1] if name=='guard' else [1,7,13,21]):
        scene.frame_set(frame)
        for direction,angle in directions:
            rig.rotation_euler.z=math.radians(angle);bpy.context.view_layer.update()
            filename=f'{name}-{direction}-{index}.png';scene.render.filepath=str(OUT/'renders'/filename)
            bpy.ops.render.render(write_still=True)
            renders.append({'action':name,'direction':direction,'phase':index,'file':'renders/'+filename})
if not PREVIEW:
    rig.animation_data.action=actions['guard'];scene.frame_set(1)
    scene.render.resolution_x=scene.render.resolution_y=384
    for i in range(12):
        rig.rotation_euler.z=math.radians(i*30);bpy.context.view_layer.update()
        scene.render.filepath=str(OUT/'renders'/f'turntable-{i:02}.png');bpy.ops.render.render(write_still=True)
rig.rotation_euler.z=0;rig.animation_data.action=actions['guard'];scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'orc-sprite-rig.blend'))
(OUT/'model-manifest.json').write_text(json.dumps({'status':'prototype_for_visual_review','boneCount':len(arm.bones),
    'meshCount':len(meshes),'actions':list(actions),'keyframes':[1,7,13,21], 'directions':[d for d,a in directions],
    'model':'orc-sprite-rig.blend','exchange':'orc-sprite-rig.glb','renders':renders,
    'notes':'True 3D geometry with weighted armature. Fixed-length limb targets; separate from approved 2D sprites.'},indent=2)+'\n')
print('ORC_3D_COMPLETE',OUT)
