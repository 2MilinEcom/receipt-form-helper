"""Mac screenshot picker and one-page receipt review."""
import html
import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def dropzone(page, directory):
    """Receive dragged local images through a temporary, local browser page."""
    directory = Path(directory)
    def receive(payload):
        if not isinstance(payload, list) or not 1 <= len(payload) <= 20:
            raise RuntimeError("Choose between 1 and 20 receipt images.")
        paths = []
        total = 0
        for i, entry in enumerate(payload):
            suffix = Path(entry["name"]).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise RuntimeError("Use PNG, JPG, or WebP screenshots.")
            data = base64.b64decode(entry["data"], validate=True)
            total += len(data)
            if len(data) > 20 * 1024 * 1024 or total > 80 * 1024 * 1024:
                raise RuntimeError("Use images under 20 MB each and 80 MB total.")
            safe_name = Path(entry["name"]).name
            path = directory / (f"{i+1:02d}_" + safe_name)
            path.write_bytes(data)
            paths.append(str(path))
        return paths
    page.expose_function("receiveReceiptImages", receive)
    page.set_content('''<!doctype html><meta charset="utf-8"><title>Drop your receipt screenshots</title>
<style>body{font:16px system-ui;margin:0;background:#f3f7fb;color:#193047}main{max-width:900px;margin:55px auto;padding:25px}h1{font-size:34px}#zone{border:3px dashed #83a5c6;border-radius:20px;padding:65px 24px;text-align:center;background:white;cursor:pointer}#zone.over{background:#e0efff;border-color:#1264a3}#previews{display:flex;gap:16px;flex-wrap:wrap;margin-top:24px}.card{background:white;border-radius:12px;padding:12px;width:180px;overflow-wrap:anywhere}.card img{width:180px;height:140px;object-fit:contain}.remove{background:#edf2f7;color:#193047;padding:6px}button{border:0;border-radius:9px;padding:15px 24px;background:#1264a3;color:white;cursor:pointer;margin-top:12px}button:disabled{opacity:.4;cursor:default}#error{color:#b00020}</style>
<main><h1>Add your receipt screenshots</h1><p>Drag all the Target screenshots here together. The helper will read them and show one combined review.</p>
<div id="zone" tabindex="0" role="button" aria-label="Drop screenshots or browse"><strong>Drop screenshots here</strong><p>PNG, JPG, or WebP • up to 20 images</p><small>Or click to browse</small></div>
<input id="files" type="file" accept="image/png,image/jpeg,image/webp" multiple hidden>
<div id="previews"></div><p id="error"></p><button id="read" disabled>Read screenshots</button>
<p id="status">Selected receipt images will be sent to OpenAI when you click Read screenshots.</p></main>
<script>
const zone=document.querySelector('#zone'), picker=document.querySelector('#files'), read=document.querySelector('#read'), error=document.querySelector('#error');
let selected=[];
function render(){const previews=document.querySelector('#previews');previews.replaceChildren();selected.forEach((f,i)=>{const card=document.createElement('div');card.className='card';const img=document.createElement('img');const url=URL.createObjectURL(f);img.src=url;img.onload=()=>URL.revokeObjectURL(url);const name=document.createElement('p');name.textContent=f.name;const remove=document.createElement('button');remove.textContent='Remove';remove.className='remove';remove.onclick=()=>{selected.splice(i,1);render();};card.append(img,name,remove);previews.append(card);});read.disabled=selected.length===0;}
function add(files){error.textContent='';for(const f of files){if(!/\\.(png|jpe?g|webp)$/i.test(f.name)){error.textContent='Use PNG, JPG, or WebP images.';continue;}if(f.size>20*1024*1024){error.textContent='An image exceeds 20 MB.';continue;}if(selected.length>=20){error.textContent='Maximum 20 images.';break;}if(!selected.some(g=>g.name===f.name&&g.size===f.size&&g.lastModified===f.lastModified))selected.push(f);}render();}
zone.onclick=()=>picker.click();zone.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();picker.click();}};picker.onchange=()=>{add(picker.files);picker.value='';};
for(const type of ['dragenter','dragover']) zone.addEventListener(type,e=>{e.preventDefault();zone.classList.add('over');});
zone.addEventListener('dragleave',()=>zone.classList.remove('over'));
zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('over');add(e.dataTransfer.files);});
window.addEventListener('dragover',e=>e.preventDefault());window.addEventListener('drop',e=>e.preventDefault());
read.onclick=async()=>{read.disabled=true;zone.style.pointerEvents='none';document.querySelector('#status').textContent='Reading screenshots with OpenAI…';
try{const payload=await Promise.all(selected.map(f=>new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve({name:f.name,data:r.result.split(',')[1]});r.onerror=reject;r.readAsDataURL(f);})));window.uploadedPaths=await window.receiveReceiptImages(payload);}
catch(e){error.textContent='Could not load images: '+e.message;read.disabled=false;zone.style.pointerEvents='auto';document.querySelector('#status').textContent='Try smaller PNG/JPG screenshots.';}};
</script>''')
    page.wait_for_function("window.uploadedPaths !== undefined", timeout=0)
    return [Path(path) for path in page.evaluate("window.uploadedPaths")]

def selected_files():
    if len(sys.argv) > 1:
        paths = [Path(arg).expanduser() for arg in sys.argv[1:]]
        files = []
        for path in paths:
            files.extend(sorted(path.iterdir()) if path.is_dir() else [path])
    elif sys.platform == "darwin":
        script = '''set chosen to choose file with prompt "Select Target receipt screenshots (hold Command for multiple)" of type {"public.image"} with multiple selections allowed
set collected to ""
repeat with f in chosen
set collected to collected & POSIX path of f & linefeed
end repeat
return collected'''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        files = [Path(line) for line in result.stdout.strip().splitlines()]
    else:
        files = list((ROOT / "receipts").glob("*"))
    files = [p.resolve() for p in files if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}]
    if not files:
        raise RuntimeError("No receipt images selected. Run python claim_helper.py /path/to/receipt/folder")
    return files

def review(page, rows, recognized):
    # Render from escaped text; images stay on the user's computer.
    headers = "<tr><th>Include</th><th>Item</th><th>Purchase date</th><th>Brand</th><th>Amount to claim (USD)</th><th>Screenshot evidence</th></tr>"
    body = []
    for n, row in enumerate(rows):
        fields = [f'<td><input type="checkbox" name="include" checked></td>',
                  f'<td><textarea name="name" rows="3" required>{html.escape(row["name"])}</textarea></td>',
                  f'<td><input name="date" placeholder="MM/DD/YYYY" value="{html.escape(row["date"], quote=True)}"></td>',
                  f'<td><input name="brand" value="{html.escape(row["brand"], quote=True)}"></td>',
                  f'<td><input name="cost" type="number" min="0.01" step="0.01" value="{html.escape(row["cost"], quote=True)}" placeholder="Missing item tax"></td>',
                  f'<td>Shown price: ${html.escape(row["price"] or "unknown")} before tax<br><strong>{html.escape(row.get("uncertainty", ""))}</strong><details><summary>Receipt evidence</summary>{html.escape(row["source"])}<br>{html.escape(row.get("evidence", ""))}</details></td>']
        body.append('<tr class="item">' + ''.join(fields) + '</tr>')
    evidence = "\n\n".join(Path(p).name + "\n" + "\n".join(l["text"] for l in lines) for p, lines in recognized.items())
    page.set_content('''<!doctype html><meta charset="utf-8"><title>Review clothing from screenshots</title>
<style>body{font:15px system-ui;padding:24px;background:#f3f7fb}table{width:100%;min-width:1060px;table-layout:fixed;border-collapse:collapse;background:white}td,th{text-align:left;padding:12px;border:1px solid #ddd;vertical-align:top;overflow-wrap:anywhere}th:nth-child(1){width:50px}th:nth-child(2){width:225px}th:nth-child(3){width:135px}th:nth-child(4){width:160px}th:nth-child(5){width:135px}input,textarea{width:100%;box-sizing:border-box;padding:9px;font:inherit}input[type=checkbox]{width:20px}button{background:#1264a3;color:white;border:0;padding:16px;border-radius:8px;margin:20px 0}pre{white-space:pre-wrap}#error{color:#b00020}details{margin-top:10px}strong{font-weight:500}</style>
<h1>Clothing read from your screenshots</h1><p>Review all five together. Missing fields are blank. Select only the stolen, unrecovered items.</p>
<p>Verify dates and receipt associations. When item tax is unknown, the amount uses the visible base price and excludes tax. You can replace it with a verified total including tax. Unknown brands are labelled Unknown. This review also confirms which included items were paid with the eligible Amex.</p>
<form><table>''' + headers + ''.join(body) + '''</table><p id="error"></p>
<button>Use these items and open Amex</button></form><details><summary>Recognized receipt text</summary><pre>''' + html.escape(evidence) + '''</pre></details>
<script>document.querySelector('form').onsubmit = e => { e.preventDefault(); const rows = [];
for(const tr of document.querySelectorAll('.item')) { const v=n=>tr.querySelector('[name='+n+']').value.trim();
if(!tr.querySelector('[name=include]').checked) continue;
const d=v('date'), m=/^(\\d{2})\\/(\\d{2})\\/(\\d{4})$/.exec(d);
const dt=m?new Date(+m[3],+m[1]-1,+m[2]):null;
if(!m || dt.getFullYear()!=+m[3] || dt.getMonth()!=+m[1]-1 || dt.getDate()!=+m[2] || !v('brand') || !v('name') || !/^\\d+(?:\\.\\d{1,2})?$/.test(v('cost')) || +v('cost')<=0){document.querySelector('#error').textContent='Complete the missing purchase date and amount for included items.';return;}
rows.push({name:v('name'),date:d,brand:v('brand'),cost:(+v('cost')).toFixed(2)});}
if(!rows.length){document.querySelector('#error').textContent='Select at least one item.';return;}
window.reviewedItems=rows; };</script>''')
    page.wait_for_function("window.reviewedItems !== undefined", timeout=0)
    return page.evaluate("window.reviewedItems")
