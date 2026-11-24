#!/usr/bin/env python3
"""Local, browser-based workflow; no Tk or external Python packages required."""
import json, re, os, plistlib, secrets, shutil, subprocess, sys, threading, time, webbrowser, zipfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import isolated_prime_tower as tower

def settings_file():
    if sys.platform=='win32':root=Path(os.environ.get('APPDATA',Path.home()/'AppData/Roaming'))
    elif sys.platform=='darwin':root=Path.home()/'Library/Application Support'
    else:root=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
    return root/'PrimeTowerWizard'/'settings.json'

def default_orca(branch='mainline'):
    if branch=='snapmaker':
        for name in ('snapmaker-orca','Snapmaker_Orca','Snapmaker_Orca.exe'):
            found=shutil.which(name)
            if found:return found
        if sys.platform=='darwin':return '/Applications/Snapmaker Orca.app'
        if sys.platform=='win32':return str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Snapmaker Orca'/'Snapmaker_Orca.exe')
        return ''
    names=('orca-slicer','OrcaSlicer','orca-slicer.exe')
    for name in names:
        found=shutil.which(name)
        if found:return found
    if sys.platform=='darwin':return '/Applications/OrcaSlicer.app'
    if sys.platform=='win32':return str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'OrcaSlicer'/'orca-slicer.exe')
    return ''

def load_settings():
    try:return json.loads(settings_file().read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def resolve_orca(value):
    value=os.path.expandvars(str(value).strip().strip('"'))
    if not value:raise tower.TowerError('Choose the installed Orca application or executable.')
    executable=Path(value).expanduser()
    if executable.suffix.lower()=='.app':
        info=executable/'Contents/Info.plist'
        name='OrcaSlicer'
        if info.is_file():
            with info.open('rb') as stream:name=plistlib.load(stream).get('CFBundleExecutable',name)
        executable=executable/'Contents/MacOS'/name
    elif not executable.is_file():
        found=shutil.which(value)
        if found:executable=Path(found)
    if not executable.is_file():raise tower.TowerError('Orca executable not found: '+str(executable))
    if sys.platform!='win32' and not os.access(executable,os.X_OK):raise tower.TowerError('Orca is not executable. On Linux, enable Execute permission on the binary or AppImage.')
    return executable.resolve()

def slicer_details(value):
    try:executable=resolve_orca(value)
    except tower.TowerError:return {'path':str(value),'installed':False,'version':''}
    version='';identity=str(executable).lower()
    bundle=next((p for p in executable.parents if p.suffix.lower()=='.app'),None)
    if bundle and (bundle/'Contents/Info.plist').is_file():
        with (bundle/'Contents/Info.plist').open('rb') as stream:info=plistlib.load(stream)
        version=info.get('CFBundleShortVersionString','')
        identity+=' '+str(info.get('CFBundleIdentifier','')).lower()
    branch='snapmaker' if 'snapmaker' in identity else ('mainline' if 'orcaslicer' in identity or 'orca-slicer' in identity else None)
    return {'path':str(executable),'installed':True,'version':version,'branch':branch}

def slicer_choices():
    saved=load_settings();locations=dict(saved.get('orca_locations',{}))
    if saved.get('orca'):
        branch=saved.get('slicer_branch') or ('snapmaker' if 'snapmaker' in saved['orca'].lower() else 'mainline')
        locations.setdefault(branch,saved['orca'])
    return {branch:slicer_details(locations.get(branch) or default_orca(branch)) for branch in ('mainline','snapmaker')}

def save_orca(value,branch=None):
    executable=resolve_orca(value);details=slicer_details(value)
    branch=branch or details.get('branch') or 'mainline'
    if branch not in ('mainline','snapmaker'):raise tower.TowerError('Choose Mainline Orca or Snapmaker Orca.')
    if details.get('branch') and details['branch']!=branch:raise tower.TowerError('The chosen application does not match the selected Orca branch. Change the branch or application location.')
    version=re.match(r'(\d+)\.(\d+)\.(\d+)',details['version'])
    if branch=='snapmaker' and version and tuple(map(int,version.groups()))<(2,4,1):raise tower.TowerError('Snapmaker Orca 2.4.1 or later is required.')
    path=settings_file();path.parent.mkdir(parents=True,exist_ok=True)
    data=load_settings();data['orca']=str(executable);data['slicer_branch']=branch
    data.setdefault('orca_locations',{})[branch]=str(executable)
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    return str(executable)

def save_source_folder(source):
    path=settings_file();path.parent.mkdir(parents=True,exist_ok=True)
    data=load_settings();data['source_folder']=str(Path(source).expanduser().resolve().parent)
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')

DEFAULT_ORCA=default_orca()

def plates(path):
    with zipfile.ZipFile(path) as z:
        return tower.plate_inventory(ET.fromstring(z.read(tower.MODEL_SETTINGS)),ET.fromstring(z.read(tower.MODEL)))

def project_materials(path):
    with zipfile.ZipFile(path) as z:settings=json.loads(z.read(tower.SETTINGS))
    types=settings.get('filament_type',[])
    return [{'slot':i+1,'material':str(value),'rigid':tower.rigid_material(value)} for i,value in enumerate(types[:tower.MAX_TOOLS])]

def detect_project_slicer(path):
    with zipfile.ZipFile(path) as archive:
        model=ET.fromstring(archive.read(tower.MODEL))
    metadata={e.get('name','').lower():(e.text or '').strip() for e in model.findall(tower.Q('metadata'))}
    application=metadata.get('application','')
    def normalized(value):return re.sub(r'[^a-z0-9]','',value.lower())
    app=normalized(application)
    if app.startswith(('snapmakerorca','snorca')):branch='snapmaker'
    elif app.startswith('orcaslicer'):branch='mainline'
    else:
        snap=any(normalized(k).startswith(('snapmakerorca','snorca')) for k in metadata)
        main='orcaslicer' in metadata
        branch='snapmaker' if snap and not main else 'mainline' if main and not snap else None
    return {'branch':branch,'application':application}

def project_summary(path):
    source=Path(path).expanduser().resolve()
    return {'plates':plates(source),'materials':project_materials(source),'folder':str(source.parent),'slicer':detect_project_slicer(source)}

def tower_options(data):
    return {'width':float(data.get('width',30)), 'rib_size':float(data.get('rib_size',5)),
            'purge_volume':float(data.get('purge_volume',5)), 'brim_width':float(data.get('brim_width',5)), 'brim_thickness':float(data.get('brim_thickness',.6)),
            'support_slot':int(data['support_slot']) if data.get('support_slot') else None,
            'frame_slot':int(data['frame_slot']) if data.get('frame_slot') else None}


def plate_options(data,plate):
    if 'plate_options' not in data:return tower_options(data)
    values=data['plate_options'].get(str(plate),{})
    return tower_options({k:v for k,v in values.items() if k!='support_slot'})

def extract_gcode(folder,plate):
    """Only inspect newly produced output, never stale G-code from a source ZIP."""
    candidates=list(folder.glob('*.gcode'))
    if len(candidates)==1:return candidates[0]
    for p in candidates:
        if p.name==f'plate_{plate}.gcode':return p
    archive=folder/'sliced.3mf'
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.gcode')]
            exact=[n for n in names if Path(n).name==f'plate_{plate}.gcode']
            chosen=exact or names
            if len(chosen)==1:
                target=folder/'exported.gcode'
                with z.open(chosen[0]) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
                return target
    raise tower.TowerError('Orca did not export a unique plain G-code file for the selected plate. Use manual export below.')

class Workflow:
    @staticmethod
    def initial_state():
        return {'busy':False,'stage':'ready','message':'Choose the original 3MF and plate.','events':[],'project':'','result':None,'folder':'','inputs':{},'open_after':None}
    def __init__(self):
        self.stage_started=time.monotonic();self.started=time.monotonic();self.log_path=None
        self.lock=threading.Lock();self.cancelled=threading.Event();self.process=None
        self.state=self.initial_state()
        self.slicer_branch=load_settings().get('slicer_branch') or ('snapmaker' if 'snapmaker' in load_settings().get('orca','').lower() else 'mainline')
        self.keep_working=False;self.work_folder=None;self.options=tower_options({});self.source=None;self.output=None;self.plate=1;self.selected_plates=[1];self.open_after=True;self.orca=load_settings().get("orca",DEFAULT_ORCA)
    def update(self,stage,message,**values):
        with self.lock:
            self.stage_started=time.monotonic()
            self.state.update(stage=stage,message=message,**values)
            self.state['events'].append(message)
    def snapshot(self):
        with self.lock:result=json.loads(json.dumps(self.state))
        result['stage_seconds']=int(time.monotonic()-self.stage_started)
        result['elapsed_seconds']=int(time.monotonic()-self.started)
        return result
    def reset(self):
        with self.lock:
            if self.state['busy']:raise tower.TowerError('Stop the current job before choosing a new original 3MF.')
            self.state=self.initial_state();self.stage_started=time.monotonic();self.started=self.stage_started;self.log_path=None
            self.source=None;self.output=None;self.plate=1;self.selected_plates=[1];self.options=tower_options({});self.open_after=True
    def check_cancel(self):
        if self.cancelled.is_set():raise tower.TowerError('Stopped. Existing output files are retained.')
    def launch(self,target,*args):
        with self.lock:
            if self.state['busy']:raise tower.TowerError('A step is already running.')
            if target in (self.automatic,self.manual_generate):
                self.state.update(events=[],result=None,stage='starting',message='Starting tower generation…',project='',folder='')
            self.state['busy']=True
            self.started=time.monotonic();self.stage_started=self.started;self.log_path=None
        self.cancelled.clear()
        def run():
            try:target(*args)
            except Exception as error:self.update('needs_attention',str(error))
            finally:
                with self.lock:self.state['busy']=False
        threading.Thread(target=run,daemon=True).start()
    def setup(self,data):
        source=Path(data['source']).expanduser().resolve()
        if source.suffix.lower()!='.3mf' or not source.is_file():raise tower.TowerError('Choose an existing original .3mf project.')
        available={p['number']:p for p in plates(source)}
        selected=list(dict.fromkeys(int(n) for n in data.get('plates',[data.get('plate',1)])))
        if not selected:raise tower.TowerError('Select at least one plate without a generated tower.')
        if any(n not in available for n in selected):raise tower.TowerError('Invalid plate number.')
        occupied=[n for n in selected if available[n]['has_tower']]
        if occupied:raise tower.TowerError('These plates already contain generated towers: '+', '.join(map(str,occupied)))
        self.selected_plates=selected
        self.keep_working=bool(data.get('keep_working',False))
        parent=Path(data.get('output') or source.parent).expanduser().resolve()
        parent.mkdir(parents=True,exist_ok=True)
        folder=parent/(source.stem+'_tower_'+time.strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(2));folder.mkdir()
        self.source=source;self.plate=selected[0];self.slicer_branch=data.get('slicer_branch',self.slicer_branch);self.orca=save_orca(data.get('orca') or self.orca,self.slicer_branch);save_source_folder(source)
        self.options=plate_options(data,self.plate) if len(selected)==1 else tower_options({});self.open_after=bool(data.get('open_after',True))
        self.work_folder=folder
        self.output=folder/(source.stem+'_tower.3mf')
        self.update('ready','Output folder created. Original project will remain unchanged.',folder=str(folder),project='',result=None)
    def finish_output(self):
        """Publish without overwriting anything; delete only this run's workspace."""
        if self.work_folder is None:return
        self.check_cancel()
        original=self.output;folder=self.work_folder
        if original.parent!=folder or folder==self.source.parent:
            raise tower.TowerError('Cannot safely identify the working folder; output retained.')
        version=1
        while True:
            target=self.source.parent/f'{self.source.stem}_tower_v{version}.3mf'
            try:stream=target.open('xb')
            except FileExistsError:
                version+=1;continue
            try:
                with stream,original.open('rb') as source:
                    shutil.copyfileobj(source,stream)
                    stream.flush();os.fsync(stream.fileno())
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            break
        self.output=target;self.work_folder=None;self.log_path=None
        with self.lock:
            self.state.update(project=str(target),folder=str(target.parent))
            self.state['events'].append(f'Final project saved: {target.name}')
        if self.keep_working:
            with self.lock:self.state['events'].append(f'Working folder kept for debugging: {folder}')
            return
        try:shutil.rmtree(folder)
        except OSError:
            with self.lock:self.state['events'].append(f'Project saved, but the working folder could not be removed: {folder}')

    def slice(self,project,tag):
        self.check_cancel()
        folder=self.output.parent/tag;folder.mkdir(exist_ok=False)
        executable=resolve_orca(self.orca)
        args=[str(executable),'--slice',str(self.plate),'--arrange','0','--orient','0','--outputdir',str(folder)]
        if self.slicer_branch=='mainline':args+=['--export-3mf','sliced.3mf']
        else:args+=['--allow-newer-file']
        args.append(str(project))
        log=folder/'orca.log';self.log_path=log
        with log.open('wb') as stream:
            self.process=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT)
            try:
                while self.process.poll() is None:
                    if self.cancelled.wait(.25):
                        self.process.terminate()
                        try:self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
                        self.check_cancel()
                code=self.process.returncode
            finally:self.process=None
        if code:
            reason='crashed' if code<0 or code in (134,139) else f'stopped (exit {code})'
            raise tower.TowerError(f'Orca automatic slicing {reason}. Log: {log}. Continue with the manual export step below.')
        return extract_gcode(folder,self.plate)
    def generate(self,reference):
        self.check_cancel();self.update('generate','Building the tower and brim on the selected plate… First use may download the brim geometry library.')
        manifest=tower.Project(self.source,self.plate,self.slicer_branch).generate(self.output,reference_gcode=reference,**self.options)
        self.update('generate',f"Frame: slot {manifest['frame_slot']} ({manifest['frame_material']}). {len(manifest['lanes'])} sections; height {manifest['tower_height']:.3f} mm; minimum priming {manifest['purge_volume']:g} mm³.")
        self.check_cancel();self.update('tower_ready',self.completion_message(),project=str(self.output),open_after=self.open_after)
    def completion_message(self):
        if self.open_after:return 'Tower generated and saved. Opening the project in Orca for you to review placement and slice.'
        return 'Tower generated and added to project plate.'
    def verify(self,gcode):
        self.check_cancel();self.update('audit','Checking material separation, section coverage, and every post-pickup tower visit…',result=None)
        result=tower.audit(gcode,tower.load_manifest(self.output,self.plate))
        self.check_cancel()
        if self.work_folder is not None:(self.work_folder/'audit.json').write_text(json.dumps(result,indent=2))
        if result['passed']:
            self.update('passed',self.completion_message(),result=result,open_after=self.open_after)
        else:self.update('failed','Audit did not pass. Review the errors below; this output is not verified.',result=result)
    def automatic(self,data):
        with self.lock:self.state['inputs']=dict(data)
        self.setup(data)
        if len(self.selected_plates)>1:return self.automatic_batch(data)
        self.update('reference_slice',f'Slicing original plate {self.plate} in Orca…')
        try:ref=self.slice(self.source,'reference_slice')
        except tower.TowerError as error:
            self.update('manual_reference',str(error)+' The original project has been opened in Orca for the guided manual export path.')
            self.open_in_orca(self.source);return
        self.generate(ref)
        self.finish_output()
        self.update('tower_ready',self.completion_message(),project=str(self.output),open_after=self.open_after)
        if self.open_after:self.open_project()
    def automatic_batch(self,data):
        original=self.source;final_output=self.output;current=original;results=[]
        for index,plate in enumerate(self.selected_plates,1):
            self.check_cancel();self.plate=plate
            row={'plate':plate,'generated':False};results.append(row)
            self.update('reference_slice',f'Plate {plate} ({index}/{len(self.selected_plates)}): slicing reference…',result={'plates':results})
            try:
                reference=self.slice(original,f'plate_{plate}_reference_slice')
                self.check_cancel()
                self.update('generate',f'Plate {plate}: building its tower…')
                candidate=final_output.parent/f'plate_{plate}_generated.3mf'
                tower.Project(current,plate,self.slicer_branch).generate(candidate,reference_gcode=reference,**plate_options(data,plate))
                current=candidate;row['generated']=True
                row['validation']='not requested'
                self.update('generate',f'Plate {plate}: tower generated.',result={'plates':results})
            except Exception as error:
                self.check_cancel()
                row['error']=str(error)
                self.update('generate',f'Plate {plate}: could not generate a tower; continuing with the other plates.',result={'plates':results})
        self.check_cancel()
        generated=[r for r in results if r['generated']]
        if not generated:
            self.update('batch_failed','No towers were generated. See the plate results below. You can retry a single plate using guided manual export.',result={'plates':results})
            return
        shutil.copy2(current,final_output)
        shutil.copy2(str(current)+'.ipt.json',str(final_output)+'.ipt.json')
        self.update('generate','Combined project saved.',project=str(final_output))
        failures=len(results)-len(generated)
        message=f"Generated towers on {len(generated)} of {len(results)} selected plates."
        if failures:message+=' Plates without a generated tower remain unchanged; see results below.'
        message+=' Review placement and slice the combined project in Orca.'
        self.update('batch_complete',message,project=str(final_output),result={'plates':results},open_after=self.open_after)
        (final_output.parent/'plate_results.json').write_text(json.dumps({'plates':results},indent=2))
        self.finish_output()
        if self.open_after:self.open_project()

    def manual_generate(self,data):
        selected=data.get('plates',[data.get('plate',1)])
        if len(selected)!=1:raise tower.TowerError('Select exactly one plate for manual reference G-code generation.')
        data=dict(data,plate=int(selected[0]))
        # Reuse an interrupted automatic job only if it has no generated tower.
        if not self.source or self.output.exists() or self.source!=Path(data['source']).expanduser().resolve() or self.plate!=int(data.get('plate',1)):self.setup(data)
        self.options=plate_options(data,self.plate)
        self.generate(selected_gcode(data['reference']))
        self.finish_output()
        if self.open_after:self.open_project()
    def open_in_orca(self,project):
        executable=resolve_orca(self.orca)
        bundle=next((p for p in executable.parents if p.suffix=='.app'),None)
        if sys.platform=='darwin' and bundle:
            subprocess.run(['/usr/bin/open','-a',str(bundle),str(project)],check=True)
        else:subprocess.Popen([str(executable),str(project)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def open_project(self):
        if not self.output or not self.output.exists():raise tower.TowerError('Generate the tower project first.')
        self.open_in_orca(self.output)

def browse_files(path,kind):
    folder=Path(path or Path.home()/'Documents').expanduser().resolve()
    if folder.is_file():folder=folder.parent
    extensions={'source':{'.3mf'},'reference':{'.gcode'},'final':{'.gcode'}}
    entries=[]
    try:
        for p in folder.iterdir():
            if p.name.startswith('.'):continue
            directory=p.is_dir();app=kind=='orca' and p.suffix=='.app'
            if directory or kind=='orca' or p.suffix.lower() in extensions.get(kind,set()):
                entries.append({'name':p.name,'path':str(p),'directory':directory and not app})
    except PermissionError:
        raise tower.TowerError('Access to this folder was blocked. Check folder permissions or paste the full file path in the main window.')
    return {'folder':str(folder),'parent':str(folder.parent),'entries':sorted(entries,key=lambda e:(not e['directory'],e['name'].lower()))}

def selected_gcode(path,label='Reference G-code'):
    selected=Path(path).expanduser().resolve()
    if selected.suffix.lower()!='.gcode' or not selected.is_file():raise tower.TowerError(f'Choose an existing {label} .gcode file.')
    return selected

def open_wizard_browser(url):
    # Browser startup must never block the local HTTP server.
    try:
        if sys.platform=='darwin':
            subprocess.run(['/usr/bin/open',url],check=True,timeout=15)
        elif not webbrowser.open(url):
            raise RuntimeError('No browser accepted the request')
    except Exception as error:
        print(f'Could not open the browser: {error}. Open {url} manually.',flush=True)

def serve(open_browser=True):
    workflow=Workflow();token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,data,status=200,kind='application/json'):
            payload=data.encode() if isinstance(data,str) else json.dumps(data).encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
        def allowed(self):
            return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}' and self.headers.get('X-Tower-Token')==token and self.headers.get('Origin',f'http://127.0.0.1:{self.server.server_port}')==f'http://127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if self.path=='/tower-icon.png':
                if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return self.send({'error':'Invalid host'},403)
                payload=Path(__file__).with_name('tower-icon.png').read_bytes()
                self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
            if self.path=='/':
                if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return self.send({'error':'Invalid host'},403)
                return self.send((Path(__file__).with_name('wizard.html')).read_text().replace('__TOKEN__',token),kind='text/html; charset=utf-8')
            if not self.allowed():return self.send({'error':'Unauthorized'},403)
            if self.path=='/settings':
                source_folder=load_settings().get('source_folder','')
                if source_folder and not Path(source_folder).is_dir():source_folder=''
                return self.send({'orca':workflow.orca,'platform':sys.platform,'source_folder':source_folder,'slicer_branch':workflow.slicer_branch,'slicers':slicer_choices()})
            if self.path=='/state':return self.send(workflow.snapshot())
            self.send({'error':'Not found'},404)
        def do_POST(self):
            if not self.allowed():return self.send({'error':'Unauthorized'},403)
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<100000:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(size));action=self.path
                if action=='/settings':
                    if workflow.snapshot()['busy']:raise tower.TowerError('Wait for the current step to finish before changing Orca.')
                    branch=data.get('slicer_branch',workflow.slicer_branch)
                    workflow.orca=save_orca(data.get('orca',''),branch);workflow.slicer_branch=branch
                    return self.send({'orca':workflow.orca,'slicer_branch':branch,'slicers':slicer_choices()})
                if action=='/browse':return self.send(browse_files(data.get('path'),data['kind']))
                if action=='/plates':return self.send(project_summary(data['source']))
                if action=='/reset':workflow.reset()
                elif action=='/auto':workflow.launch(workflow.automatic,data)
                elif action=='/generate':workflow.launch(workflow.manual_generate,data)
                elif action=='/audit':
                    if not workflow.output:raise tower.TowerError('Generate a tower in this session first.')
                    workflow.launch(workflow.verify,selected_gcode(data['final'],'Final G-code'))
                elif action=='/open':workflow.open_project()
                elif action=='/cancel':workflow.cancelled.set()
                else:return self.send({'error':'Not found'},404)
                self.send({'ok':True})
            except Exception as error:self.send({'error':str(error)},400)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}/'
    print('Prime Tower Wizard: '+url,flush=True)
    print('Keep this window running. Press Control-C to close the wizard.',flush=True)
    if open_browser:threading.Thread(target=open_wizard_browser,args=(url,),daemon=True).start()
    try:server.serve_forever()
    except KeyboardInterrupt:workflow.cancelled.set()
    finally:server.server_close()

if __name__=='__main__':serve('--no-browser' not in sys.argv)
