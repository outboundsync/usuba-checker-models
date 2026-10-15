import json,os,sys,urllib.request,concurrent.futures as cf
model,out=sys.argv[1],sys.argv[2]
rows=[json.loads(l) for l in open('/workspace/omarchy-specialist/runs/basetry/../../data/holdout.jsonl')]
def call(r):
    body=json.dumps({"model":model,"messages":r["messages"][:-1],"temperature":0,"max_tokens":16000,"usage":{"include":True}}).encode()
    for a in range(3):
        try:
            q=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",body,{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
            d=json.load(urllib.request.urlopen(q,timeout=900)); c=d["choices"][0]
            return {"task":r["task"],"output":c["message"]["content"] or "","finish":c["finish_reason"],"usage":d.get("usage")}
        except Exception as e: err=str(e)
    return {"task":r["task"],"output":"","finish":"error:"+err,"usage":None}
with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(call,rows))
open(out,"w").write("".join(json.dumps(x)+"\n" for x in res))
u=[x["usage"] or {} for x in res]
print("in",sum(x.get("prompt_tokens",0) for x in u),"out",sum(x.get("completion_tokens",0) for x in u),"cost_usd",round(sum(x.get("cost",0) or 0 for x in u),4),"errors",sum(x["finish"].startswith("error") for x in res))
