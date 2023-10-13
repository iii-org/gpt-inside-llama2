#!/usr/bin/env python
# coding=utf-8
# Copyright 2023 The 資策會服創所 資料科技組. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pandas as pd
import networkx as nx

from transformers import AutoTokenizer
from sklearn.model_selection import train_test_split
from gpt_format import LlamaChatFormat, LlamaFormat, GPTJFormat

pd.options.mode.chained_assignment = None
trans_func = {
    'gpt-j': GPTJFormat,
    'llama': LlamaFormat,
    'llama-chat': LlamaChatFormat,
    }
 
def gen_training_df(data_list, max_len, ignore_error=False):
    """
    生成訓練數據的DataFrame
    """
    df = pd.DataFrame({'text': data_list})
    return df

def gen_dataset(dataset, test_rate, seed, max_len, ignore_error):
    X_train, X_test, _, _ = train_test_split(
        dataset,
        range(len(dataset)),
        test_size=test_rate,
        random_state=seed
        )

    train_df = gen_training_df(X_train, max_len, ignore_error)
    test_df = gen_training_df(X_test, max_len, ignore_error)
    return train_df, test_df


def process(data_path, test_rate, seed, data_format='gpt-j', output_dir='/dataset', max_len=2048, ignore_error=False):
    """
    處理數據並生成訓練集和測試集
    """
    qa_df = pd.read_excel(
        data_path,
        converters={'Q': str.strip, 'A': str.strip, 'REF': str.strip}
        )

    tokenizers = {
        'gpt-j': 'EleutherAI/gpt-j-6b',
        'llama': 'yentinglin/Taiwan-LLaMa-v1.0',
        'llama-chat': 'meta-llama/Llama-2-7b-chat-hf'
        }

    tokenizer = AutoTokenizer.from_pretrained(
        tokenizers[data_format],
        use_auth_token=os.getenv('HF_TOKEN'),
        legacy=False,
        use_fast=True
        )

    tokenizer.pad_token = tokenizer.eos_token

    ref_encode = tokenizer(qa_df['REF'].to_list(), max_length=int(max_len*0.8), truncation=True, padding=True, return_tensors="pt")
    qa_df['REF'] = tokenizer.batch_decode(ref_encode.input_ids, skip_special_tokens=True)

   
    dataset = qa_df.apply(lambda x: trans_func[data_format](x['A'], user_prompt=f'根據以下參考資料回答，{x["Q"]}\n參考資料:\n{x["REF"]}\n').gen_text(), axis=1)
    train_df, test_df = gen_dataset(dataset, test_rate, seed, max_len, ignore_error)
    
    dataset = qa_df.apply(lambda x: trans_func[data_format](x['A'], user_prompt=f'{x["Q"]}\n').gen_text(), axis=1)
    train_df_no_ref, test_df_no_ref = gen_dataset(dataset, test_rate, seed, max_len, ignore_error)
    
    train_df = pd.concat([train_df, train_df_no_ref], axis=0, ignore_index=True)
    test_df = pd.concat([test_df, test_df_no_ref], axis=0, ignore_index=True)
    
    sum_func = lambda text: len(tokenizer(
        text,
        max_length=int(max_len*0.8),
        truncation=True,
        padding=True,
        return_tensors="pt"
        ).input_ids[0])

    train_tokens = train_df['text'].apply(sum_func).sum()
    print('Total train tokens:', train_tokens)

    train_df.sample(frac=1.0).to_csv(os.path.join(output_dir, 'train.csv'))
    test_df.to_csv(os.path.join(output_dir, 'validation.csv'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str,
                        help='xlsx檔案儲存位置')
    parser.add_argument('--output_dir', type=str,
                        default='/dataset', help='用於訓練的txt檔案儲存資料夾位置')
    parser.add_argument('--test_rate', type=float, default=0.1,
                        help='需介於0～1之間的浮點數，表示取用多少資料作為驗證集資料')
    parser.add_argument('--seed', type=int, default=715,
                        help='亂數種子碼，只能輸入正整數')
    parser.add_argument('--max_len', type=int, default=2048,
                        help='單筆訓練資料的最大長度為何，取決於模型不同而不同，只能輸入大於0的正整數')
    parser.add_argument('--ignore_too_long', type=str, choices=['true', 'false'], default='false',
                        help='當單筆訓練資料長度超過最大上限時，是否忽略該筆訓練資料，只能填入true或false')
    parser.add_argument('--data_format', type=str, choices=['gpt-j', 'llama', 'llama-chat'], default='gpt-j',
                        help='訓練資料格式')

    args = parser.parse_args()
    ignore_error = True if args.ignore_too_long == 'true' else False
    process(args.data, args.test_rate, args.seed, args.data_format, args.output_dir, args.max_len, ignore_error)
