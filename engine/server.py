import json,secrets,threading,urllib.parse
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import service as s
PORT=8096;TOKEN=secrets.token_urlsafe(32);WEB=Path(__file__).parent/'web'
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,data,status=200,mime='application/json'):
  raw=json.dumps(data,ensure_ascii=False).encode() if mime=='application/json' else data.encode() if isinstance(data,str) else data
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.end_headers();self.wfile.write(raw)
 def trusted(self):return self.headers.get('Host') in ('127.0.0.1:'+str(PORT),'localhost:'+str(PORT))
 def do_GET(self):
  if not self.trusted():return self.send({'error':'Ongeldige host'},403)
  path=urllib.parse.urlparse(self.path).path
  if path=='/api/state':return self.send({**s.state(),'token':TOKEN})
  assets={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css'),'/app.js':('app.js','text/javascript')}
  if path in assets:
   name,mime=assets[path];return self.send((WEB/name).read_bytes(),mime=mime)
  return self.send({'error':'Niet gevonden'},404)
 def do_POST(self):
  if not self.trusted() or self.headers.get('X-Local-Token')!=TOKEN:return self.send({'error':'Vernieuw de lokale pagina.'},403)
  origin=self.headers.get('Origin')
  if origin and origin not in ('http://127.0.0.1:'+str(PORT),'http://localhost:'+str(PORT)):return self.send({'error':'Ongeldige herkomst'},403)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length<0 or length>100*1024*1024:raise ValueError('Maximaal 100 MB.')
   if self.path=='/api/upload':
    ext={ 'video/mp4':'mp4','video/webm':'webm','video/quicktime':'mov'}.get(self.headers.get('Content-Type',''))
    if not ext:raise ValueError('Kies mp4, webm of mov.')
    folder=s.DATA/'uploads';folder.mkdir(exist_ok=True);name=s.uid()+'.'+ext
    (folder/name).write_bytes(self.rfile.read(length));return self.send({'reference':'upload:'+name})
   if length>200000:raise ValueError('Te veel tekst.')
   d=json.loads(self.rfile.read(length))
   if self.path=='/api/discovery':return self.send(s.save_auto(d))
   if self.path=='/api/discover':return self.send({'id':s.start_discovery()})
   if self.path=='/api/client':
    c=s.config(d);cid=d.get('id') or s.uid();old=s.one('SELECT * FROM clients WHERE id=?',(cid,));next_run=(old['next_run'] if old and old['next_run'] else s.time.time()+7*86400) if c['weekly'] else None
    s.execute('INSERT INTO clients VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET config=excluded.config,next_run=excluded.next_run',(cid,json.dumps(c),next_run));return self.send({'id':cid})
   if self.path=='/api/run':return self.send({'id':s.start(str(d['client']))})
   if self.path=='/api/cancel':s.execute("UPDATE runs SET status='cancelled',message='Stop aangevraagd' WHERE id=? AND status IN ('queued','running')",(str(d['id']),));return self.send({'ok':True})
   return self.send({'error':'Niet gevonden'},404)
  except (ValueError,KeyError,TypeError) as e:return self.send({'error':str(e)},400)
  except Exception:return self.send({'error':'Opslaan mislukt.'},500)
if __name__=='__main__':
 s.init();server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);threading.Thread(target=s.worker,daemon=True).start();print(f'Clip Library: http://127.0.0.1:{PORT}',flush=True);server.serve_forever()
