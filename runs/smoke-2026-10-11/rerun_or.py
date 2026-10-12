import json,os,sys,time,urllib.request,urllib.error,concurrent.futures as cf
model,f=sys.argv[1],sys.argv[2]
hold=[json.loads(l) for l in open('../../data/holdout.jsonl')]
rows=[json.loads(l) for l in open(f)]
todo=[i for i,r in enumerate(rows) if str(r['finish']).startswith('error')]
def call(i):
    body=json.dumps({"model":model,"messages":hold[i]["messages"][:-1],"temperature":0,"max_tokens":16000,"usage":{"include":True}}).encode()
    err=""
    for a in range(5):
        try:
            q=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",body,{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
            d=json.load(urllib.request.urlopen(q,timeout=900)); c=d["choices"][0]
            return i,{"task":hold[i]["task"],"output":c["message"]["content"] or "","finish":c["finish_reason"],"usage":d.get("usage")}
        except urllib.error.HTTPError as e: err=f"HTTP {e.code}"
        except Exception as e: err=str(e)[:80]
        time.sleep(10*2**a)
    return i,{"task":hold[i]["task"],"output":"","finish":"error:"+err,"usage":None}
with cf.ThreadPoolExecutor(4) as ex:
    for i,r in ex.map(call,todo): rows[i]=r
open(f,"w").write("".join(json.dumps(x)+"\n" for x in rows))
c=sum((r.get("usage") or {}).get("cost",0) or 0 for r in rows)
print(model,"rerun",len(todo),"still_err",sum(str(r['finish']).startswith('error') for r in rows),"total_cost_file",round(c,4))
