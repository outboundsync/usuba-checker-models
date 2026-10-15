from unsloth import FastLanguageModel
import json,torch,sys
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth.chat_templates import train_on_responses_only
LR=float(sys.argv[1]); CAP=int(sys.argv[2]); OUT=sys.argv[3]; MAX=CAP
m,tok=FastLanguageModel.from_pretrained("unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",max_seq_length=24576,load_in_4bit=True)
tok.pad_token="<|endoftext|>"; IM=tok.convert_tokens_to_ids("<|im_end|>"); assert tok.pad_token_id!=IM==tok.eos_token_id
m=FastLanguageModel.get_peft_model(m,r=16,lora_alpha=32,lora_dropout=0,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],use_gradient_checkpointing="unsloth",random_state=0)
rows=[json.loads(l) for l in open("train.jsonl")]
texts=[tok.apply_chat_template(r["messages"],tokenize=False) for r in rows]
keep=[t for t in texts if len(tok(t,add_special_tokens=False).input_ids)<=CAP]; print("KEPT",len(keep),"of",len(texts),flush=True)
tr=SFTTrainer(model=m,tokenizer=tok,train_dataset=Dataset.from_list([{"text":t} for t in keep]),args=SFTConfig(dataset_text_field="text",max_seq_length=MAX,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=1,learning_rate=LR,warmup_steps=3,lr_scheduler_type="cosine",logging_steps=1,optim="adamw_8bit",bf16=True,output_dir=OUT+"_o",save_strategy="no",report_to="none",seed=0,packing=False,padding_free=False))
tr=train_on_responses_only(tr,instruction_part="<|im_start|>user\n",response_part="<|im_start|>assistant\n")
ex=tr.train_dataset[0]; ids,lab=ex["input_ids"],ex["labels"]; last=max(i for i,t in enumerate(ids) if t==IM)
first=next(i for i,l in enumerate(lab) if l!=-100)
print("MASKCHK last_im_end_trained",lab[last]==IM,"masked_prefix",first,"first_trained_text",repr(tok.decode(ids[first:first+8])),"prefix_tail",repr(tok.decode(ids[first-4:first])),flush=True)
tr.train(); json.dump(tr.state.log_history,open(OUT+"_loss.json","w"),indent=1)
m.save_pretrained(OUT); tok.save_pretrained(OUT); print("TRAIN_DONE",flush=True)
