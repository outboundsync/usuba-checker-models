from unsloth import FastLanguageModel
import json,torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth.chat_templates import train_on_responses_only
MAX=24576
m,tok=FastLanguageModel.from_pretrained("unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",max_seq_length=MAX,load_in_4bit=True)
tok.pad_token="<|endoftext|>"; IM=tok.convert_tokens_to_ids("<|im_end|>")
assert tok.pad_token_id!=IM and tok.eos_token_id==IM, (tok.pad_token_id,tok.eos_token_id)
m.config.pad_token_id=tok.pad_token_id; m.generation_config.eos_token_id=[IM,tok.convert_tokens_to_ids("<|endoftext|>")]
m=FastLanguageModel.get_peft_model(m,r=16,lora_alpha=16,lora_dropout=0,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],use_gradient_checkpointing="unsloth",random_state=0)
rows=[json.loads(l) for l in open("train.jsonl")]
texts=[tok.apply_chat_template(r["messages"],tokenize=False) for r in rows]
assert all(t.rstrip().endswith("<|im_end|>") for t in texts)
ds=Dataset.from_list([{"text":t} for t in texts])
tr=SFTTrainer(model=m,tokenizer=tok,train_dataset=ds,args=SFTConfig(dataset_text_field="text",max_seq_length=MAX,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=2,learning_rate=2e-4,warmup_steps=5,lr_scheduler_type="cosine",logging_steps=1,optim="adamw_8bit",bf16=True,output_dir="out2",save_strategy="no",report_to="none",seed=0,packing=False,padding_free=False,add_eos_token=False))
tr=train_on_responses_only(tr,instruction_part="<|im_start|>user\n",response_part="<|im_start|>assistant\n")
# verify the closing <|im_end|> of the assistant turn is a trained label
ok=0
for k in range(5):
    ex=tr.train_dataset[k]; ids=ex["input_ids"]; lab=ex["labels"]
    pos=[i for i,t in enumerate(ids) if t==IM]; last=pos[-1]
    print("ROW",k,"len",len(ids),"im_end positions",len(pos),"last im_end label",lab[last],"trained tokens",sum(l!=-100 for l in lab),flush=True)
    ok+=lab[last]==IM
assert ok==5,"EOS not trained"
tr.train()
json.dump(tr.state.log_history,open("loss_log2.json","w"),indent=1)
m.save_pretrained("adapter2");tok.save_pretrained("adapter2")
m.save_pretrained_merged("merged2",tok,save_method="merged_16bit")
print("TRAIN_DONE",torch.cuda.max_memory_allocated()/1e9,flush=True)
