from unsloth import FastLanguageModel
import json,torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth.chat_templates import train_on_responses_only
MAX=24576
m,tok=FastLanguageModel.from_pretrained("unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",max_seq_length=MAX,load_in_4bit=True)
m=FastLanguageModel.get_peft_model(m,r=16,lora_alpha=16,lora_dropout=0,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],use_gradient_checkpointing="unsloth",random_state=0)
rows=[json.loads(l) for l in open("train.jsonl")]
ds=Dataset.from_list([{"text":tok.apply_chat_template(r["messages"],tokenize=False)} for r in rows])
tr=SFTTrainer(model=m,tokenizer=tok,train_dataset=ds,args=SFTConfig(dataset_text_field="text",max_seq_length=MAX,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=2,learning_rate=2e-4,warmup_steps=5,lr_scheduler_type="cosine",logging_steps=1,optim="adamw_8bit",bf16=True,output_dir="out",save_strategy="no",report_to="none",seed=0,packing=False))
tr=train_on_responses_only(tr,instruction_part="<|im_start|>user\n",response_part="<|im_start|>assistant\n")
tr.train()
json.dump(tr.state.log_history,open("loss_log.json","w"),indent=1)
m.save_pretrained("adapter");tok.save_pretrained("adapter")
print("TRAIN_DONE",torch.cuda.max_memory_allocated()/1e9)
