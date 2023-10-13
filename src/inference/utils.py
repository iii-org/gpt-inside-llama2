import os
import torch
import hashlib
import pandas as pd

from optimum.pipelines import pipeline
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from accelerate import init_empty_weights, load_checkpoint_and_dispatch


def get_weights_location(name):
    try:
        weights_location = snapshot_download(
            repo_id=name,
            local_dir=os.path.join('/model', name),
            ignore_patterns="*.safetensors*",
            use_auth_token=os.getenv('HF_TOKEN'))
    except:
        weights_location = name

    return weights_location

def load_model(name):
    weights_location = get_weights_location(name)
    if not os.path.exists(os.path.join('/model', name, 'config.json')):
        ori_name = 'yentinglin/Taiwan-LLaMa-v1.0'
        print(f'Load model "{name}" failed. Change to load default model "{ori_name}"')
        weights_location = get_weights_location(ori_name)

    config = AutoConfig.from_pretrained(weights_location, local_files_only=True)

    with init_empty_weights():
        model = AutoModelForCausalLM.from_config(
            config,
            torch_dtype=torch.bfloat16
            )

    model = load_checkpoint_and_dispatch(
        model,
        weights_location,
        device_map='sequential',
        no_split_module_classes=model._no_split_modules
        )
    tokenizer = AutoTokenizer.from_pretrained(name, padding=False, use_fast=True)
    return pipeline(
        task='text-generation',
        model=model,
        tokenizer=tokenizer,
        accelerator='bettertransformer'
        )

def get_model_max_len(weights_location):
    return AutoConfig.from_pretrained(weights_location).max_position_embeddings

def get_tokenizer(weights_location):
    tokenizer = AutoTokenizer.from_pretrained(
        weights_location,
        use_auth_token=os.getenv('HF_TOKEN'),
        legacy=False,
        use_fast=True
        )
    tokenizer.pad_token = tokenizer.eos_token
    return tokenizer

def count_tokens(weights_location, text):
    if text:
        text = text if isinstance(text, list) else [text]
        tokenizer = get_tokenizer(weights_location)
        return len(tokenizer(text, return_tensors="pt").input_ids[-1])
    else:
        return 0

def cut_text(weights_location, text):
    text = text if isinstance(text, list) else [text]
    max_len = get_model_max_len(weights_location)
    tokenizer = get_tokenizer(weights_location)
    ref_encode = tokenizer(text, max_length=int(max_len*0.75), truncation=True, padding=True, return_tensors="pt")
    return tokenizer.batch_decode(ref_encode.input_ids, skip_special_tokens=True)[0]

def complete(model, prompt, inst_eos='', **model_kwargs):
    with torch.no_grad():
        result = model(prompt, **model_kwargs)
    return result[0]['generated_text'].split(inst_eos)[-1].strip()

def load_encoder(bi_encoder_name, cross_encoder_name):
    bi_encoder = SentenceTransformer(bi_encoder_name)
    bi_encoder.max_seq_length = 512
    cross_encoder = CrossEncoder(cross_encoder_name)
    return bi_encoder, cross_encoder

def get_check_sum(file_path):
    hash_obj = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while True:
            data = file.read(65536)
            if not data:
                break
            hash_obj.update(data)

    return hash_obj.hexdigest()

def load_reference(ref_path, bi_encoder):
    try:
        ref_data = pd.read_excel(ref_path, usecols=['REF'])
    except:
        print('Can not find reference data. Set the semantic_search argument alaway is false!!!')
        return None

    check_sum = get_check_sum(ref_path)
    embd_file = os.path.join('/data/embeddings', check_sum+'.pt')
    try:
        embds = torch.load(embd_file).cpu()
        print(f'load embeddings from {embd_file}')
    except:
        print(f'encode reference data to embeddings')
        embds = bi_encoder.encode(ref_data['REF'].to_list(), convert_to_tensor=True).cpu()
        torch.save(embds, embd_file)
        print(f'save embeddings to {embd_file}')

    ref_data['embeddings'] = list(embds)
    return ref_data
