import json,os,re,threading,hashlib,urllib.request,time
MODEL="qwen/qwen3.5-397b-a17b"; CAP=9.0
HERE=os.path.dirname(os.path.abspath(__file__)); WORK=os.environ.get('R_WORK','/tmp/usuba_r_work'); os.makedirs(WORK,exist_ok=True)
LEDGER=WORK+'/ledger.json'; CACHE=WORK+'/cache.jsonl'
SEED_CACHE=os.path.join(HERE,'..','r3_cache','llm_cache.jsonl.gz')   # every model reply used for r2+r3 (offline replay: zero cost); delete R_WORK to re-query
if not os.path.exists(CACHE) and os.path.exists(SEED_CACHE):
    import gzip,shutil; shutil.copyfileobj(gzip.open(SEED_CACHE,'rb'),open(CACHE,'wb'))
_lk=threading.Lock(); _cache={}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try: d=json.loads(l); _cache[d['k']]=d
        except: pass
_tot=[json.load(open(LEDGER))['usd'] if os.path.exists(LEDGER) else 0.0]
def spent(): return _tot[0]
def _add(c):
    with _lk:
        _tot[0]+=c; json.dump({'usd':_tot[0]},open(LEDGER,'w'))
def call(system,user,tag='',temperature=0.0,max_tokens=6000,effort='none',seed=None):
    k=hashlib.sha1(json.dumps([system,user,temperature,seed,tag]).encode()).hexdigest()
    if k in _cache: return _cache[k]['out']
    if spent()>CAP: raise RuntimeError('budget cap')
    req=dict(model=MODEL,max_tokens=max_tokens,messages=[{"role":"system","content":system},{"role":"user","content":user}],reasoning={"effort":effort},
             provider={"data_collection":"deny","sort":"throughput"},usage={"include":True},temperature=temperature)
    if seed is not None: req['seed']=seed
    err=''
    for att in range(5):
        try:
            r=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=json.dumps(req).encode(),headers={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
            j=json.load(urllib.request.urlopen(r,timeout=300)); t=j["choices"][0]["message"].get("content") or ""
            _add((j.get("usage") or {}).get("cost") or 0.0)
            m=re.search(r"\{.*\}",t,re.S); out=json.loads(m.group(0))
            with _lk:
                _cache[k]=dict(k=k,out=out); open(CACHE,'a').write(json.dumps(_cache[k])+"\n")
            return out
        except Exception as e: err=repr(e)[:150]; time.sleep(2+att*3)
    return {"_error":err}
