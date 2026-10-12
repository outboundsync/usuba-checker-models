import json,os,sys,time,threading,urllib.request,urllib.error,concurrent.futures as cf
model,name,mt,cap,worst=sys.argv[1],sys.argv[2],int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5])
hold=[json.loads(l) for l in open('../../data/holdout.jsonl')]
rows=[json.loads(l) for l in open(f'gen_{name}.jsonl')]
todo=[i for i,r in enumerate(rows) if r['finish']=='length']
out=f'gen_{name}_big.jsonl'; lock=threading.Lock(); spent=[0.0]; inflight=[0]; stop=[None]; done=[]
def save(): open(out,"w").write("".join(json.dumps(x)+"\n" for x in rows))
def call(i):
    body=json.dumps({"model":model,"messages":hold[i]["messages"][:-1],"temperature":0,"max_tokens":mt,"usage":{"include":True}}).encode()
    err=""
    for a in range(4):
        try:
            q=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",body,{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
            d=json.load(urllib.request.urlopen(q,timeout=1800)); c=d["choices"][0]
            return {"task":hold[i]["task"],"output":c["message"]["content"] or "","finish":c["finish_reason"],"usage":d.get("usage")}
        except urllib.error.HTTPError as e:
            err=f"HTTP {e.code}"
            if e.code==402: stop[0]="402"; return None
        except Exception as e: err=str(e)[:80]
        time.sleep(10*2**a)
    print("ERR",i,err,flush=True); return None
def work(i):
    r=call(i)
    with lock:
        inflight[0]-=1
        if r:
            c=(r.get("usage") or {}).get("cost",0) or 0; spent[0]+=c; rows[i]=r; done.append(i); save()
            print(f"row {i} {r['finish']} cost {c:.3f} spent {spent[0]:.3f}",flush=True)
save()
with cf.ThreadPoolExecutor(4) as ex:
    fs=[]
    for i in todo:
        while True:
            with lock:
                if stop[0] or spent[0]+(inflight[0]+1)*worst>cap: break
                if inflight[0]<4: inflight[0]+=1; fs.append(ex.submit(work,i)); i=None; break
            time.sleep(2)
        if i is not None:
            if not stop[0]: stop[0]="cap"
            break
    cf.wait(fs)
save()
print("SUMMARY",name,"todo",len(todo),"rerun",len(done),"still_length",sum(rows[i]['finish']=='length' for i in done),"spent",round(spent[0],3),"stop",stop[0])
