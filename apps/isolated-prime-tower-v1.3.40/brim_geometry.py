"""Create an outer-only brim and triangular base reinforcement without changing slicer tool selection."""
import importlib
import os
from pathlib import Path
import platform
import subprocess
import sys


def geometry_library():
    cache=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.cache'))/'PrimeTowerWizard'/('geometry-'+sys.implementation.cache_tag+'-'+platform.system()+'-'+platform.machine())
    if str(cache) not in sys.path:sys.path.insert(0,str(cache))
    try:return importlib.import_module('shapely')
    except ImportError:
        cache.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--only-binary=:all:','--target',str(cache),'shapely==2.1.2'],capture_output=True,text=True,timeout=300)
        if result.returncode:
            raise RuntimeError('Could not prepare the brim geometry library. Check your internet connection and that Python includes pip, then retry.')
        importlib.invalidate_caches()
        return importlib.import_module('shapely')


def make_brim(frame,width,height):
    """Union the frame footprint, fill enclosed holes, and offset only its exterior.

    The brim overlaps the frame by 0.02 mm so the slicer unions them reliably;
    it never enters material lanes or the hollow interiors of the outer ribs.
    """
    if width<=0:return []
    geometry_library()
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely import constrained_delaunay_triangles,set_precision
    from shapely.geometry.polygon import orient
    bottoms=[Polygon([(x,y) for x,y,z in triangle]) for triangle in frame if all(abs(v[2])<1e-8 for v in triangle)]
    footprint=unary_union([p for p in bottoms if p.area>1e-10])
    components=list(footprint.geoms) if footprint.geom_type=='MultiPolygon' else [footprint]
    filled=unary_union([Polygon(p.exterior) for p in components])
    brim=filled.buffer(width,quad_segs=128).difference(filled).union(footprint.intersection(filled.boundary.buffer(.02)))
    brim=set_precision(brim,0.00001)
    triangles=[]
    polygons=list(brim.geoms) if brim.geom_type=='MultiPolygon' else [brim]
    for polygon in polygons:
        polygon=orient(polygon,sign=1.0)
        for t in constrained_delaunay_triangles(polygon).geoms:
            points=list(orient(t,sign=1.0).exterior.coords)[:3]
            triangles.append(tuple((x,y,height) for x,y in points))
            triangles.append(tuple((x,y,0.) for x,y in reversed(points)))
        for boundary in [polygon.exterior,*polygon.interiors]:
            points=list(boundary.coords)
            for (x,y),(u,v) in zip(points,points[1:]):
                a,b,c,d=(x,y,0.),(u,v,0.),(u,v,height),(x,y,height)
                triangles.extend([(a,b,c),(a,c,d)])
    return triangles


def outer_footprint(frame):
    geometry_library()
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polygons=[Polygon([(x,y) for x,y,z in t]) for t in frame if all(abs(p[2])<1e-8 for p in t)]
    footprint=unary_union([p for p in polygons if p.area>1e-10])
    parts=list(footprint.geoms) if footprint.geom_type=='MultiPolygon' else [footprint]
    return unary_union([Polygon(p.exterior) for p in parts])


def make_gussets(frame,brim_width,brim_height,tower_height,box_width,box_depth):
    """Two 1.2 mm upright triangular fins per side, bonded to frame and brim."""
    if brim_width<=0 or tower_height<=brim_height+.05:return [],[]
    geometry_library()
    from shapely.geometry import box
    from shapely.affinity import affine_transform
    footprint=outer_footprint(frame)
    thickness=1.2;run=brim_width
    rise=min(2.*brim_width,tower_height-brim_height)
    if run<.4 or rise<.05:return [],[]
    triangles=[];details=[]
    # Each transform maps its side to local (along-wall, outward) coordinates.
    sides=[('back',box_width,[1,0,0,1,0,0],lambda u,v:(u,v)),
           ('front',box_width,[1,0,0,-1,0,0],lambda u,v:(u,-v)),
           ('right',box_depth,[0,1,1,0,0,0],lambda u,v:(v,u)),
           ('left',box_depth,[0,1,-1,0,0,0],lambda u,v:(-v,u))]
    for side,span,matrix,world in sides:
        local=affine_transform(footprint,matrix)
        for fraction in (.35,.65):
            center=span*fraction
            # Follow the curved outer connection rather than starting in empty space.
            strip=local.intersection(box(center-thickness/2,local.bounds[1]-1,center+thickness/2,local.bounds[3]+1))
            if strip.is_empty:continue
            start=strip.bounds[3]-.2;end=start+run
            z0=max(0.,brim_height-.02);zt=brim_height+rise
            left=[(*world(center-thickness/2,v),z) for v,z in ((start,z0),(end,z0),(start,zt))]
            right=[(*world(center+thickness/2,v),z) for v,z in ((start,z0),(end,z0),(start,zt))]
            # Orient each closed triangular prism consistently after side reflection.
            ts=[tuple(reversed(left)),tuple(right)]
            for i in range(3):
                j=(i+1)%3;a,b,c,d=left[i],left[j],right[j],right[i]
                ts.extend([(a,b,c),(a,c,d)])
            volume=sum(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]) for a,b,c in ts)/6
            if volume<0:ts=[tuple(reversed(t)) for t in ts]
            triangles.extend(ts)
            details.append({'side':side,'thickness':thickness,'run':run,'height':rise,'top_z':zt})
    return triangles,details


def clear_frame_interior(frame,height,width,depth,wall):
    """Keep frame connections outside filament lanes, preserving wall contact."""
    geometry_library()
    from shapely.geometry import Polygon,box
    from shapely.ops import unary_union
    from shapely import constrained_delaunay_triangles,set_precision
    from shapely.geometry.polygon import orient
    bottoms=[Polygon([(x,y) for x,y,z in t]) for t in frame if all(abs(p[2])<1e-8 for p in t)]
    footprint=unary_union([p for p in bottoms if p.area>1e-10])
    footprint=set_precision(footprint.difference(box(wall,wall,wall+width,wall+depth)),.000001)
    polygons=list(footprint.geoms) if footprint.geom_type=='MultiPolygon' else [footprint]
    triangles=[]
    for polygon in polygons:
        polygon=orient(polygon,sign=1.)
        for t in constrained_delaunay_triangles(polygon).geoms:
            points=list(orient(t,sign=1.).exterior.coords)[:3]
            triangles.append(tuple((x,y,height) for x,y in points))
            triangles.append(tuple((x,y,0.) for x,y in reversed(points)))
        for boundary in [polygon.exterior,*polygon.interiors]:
            points=list(boundary.coords)
            for (x,y),(u,v) in zip(points,points[1:]):
                a,b,c,d=(x,y,0.),(u,v,0.),(u,v,height),(x,y,height)
                triangles.extend([(a,b,c),(a,c,d)])
    return triangles


def braced_loop_mesh(width,depth,height,wall,ribs,rounded,x0,y0):
    """A single watertight loop with filleted, same-material cross-ribs."""
    geometry_library()
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    from shapely import constrained_delaunay_triangles,set_precision
    cell=(depth-2*wall-ribs*wall)/(ribs+1)
    outer=[(x+x0+width/2,y+y0+depth/2) for x,y in rounded(width,depth,2.4)]
    holes=[]
    for i in range(ribs+1):
        cy=y0+wall+cell/2+i*(cell+wall)
        holes.append([(x+x0+width/2,y+cy) for x,y in rounded(width-2*wall,cell,min(1.6,cell/2))])
    polygon=orient(set_precision(Polygon(outer,holes),.000001),sign=1.)
    triangles=[]
    for t in constrained_delaunay_triangles(polygon).geoms:
        points=list(orient(t,sign=1.).exterior.coords)[:3]
        triangles.append(tuple((x,y,height) for x,y in points))
        triangles.append(tuple((x,y,0.) for x,y in reversed(points)))
    for boundary in [polygon.exterior,*polygon.interiors]:
        points=list(boundary.coords)
        for (x,y),(u,v) in zip(points,points[1:]):
            a,b,c,d=(x,y,0.),(u,v,0.),(u,v,height),(x,y,height)
            triangles.extend([(a,b,c),(a,c,d)])
    return triangles
