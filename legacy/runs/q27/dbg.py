# Qwen3.6-27B LoRA SFT (bf16 base, r16 per v3), no-think template, EOS (<|im_end|>) in labels
import json,sys,torch,os,time
torch.backends.cuda.enable_cudnn_sdp(False)  # cuDNN SDPA graph failed on long seqs (mha_graph.execute) -> device assert
from transformers import AutoTokenizer,AutoModelForImageTextToText,Trainer,TrainingArguments,DataCollatorForSeq2Seq,TrainerCallback
from peft import LoraConfig,get_peft_model
from datasets import Dataset
lr,ep,cap=float(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3])
B="/root/base"
tok=AutoTokenizer.from_pretrained(B); assert tok.pad_token_id!=tok.eos_token_id,(tok.pad_token_id,tok.eos_token_id)
rows=[json.loads(l) for l in open("train_v3.jsonl")]
ex=[]
for r in rows:
  p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  full=tok.apply_chat_template(r["messages"],tokenize=False,enable_thinking=False)
  assert full.startswith(p),(p[-200:],full[len(p)-200:len(p)+50])
  pi=tok(p,add_special_tokens=False).input_ids; ai=tok(full[len(p):],add_special_tokens=False).input_ids
  if len(pi)+len(ai)>cap: continue
  ex.append({"input_ids":pi+ai,"attention_mask":[1]*(len(pi)+len(ai)),"labels":[-100]*len(pi)+ai})
lab=[x for x in ex[0]["labels"] if x!=-100]
print("N",len(ex),"of",len(rows),"prompt tail",repr(tok.decode(ex[0]["input_ids"][len(ex[0]["input_ids"])-len(lab)-12:len(ex[0]["input_ids"])-len(lab)])),"label tail",repr(tok.decode(lab[-4:])),"eos in labels",tok.eos_token_id in lab,"ntok",sum(len(e["input_ids"]) for e in ex),flush=True)
assert tok.eos_token_id in lab; mx=max(max(e["input_ids"]) for e in ex); print("max id",mx,"maxlen",max(len(e["input_ids"]) for e in ex)); assert mx<248320
m=AutoModelForImageTextToText.from_pretrained(B,dtype=torch.bfloat16,attn_implementation="flash_attention_2" if os.environ.get("FA","1")=="1" else "sdpa",device_map={"":0})
m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False}); m.enable_input_require_grads(); m.config.use_cache=False
tm=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|in_proj_qkv|in_proj_z|out_proj)"
m=get_peft_model(m,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,target_modules=tm,task_type="CAUSAL_LM"))
m.print_trainable_parameters()
class CB(TrainerCallback):
  t0=time.time()
  def on_log(self,a,s,c,logs=None,**k):
    el=time.time()-self.t0; eta=el/max(s.global_step,1)*(s.max_steps-s.global_step)
    open("progress.txt","w").write(f"step {s.global_step}/{s.max_steps} loss {logs.get('loss')} elapsed {el/60:.1f}m eta {eta/60:.1f}m\n")
args=TrainingArguments(output_dir="out",per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=ep,learning_rate=lr,warmup_steps=5,lr_scheduler_type="cosine",logging_steps=1,bf16=True,save_strategy="no",report_to="none",seed=0,remove_unused_columns=False)
tr=Trainer(model=m,args=args,train_dataset=Dataset.from_list(ex),data_collator=DataCollatorForSeq2Seq(tok,padding=True),callbacks=[CB()])

dl=tr.get_train_dataloader(); m.train()
for i,b in enumerate(dl):
  if i<262: continue
  if i>275: break
  b={k:v.cuda() for k,v in b.items()}
  L=b["input_ids"].shape[1]; nl=(b["labels"]!=-100).sum().item()
  print("MB",i,"len",L,"nlab",nl,"row", [j for j,e in enumerate(ex) if len(e["input_ids"])==L],flush=True)
  out=m(**b); out.loss.backward(); m.zero_grad(); print("ok",i,out.loss.item(),flush=True)
