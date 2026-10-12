import json,sys,torch,os
from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,DataCollatorForSeq2Seq
from peft import LoraConfig,get_peft_model
from datasets import Dataset
tag,lr,ep,cap=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),int(sys.argv[4])
B="Qwen/Qwen2.5-Coder-7B-Instruct"
tok=AutoTokenizer.from_pretrained(B); assert tok.pad_token_id!=tok.eos_token_id
rows=[json.loads(l) for l in open(os.environ.get("TRAIN","train.jsonl"))]
ex=[]
for r in rows:
  p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True)
  full=tok.apply_chat_template(r["messages"],tokenize=False)
  assert full.startswith(p)
  pi=tok(p,add_special_tokens=False).input_ids; ai=tok(full[len(p):],add_special_tokens=False).input_ids
  ids=pi+ai
  if len(ids)>cap: continue
  ex.append({"input_ids":ids,"attention_mask":[1]*len(ids),"labels":[-100]*len(pi)+ai})
e=ex[0]; lab=[x for x in e["labels"] if x!=-100]
print("N",len(ex),"of",len(rows),"label tail",repr(tok.decode(lab[-4:])),"eos in labels",tok.eos_token_id in lab,flush=True)
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16,attn_implementation="sdpa").cuda()
m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False}); m.enable_input_require_grads(); m.config.use_cache=False
m=get_peft_model(m,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],task_type="CAUSAL_LM"))
args=TrainingArguments(output_dir="out_"+tag,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=ep,learning_rate=lr,warmup_steps=5,lr_scheduler_type="cosine",logging_steps=1,bf16=True,save_strategy="no",report_to="none",seed=0,remove_unused_columns=False)
tr=Trainer(model=m,args=args,train_dataset=Dataset.from_list(ex),data_collator=DataCollatorForSeq2Seq(tok,padding=True))
tr.train()
json.dump(tr.state.log_history,open(f"loss_{tag}.json","w"),indent=1)
m.save_pretrained("adapter_"+tag); tok.save_pretrained("adapter_"+tag)
print("TRAIN_DONE",tag,torch.cuda.max_memory_allocated()/1e9,flush=True)
