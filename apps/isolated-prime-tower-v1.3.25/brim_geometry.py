"""Create an outer-only, first-layer brim without changing slicer tool selection."""
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
