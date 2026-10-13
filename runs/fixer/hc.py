import json,sys,re;sys.path.insert(0,'../../validator');from build_parse import parse
v=sys.argv[1]; only=[int(x) for x in sys.argv[2:]]
for l in open(v+'/rows.jsonl'):
  r=json.loads(l)
  if r['first_pass_round'] is None or (only and r['i'] not in only): continue
  x=r['rounds'][r['first_pass_round']]; fs=parse(x['output'])
  print('=====',v,r['i'],r['task'],'round',r['first_pass_round'],{k:len(c) for k,c in fs.items()})
  for k,c in fs.items():
    if k=='manifest.json': print(c[:400]); continue
    for ln in c.splitlines():
      if re.search(r'command|exec|moduleName|\.sh|\.py|resolvedUrl|Process|/usr|~/|HOME|setting\(|Commons\.|Theme|Style',ln): print('   ',k,'|',ln.strip()[:160])
