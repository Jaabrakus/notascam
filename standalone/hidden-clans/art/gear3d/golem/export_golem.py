# The stone golem for the page (bosses.js): every stone of collections 01-04, ambient occlusion baked into its vertex
# colours (Cycles: the carved spirals and cracks stay dark under the game's light), decimated to a game size, then
# triangles with corner normals and colours, in Blender units (cm), Blender axes (z up, -y the front).
# blender --background --factory-startup --disable-autoexec stone_golem.blend --python export_golem.py -- OUT RATIO
import bpy, json, sys, base64, struct
args = sys.argv[sys.argv.index('--') + 1:]
out, ratio = args[0], float(args[1]) if len(args) > 1 else 0.1
parts = [o for o in bpy.data.objects if o.type == 'MESH' and any(c.name[:2] in ('01', '02', '03', '04') for c in o.users_collection)]
for o in bpy.data.objects:
    if o not in parts: o.hide_render = True
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
try: sc.render.bake.target = 'VERTEX_COLORS'
except Exception as e: print('bake target', e)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    me = o.data
    a = me.color_attributes.get('AO') or me.color_attributes.new('AO', 'FLOAT_COLOR', 'POINT')
    me.color_attributes.active_color = a
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
print('baked AO on', len(parts))
for o in parts:
    m = o.modifiers.new('game', 'DECIMATE'); m.ratio = ratio
dg = bpy.context.evaluated_depsgraph_get()
rows = []; tris = 0
for o in parts:
    ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
    W = o.matrix_world; N3 = W.to_3x3().inverted().transposed()
    ao = me.color_attributes.get('AO'); cn = me.corner_normals
    pos = []; nrm = []; col = []
    for t in me.loop_triangles:
        for li in t.loops:
            v = me.loops[li].vertex_index; p = W @ me.vertices[v].co; n = (N3 @ cn[li].vector).normalized()
            c = ao.data[v].color if ao and ao.domain == 'POINT' else (ao.data[li].color if ao else (1, 1, 1, 1))
            pos += [p.x, p.y, p.z]; nrm += [n.x, n.y, n.z]; col.append(max(0.0, min(1.0, c[0])))
    tris += len(me.loop_triangles); ev.to_mesh_clear()
    q = lambda xs, k, f: base64.b64encode(struct.pack('<%d%s' % (len(xs), f), *[int(round(x * k)) for x in xs])).decode()
    rows.append(dict(name=o.name, col=[c.name for c in o.users_collection][0], n=len(col), pos=q(pos, 1000, 'h'), nrm=q(nrm, 127, 'b'), ao=q(col, 255, 'B')))
json.dump(dict(units='cm, z up, -y front', parts=rows), open(out, 'w'), separators=(',', ':'))
print('parts', len(rows), 'triangles', tris)
