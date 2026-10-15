import json
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained("adapter")
r=json.loads(open("train.jsonl").readline())
t=tok.apply_chat_template(r["messages"],tokenize=False)
print("ENDS:",repr(t[-40:]),"eos",tok.eos_token,"pad",tok.pad_token,tok.pad_token_id,tok.eos_token_id)
ids=tok(t,add_special_tokens=False).input_ids
im=tok.convert_tokens_to_ids("<|im_end|>"); print("im_end count",ids.count(im),"last ids",ids[-3:])
