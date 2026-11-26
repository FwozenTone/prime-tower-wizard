"""Explicit test inputs for older geometry regressions, not production defaults."""
from pathlib import Path
import isolated_prime_tower as ipt

def generate_fixture(project,output,*args,**kwargs):
    reference=kwargs.get('reference_gcode')
    if reference:
        layers=ipt.reference_layers(reference,set(range(len(project.settings['filament_type']))))
        order=sorted({t+1 for tools in layers.values() for t in tools})
    else:
        order,_=project.used_filaments(kwargs.get('filaments'))
        first=float(project.settings.get('initial_layer_print_height',.2));step=float(project.settings.get('layer_height',.2));height=project.reference_bounds[5]
        z=first;lines=['G90','M83','G0 X100 Y100']
        while z<=height+1e-5:
            lines.append(f';Z:{z:.5f}')
            for slot in order:lines.extend([f'T{slot-1}',';TYPE:Outer wall','G0 X100 Y100','G1 X110 E1'])
            z=round(z+step,5)
        reference=Path(output).with_suffix('.reference.gcode');reference.write_text('\n'.join(lines))
        kwargs['reference_gcode']=reference
    if not kwargs.get('frame_slot'):
        kwargs['frame_slot']=ipt.choose_frame(order,{slot:ipt.material_key(project.settings['filament_type'][slot-1]) for slot in order})
    return project.generate(output,*args,**kwargs)
