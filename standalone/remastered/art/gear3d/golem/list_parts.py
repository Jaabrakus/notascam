# List the golem's stones: name, collection, vertex count, world bounds, material (run inside Blender, background).
import bpy, json, sys
out = sys.argv[sys.argv.index('--') + 1]
rows = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    cols = [c.name for c in o.users_collection]
    bb = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
    mn = [round(min(v[i] for v in bb), 3) for i in range(3)]; mx = [round(max(v[i] for v in bb), 3) for i in range(3)]
    mats = [m.name for m in o.data.materials if m]
    rows.append(dict(name=o.name, parent=o.parent.name if o.parent else None, cols=cols, verts=len(o.data.vertices), faces=len(o.data.polygons), mods=[m.type for m in o.modifiers], min=mn, max=mx, mats=mats))
json.dump(rows, open(out, 'w'), indent=1)
print('parts', len(rows))
