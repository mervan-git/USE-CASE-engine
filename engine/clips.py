"""Local, cached shot search. Python standard library only."""
import argparse, hashlib, json, math, re, sqlite3, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL='gemini-3.6-flash'
BRIEF='Real people actively cleaning building window glass with scrubber, squeegee or water-fed pole. Visible tool contact and cleaning motion. Exclude talking heads, car glass and unrelated cleaning.'
def parse(response):
    txt=''.join(c.get('text','') for s in response.get('steps',[]) if s.get('type')=='model_output' for c in s.get('content',[]))
    try: data=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',txt.strip()))
    except (ValueError,TypeError): return []
    valid=[]
    for c in data.get('clips',[]):
        a,b=c.get('start_seconds'),c.get('end_seconds')
        if type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and a>=0 and 4<=b-a<=12: valid.append(c)
    return valid

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--client',default='Snijders');p.add_argument('--brief',default=BRIEF)
    p.add_argument('--query',default='professional window cleaning squeegee demonstration')
    p.add_argument('--count',type=int,default=10);p.add_argument('--max-analyses',type=int,default=3)
    p.add_argument('--online',action='store_true',help='Enable external requests; default uses saved shots only')
    a=p.parse_args()
    if not 1<=a.count<=100 or not 0<=a.max_analyses<=20: p.error('count 1–100; max-analyses 0–20')
    (ROOT/'work').mkdir(exist_ok=True);(ROOT/'outputs').mkdir(exist_ok=True)
    db=sqlite3.connect(ROOT/'work/clips.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS analyses (video TEXT, brief TEXT, model TEXT, response TEXT, created REAL, PRIMARY KEY(video,brief,model))')
    db.execute('CREATE TABLE IF NOT EXISTS searches (query TEXT PRIMARY KEY, response TEXT, created REAL)')
    # Import the already paid first experiment exactly once, for its original brief.
    seed=ROOT/'work/snijders_raw.json'
    if seed.exists():
        for v in json.loads(seed.read_text()).get('videos',[]):
            if v['response'].get('status')=='completed': db.execute('INSERT OR IGNORE INTO analyses VALUES(?,?,?,?,?)',(v['video_id'],BRIEF,MODEL,json.dumps(v['response']),time.time()))
        db.commit()
    keys={}
    if (ROOT/'.env').exists():
        for l in (ROOT/'.env').read_text().splitlines():
            if '=' in l and not l.lstrip().startswith('#'):
                k,v=l.split('=',1);keys[k.strip()]=v.strip().strip('\"\'')
    calls=[];found=[];seen=set()
    runid=str(time.time_ns()); logpath=ROOT/'outputs'/f'api-kosten-{runid}.json'
    def persist():logpath.write_text(json.dumps({'client':a.client,'calls':calls,'note':'Token usage is measured; USD estimates use standard paid rates dated 2026-09-11, not confirmed invoices. Failed calls with no usage have unknown billing. No euro conversion.'},indent=2))
    def request(url,key,payload=None):
        event={'provider':'gemini' if payload else 'youtube','status':'pending','estimated_usd':None};calls.append(event);persist()
        try:
            req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload else None,headers={'x-goog-api-key':keys[key],'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=180) as r: result=json.load(r)
            event['status']='completed'
            if payload:
                u=result.get('usage',{});event['usage']=u
                if 'total_input_tokens' in u and 'total_output_tokens' in u:
                    event['estimated_usd']=(u['total_input_tokens']*.75+(u['total_output_tokens']+u.get('total_thought_tokens',0))*3.75)/1e6
            else:event['search_requests']=1
            return result
        except urllib.error.HTTPError as e:event['status']='http_'+str(e.code);return {}
        except Exception as e:event['status']=type(e).__name__;return {}
        finally:persist()
    def collect(vid,response,cached):
        for c in parse(response):
            ident=(vid,c['start_seconds'],c['end_seconds'])
            if ident not in seen:
                seen.add(ident);found.append({'video':vid,**c,'cached':cached})
    for vid,response in db.execute('SELECT video,response FROM analyses WHERE brief=? AND model=? ORDER BY created',(a.brief,MODEL)):
        collect(vid,json.loads(response),True)
    if a.online and len(found)<a.count:
        for key in ('YOUTUBE_API_KEY','GEMINI_API_KEY'):
            if not keys.get(key):p.error(key+' ontbreekt in .env')
        old=db.execute('SELECT response,created FROM searches WHERE query=?',(a.query,)).fetchone()
        if old and time.time()-old[1]<86400: result=json.loads(old[0])
        else:
            q=urllib.parse.urlencode({'part':'snippet','type':'video','q':a.query,'maxResults':20,'videoDuration':'short'})
            result=request('https://www.googleapis.com/youtube/v3/search?'+q,'YOUTUBE_API_KEY')
            if 'items' in result:
                db.execute('INSERT OR REPLACE INTO searches VALUES(?,?,?)',(a.query,json.dumps(result),time.time()));db.commit()
        n=0
        for item in result.get('items',[]):
            if len(found)>=a.count or n>=a.max_analyses:break
            vid=item['id']['videoId']
            if db.execute('SELECT 1 FROM analyses WHERE video=? AND brief=? AND model=?',(vid,a.brief,MODEL)).fetchone():continue
            n+=1
            prompt='Inspect actual video. Find up to 3 continuous 4-12 second shots matching: '+a.brief+' Return only JSON {"clips":[{"start_seconds":number,"end_seconds":number,"description_nl":string,"uncertainty":string}]}. Times absolute from original video. If inaccessible/no match return empty clips. Never invent observations.'
            response=request('https://generativelanguage.googleapis.com/v1beta/interactions','GEMINI_API_KEY',{'model':MODEL,'input':[{'type':'video','uri':'https://www.youtube.com/watch?v='+vid},{'type':'text','text':prompt}]})
            if response.get('status')=='completed':
                db.execute('INSERT OR REPLACE INTO analyses VALUES(?,?,?,?,?)',(vid,a.brief,MODEL,json.dumps(response),time.time()));db.commit();collect(vid,response,False)
    found=found[:a.count];persist()
    slug=re.sub('[^a-z0-9-]+','-',a.client.lower()).strip('-') or 'client'
    lines=[f'https://www.youtube.com/watch?v={c["video"]}&t={int(c["start_seconds"])}s — {c["start_seconds"]}–{c["end_seconds"]} seconden' for c in found]
    (ROOT/'outputs'/f'{slug}-linkjes.txt').write_text('\n'.join(lines)+'\n')
    cost=sum(c['estimated_usd'] or 0 for c in calls)
    report={'client':a.client,'requested':a.count,'returned':len(found),'new_calls':len(calls),'estimated_gemini_usd':cost,'estimated_research_usd_per_returned_clip':cost/len(found) if found else None,'status':'complete' if len(found)==a.count else 'partial','clips':found,'verification':'AI-selected; not independently verified','ledger':logpath.name}
    (ROOT/'outputs'/f'{slug}-kosten.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('\n'.join(lines))
    db.close()
if __name__=='__main__':main()
