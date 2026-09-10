#!/usr/bin/env python3
"""Render local IEDL examples and build a portable HTML gallery. No paid calls."""
import argparse
import concurrent.futures
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import time

ROOT = Path(__file__).resolve().parent


def build_html(cases, results):
    cards = []
    groups = list(dict.fromkeys(c['group'] for c in cases))
    for case in cases:
        result = results.get(case['id'], {})
        status = 'Recipe only' if case['remote'] else result.get('status', 'Not rendered')
        successful = status == 'Rendered'
        recipe = (ROOT / 'recipes' / (case['id'] + '.iedl')).read_text()
        image = result.get('image', 'source.jpg') if successful else 'source.jpg'
        command = ['5am', 'media', 'image-edit', 'render', 'recipes/' + case['id'] + '.iedl']
        command += ['--media-id', 'YOUR_MEDIA_ID'] if case['remote'] else ['--input', 'source.jpg']
        for name, path in case['assets'].items():
            command += ['--asset', name + '=' + path]
        command += ['-o', 'edited.' + ('jpg' if case['format'] == 'jpeg' else case['format'])]
        # All catalog values are local trusted strings; escaping also keeps generated errors inert.
        esc = html.escape
        links = f'<a download href="recipes/{case["id"]}.iedl">Recipe ↓</a>'
        if successful:
            links += f'<a download href="{image}">Image ↓</a><a href="resolved/{case["id"]}.json">Resolved report ↗</a>'
        if result.get('mask'):
            links += f'<a href="{result["mask"]}">Mask ↗</a>'
        if result.get('bundle'):
            links += f'<a download href="{result["bundle"]}">Bundle ↓</a>'
        visual = f'<div class="comparison"><img loading="lazy" src="source.jpg" alt="Original concert photograph"><img class="edited" loading="lazy" src="{image}" alt="{esc(case["title"], quote=True)}"><span class="before-label">ORIGINAL</span><span class="after-label">EDITED</span></div>' if successful else '<div class="comparison pending"><img loading="lazy" src="source.jpg" alt="Original only; this example has no rendered result"><span class="pending-label">'+esc(status)+' · original shown</span></div>'
        slider = f'<label class="slider">Before / after <input aria-label="Compare {esc(case["title"],quote=True)}" type="range" min="0" max="100" value="65"></label>' if successful else ''
        error = '<p class="error">'+esc(result['error'])+'</p>' if result.get('error') else ''
        cards.append(f'''<article id="{case['id']}" data-group="{esc(case['group'],quote=True)}" data-search="{esc((case['title']+' '+case['group']+' '+recipe).lower(),quote=True)}">
<div class="card-top"><span>{esc(case['group'])}</span><span class="status {'ok' if successful else ''}">{esc(status)}</span></div>
{visual}{slider}<div class="card-body"><h3>{esc(case['title'])}</h3><p>{esc(case['note'])}</p>{error}<div class="links">{links}</div>
<details><summary>Recipe & command</summary><pre><code>{esc(recipe)}</code></pre><button class="copy" type="button">Copy recipe</button><pre class="command"><code>{esc(' '.join(command))}</code></pre></details></div></article>''')
    options = ''.join(f'<option>{html.escape(group)}</option>' for group in groups)
    rendered = sum(r.get('status') == 'Rendered' for r in results.values())
    remote = sum(c['remote'] for c in cases)
    commands = sorted({line.split()[0] for case in cases for line in (ROOT/'recipes'/(case['id']+'.iedl')).read_text().splitlines() if line and not line.startswith(('#','iedl '))})
    registry = json.loads((ROOT/'capabilities.json').read_text())['registry']
    missing = set(registry) - set(commands)
    if missing:
        raise ValueError('Catalog omits IEDL commands: ' + ', '.join(sorted(missing)))
    content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IEDL / The image-edit field guide</title><meta name="description" content="Real 5AM CLI renders: 113 photographic examples of IEDL adjustments, presets, masks and editing tools."><link rel="stylesheet" href="gallery.css"></head><body>
<header><a class="brand" href="../../README.md">5AM <span>/ FIELD GUIDE 01</span></a><nav><a href="../../skills/iedl/SKILL.md">LLM skill ↗</a><a href="../../docs/iedl.md">IEDL reference ↗</a></nav></header>
<main><section class="hero"><div><p class="eyebrow">ONE PHOTOGRAPH. AN EDITABLE LANGUAGE.</p><h1>See what<br>an edit does.</h1><p class="intro">Mixed stage light. Bright satin. Deep shadows. Explore the image editor one operation at a time—with real renders and recipes you can take apart.</p><a class="cta" href="#catalog">Explore the edits ↓</a><p class="small">{rendered} local renders · {remote} authenticated recipe examples · {len(registry)} IEDL commands · 20 presets</p></div><figure><img src="images/stage-balance.jpg" alt="Concert photograph with gentle highlight and color adjustments"><figcaption>STAGE BALANCE / A restrained starting point, not a universal correction.</figcaption></figure></section>
<section class="context"><div><h2>Real pixels.<br>Honest examples.</h2></div><div><p>Every card marked <strong>Rendered</strong> was executed by the shared image-edit runtime on this 640 × 960 derivative of the supplied photograph. Drag to compare; open the recipe to reproduce it. These are capability demonstrations, not recommended corrections for every image.</p><p>Manual masks are explicitly labeled. Remote selections and Magic Eraser examples show the <strong>original only</strong>: no AI results are fabricated. This image has no visible stars or red-eye; the relevant tools may show little change. Clipped stage lights cannot recover detail absent from the JPEG.</p><p><a href="README.md">Setup, rebuild & provenance ↗</a> · <a href="source.jpg">Download the sample photo ↗</a> · <a href="results.json">Execution results ↗</a></p></div></section>
<section id="catalog"><div class="catalog-title"><h2>The edit library</h2><span id="count">{len(cases)} examples</span></div><div class="toolbar"><label>Find a tool<input id="search" type="search" placeholder="Try exposure, polygon, skin, cinematic…"></label><label>Explore<select id="group"><option value="">All categories</option>{options}</select></label><button id="reset" type="button">Reset filters</button></div><div class="grid">{''.join(cards)}</div><p id="empty" hidden>No matching examples.</p></section>
<section class="workflow"><p class="eyebrow">FROM EXPERIMENT TO AUTOMATION</p><h2>Find a look. Keep the recipe.</h2><ol><li>Inspect the pixels and mask edges.</li><li>Download and validate the recipe.</li><li>Render another image; re-check local geometry.</li><li>Save a resolved bundle for replay, or use the reusable recipe in a workflow.</li></ol><pre><code>5am update --runtime-only
5am media image-edit validate recipes/stage-balance.iedl
5am media image-edit render recipes/stage-balance.iedl --input source.jpg -o stage.jpg --bundle stage.iedl.zip</code></pre><p>Workflow Python calls the CLI. Shared JavaScript owns IEDL rules; Go owns Gemini transport and credentials. Image rendering and local analysis stay local.</p></section></main><footer>5AM / IEDL 1 · Photographic examples, not a benchmark of every scene. <a href="README.md#photo-and-license">Photo & license</a></footer><script src="gallery.js"></script></body></html>'''
    hero = next((r['image'] for r in results.values() if r.get('status') == 'Rendered'), 'source.jpg')
    if results.get('stage-balance',{}).get('status') != 'Rendered':
        content = content.replace('src="images/stage-balance.jpg"', f'src="{hero}"')
    if (ROOT/'custom-source.json').exists():
        content = content.replace('Original concert photograph', 'Original photograph')
        content = content.replace('Mixed stage light. Bright satin. Deep shadows.', 'Your photograph. Your experiments.')
        content = content.replace('640 × 960 derivative of the supplied photograph', 'resized copy of your photograph')
        content = content.replace('Concert photograph with gentle highlight and color adjustments', 'Gallery preview')
        content = content.replace('STAGE BALANCE / A restrained starting point, not a universal correction.', 'CAPABILITY PREVIEW / Review each edit on your own photograph.')
        content = content.replace('This image has no visible stars or red-eye; the relevant tools may show little change.', 'Some tools require suitable targets, such as stars or red-eye.')
        content = content.replace('Manual masks are explicitly labeled.', 'Manual masks and retouch coordinates were drawn for the original concert example. They do not identify subjects in your image: edit the recipes before judging local effects.')
        for relative in ['../../README.md','../../skills/iedl/SKILL.md','../../docs/iedl.md']:
            content = content.replace(relative, 'https://github.com/digvan/5am-cli/blob/main/'+relative.removeprefix('../../'))
    (ROOT/'index.html').write_text(content)


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='Execute local recipes using the installed CLI')
    parser.add_argument('--cli', default='5am')
    parser.add_argument('--runtime', help='Optional explicit runner.mjs')
    parser.add_argument('--browser', help='Optional explicit Chrome executable')
    parser.add_argument('--jobs', type=int, choices=(1,2), default=1, help='Bound parallel browsers; default serial')
    parser.add_argument('--only', help='Comma-separated case IDs to rerender')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--input', type=Path, help='Create a gallery with your own JPEG, PNG, or WebP')
    parser.add_argument('--output-dir', type=Path, help='New/empty destination for --input; existing gallery for rebuilds')
    parser.add_argument('--width', type=int, default=640, help='Preview width for your image (64–2048; default 640)')
    args = parser.parse_args()
    if args.input and not args.output_dir:
        parser.error('--input requires --output-dir to protect the published examples')
    if not 64 <= args.width <= 2048:
        parser.error('--width must be between 64 and 2048')
    template = ROOT
    known = {c["id"] for c in json.loads((template/"cases.json").read_text())}
    if args.only and set(args.only.split(","))-known: parser.error("Unknown case in --only")
    if args.output_dir:
        destination = args.output_dir.expanduser().resolve()
        if args.input:
            source = args.input.expanduser().resolve()
            if not source.is_file(): parser.error('--input must be an existing image')
            if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
                parser.error('--input requires a new or empty output directory; choose another directory')
            # Prepare the source before copying anything; originals are never overwritten.
            with tempfile.TemporaryDirectory(prefix='iedl-gallery-') as temporary:
                converted = Path(temporary)/'converted.jpg'
                resized = Path(temporary)/'source.jpg'
                with source.open('rb') as stream:
                    jpeg = stream.read(3) == b'\xff\xd8\xff'
                commands = []
                if jpeg: shutil.copy2(source,converted)
                else: commands.append([args.cli,'media','convert',str(source),'--output',str(converted)])
                commands.append([args.cli,'media','resize',str(converted),'--width',str(args.width),'--output',str(resized)])
                for command in commands:
                    result = subprocess.run(command,capture_output=True,text=True,timeout=150)
                    if result.returncode: raise RuntimeError(result.stderr or result.stdout)
                destination.mkdir(parents=True,exist_ok=True)
                for name in ['cases.json','capabilities.json','gallery.css','gallery.js','README.md','build_gallery.py','check_gallery.py','test_gallery_builder.py','LICENSE']:
                    shutil.copy2(template/name,destination/name)
                shutil.copytree(template/'recipes',destination/'recipes')
                shutil.copy2(resized,destination/'source.jpg')
                (destination/'custom-source.json').write_text(json.dumps({'preview_width':args.width}))
            args.render = True
        ROOT = destination
    if not (ROOT/'cases.json').is_file(): parser.error('Output directory is not an initialized gallery')
    cases = json.loads((ROOT/'cases.json').read_text())
    results_path = ROOT/'results.json'
    previous = json.loads(results_path.read_text()) if results_path.exists() else {}
    source_hash = hashlib.sha256((ROOT/'source.jpg').read_bytes()).hexdigest()
    if previous and previous.get('source_sha256') != source_hash:
        parser.error('Source changed: create a new gallery with --input and a new --output-dir')
    results = previous.get('cases',{})
    selected = set(args.only.split(',')) if args.only else {c['id'] for c in cases}
    if selected-{c['id'] for c in cases}: parser.error('Unknown case in --only')
    env = dict(os.environ, **{'5AM_NO_UPDATE_CHECK':'1'})
    def call(action, *argv):
        command = [args.cli,'media','image-edit',action,*map(str,argv)]
        if args.runtime: command += ['--runtime',args.runtime]
        if args.browser: command += ['--browser',args.browser]
        result = subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=150)
        if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip()[-1600:])
        return json.loads(result.stdout)
    if args.render:
        for directory in ['images','resolved','masks','assets','bundles']: (ROOT/directory).mkdir(exist_ok=True)
        seed = ROOT/'assets/subject-mask.png'
        if not seed.exists() or args.overwrite:
            call('render','recipes/stage-balance.iedl','--input','source.jpg','--mask','subject','-o',seed,*(['--overwrite'] if args.overwrite else []))
        def execute(case):
            id=case['id'];start=time.monotonic()
            try:
                call('validate','recipes/'+id+'.iedl')
                if case['remote']: return id,dict(status='Recipe only',validated=True)
                output='images/'+id+'.'+('jpg' if case['format']=='jpeg' else case['format'])
                argv=['recipes/'+id+'.iedl','--input','source.jpg','-o',output,'--resolved','resolved/'+id+'.json']
                if case['mask']: argv += ['--bundle','bundles/'+id+'.iedl.zip']
                for name,path in case['assets'].items(): argv += ['--asset',name+'='+path]
                if args.overwrite: argv += ['--overwrite']
                rendered=call('render',*argv)
                record=dict(status='Rendered',image=output,width=rendered['width'],height=rendered['height'],seconds=round(time.monotonic()-start,2))
                if case['mask']:
                    maskpath='masks/'+id+'.png'
                    call('render','bundles/'+id+'.iedl.zip','--input','source.jpg','--mask',case['mask'],'-o',maskpath,*(['--overwrite'] if args.overwrite else []))
                    record['mask']=maskpath
                    record['bundle']='bundles/'+id+'.iedl.zip'
                return id,record
            except Exception as error: return id,dict(status='Failed',error=str(error))
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures=[pool.submit(execute,c) for c in cases if c['id'] in selected]
            for future in concurrent.futures.as_completed(futures):
                id,record=future.result();results[id]=record
                results_path.write_text(json.dumps(dict(source_sha256=hashlib.sha256((ROOT/'source.jpg').read_bytes()).hexdigest(),cases=results),indent=2)+'\n')
                print(record['status'],id,record.get('error',''),flush=True)
    build_html(cases,results)
    failures=[id for id,r in results.items() if r.get('status')=='Failed']
    print(f'Gallery ready: {len(cases)} examples; {len(failures)} failures')
    return bool(failures)


if __name__=='__main__': raise SystemExit(main())
