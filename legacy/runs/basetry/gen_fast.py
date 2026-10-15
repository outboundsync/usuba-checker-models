import json,os,sys,threading,urllib.request,concurrent.futures as cf
model,out=sys.argv[1],sys.argv[2]
H=os.path.dirname(os.path.abspath(__file__))
hold=[json.loads(l) for l in open(H+'/../../data/holdout.jsonl')]
clean=[json.loads(l)["holdout_i"] for l in open(H+'/../../clean/holdout_clean.jsonl')]
lock=threading.Lock(); part=out+'.part'; open(part,'w').close()
def call(i):
    r=hold[i]; b={"model":model,"messages":r["messages"][:-1],"temperature":0,"max_tokens":16000,"usage":{"include":True},"provider":{"sort":"throughput"}}
    if any(k in model for k in ["qwen3.6","qwen3.8","gpt-oss"]): b["reasoning"]={"effort":"low","exclude":True}
    err=""
    for a in range(2):
        try:
            q=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",json.dumps(b).encode(),{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
            d=json.load(urllib.request.urlopen(q,timeout=240)); c=d["choices"][0]
            x={"i":i,"task":r["task"],"output":c["message"]["content"] or "","finish":c["finish_reason"],"usage":d.get("usage"),"provider":d.get("provider")}; break
        except Exception as e: err=str(e)
    else: x={"i":i,"task":r["task"],"output":"","finish":"error:"+err,"usage":None}
    with lock: open(part,'a').write(json.dumps(x)+"\n")
    return x
with cf.ThreadPoolExecutor(49) as ex: res=list(ex.map(call,clean))
open(out,"w").write("".join(json.dumps(x)+"\n" for x in res))
u=[x["usage"] or {} for x in res]
print("in",sum(x.get("prompt_tokens",0) for x in u),"out",sum(x.get("completion_tokens",0) for x in u),"cost_usd",round(sum(x.get("cost",0) or 0 for x in u),4),"errors",sum(x["finish"].startswith("error") for x in res),"len",sum(x["finish"]=="length" for x in res))
