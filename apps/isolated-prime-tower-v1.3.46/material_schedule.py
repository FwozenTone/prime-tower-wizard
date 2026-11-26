"""Plate-specific material areas and per-layer ownership, independent of meshes."""
def plan_areas(layers,materials,frame_slot,height):
    groups={}
    for slot,kind in sorted(materials.items()):groups.setdefault(kind,[]).append(slot-1)
    frame_type=materials[frame_slot]
    areas=[]
    for kind,tools in sorted(groups.items(),key=lambda item:(item[0]==frame_type,item[0])):
        peak=max(len(set(used)&set(tools)) for used in layers.values())
        count=max(peak,2 if len(groups)==1 else 1)
        for index in range(count):
            areas.append({'material':kind,'tool':tools[index%len(tools)],'tools':tools,'height':0.})
    # All lanes span the box width. Prefer the lanes nearest its two end walls
    # along the stacking axis; ties retain the lower index deterministically.
    priorities={kind:sorted((i for i,a in enumerate(areas) if a['material']==kind),
                           key=lambda i:(min(i,len(areas)-1-i),i)) for kind in groups}
    remaining={kind:0 for kind in groups};demands={}
    for z,used in sorted(layers.items(),reverse=True):
        for kind,tools in groups.items():
            remaining[kind]=max(remaining[kind],len(set(used)&set(tools)))
        demands[z]=dict(remaining)
    first=min(layers)
    for z in sorted(layers):
        if z>height+1e-5:break
        for kind,indices in priorities.items():
            count=max(demands[z][kind],1 if kind==frame_type else 0)
            if z==first:count=len(indices) # Preserve the full initial footprint.
            for i in indices[:count]:areas[i]['height']=z
    previous=[a['tool'] for a in areas];schedule=[];lo=0.
    for z,used in sorted(layers.items()):
        if z>height+1e-5:break
        if z<=lo:raise ValueError('Invalid reference layer heights.')
        owners=[None]*len(areas)
        for kind,tools in groups.items():
            indices=[i for i,a in enumerate(areas) if a['material']==kind and z<=a['height']+1e-5]
            if not indices:continue
            active=[t for t in used if t in tools]
            remaining=list(dict.fromkeys(active))
            for i in indices:
                if previous[i] in remaining:owners[i]=previous[i];remaining.remove(previous[i])
            for tool in remaining:
                i=next(i for i in indices if owners[i] is None);owners[i]=tool
            donor=active[0] if active else previous[indices[0]]
            for i in indices:
                if owners[i] is None:owners[i]=donor
                previous[i]=owners[i]
        schedule.append({'z':z,'min_z':lo,'max_z':z,'tools':owners,'reference_tools':used})
        lo=z
    return areas,schedule
