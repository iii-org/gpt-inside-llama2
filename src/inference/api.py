import os
import logging
import traceback
import numpy as np
import datetime as dt

from utils         import complete, cut_text, get_weights_location, get_model_max_len, count_tokens
from flask.views   import MethodView
from flask import jsonify, request
from environment   import app
from sentence_transformers import util


def error_message(message, status_code):
    error = jsonify({'status': 'error', 'message': message})
    error.status_code = status_code
    return error

def search_reference(query, ref_threshold):
    reference = app.config['REF_DATA']
    bi_encoder = app.config['ENCODER']
    cross_encoder = app.config['CROSS_ENCODER']
    question_embedding = bi_encoder.encode(query, convert_to_tensor=True)
    question_embedding = question_embedding.cuda()

    hits = util.semantic_search(question_embedding, list(reference['embeddings'].iloc), top_k=128)
    hits = hits[0]

    cross_inp = [[query, reference['REF'].iloc[hit['corpus_id']]]for hit in hits]
    cross_scores = cross_encoder.predict(cross_inp)

    for idx in range(len(cross_scores)):
        hits[idx]['cross-score'] = cross_scores[idx]

    hits = sorted(hits, key=lambda x: x['cross-score'], reverse=True)

    if hits[0]['cross-score'] > ref_threshold:
        result = reference.iloc[hits[0]['corpus_id']]
        return result['REF'], hits[0]['cross-score']
    return None, hits[0]['cross-score']

class TextGenerationAPI(MethodView):

    def post(self):
        req_start_time = dt.datetime.now()
        if not request.is_json:
            return error_message('[Error Message] POST body must be a JSON format', 400)

        try:
            logger = logging.getLogger('chat_logger')
            req_data = request.get_json()
            user_input = req_data.get('user_input')
            ref_threshold = req_data.get('ref_threshold', 0)
            semantic_search = req_data.get('semantic_search', True)
            reference = req_data.get('reference')
            do_sample=req_data.get('do_sample', True)
            temperature = float(req_data.get('temperature', 0.9))
            top_p = float(req_data.get('top_p', 1.0))
            top_k = int(req_data.get('top_k', 10))
            rep = float(req_data.get('repetition_penalty', 1.2))
            gen_tokens = int(req_data.get('gen_tokens', 512))

            formatter = app.config['FORMATTER']
            weights_location = get_weights_location(os.getenv('GPT_MODEL_NAME_OR_DIR'))

            if not user_input:
                raise Exception('"user_input" can not be empty.')

            result = None
            prompt = None
            if reference:
                reference = cut_text(weights_location, reference)
                prompt = formatter(f"根據以下參考資料並以台灣繁體中文回答，{user_input}\n參考資料:\n{reference}\n\n").gen_text()
                ref_data, ref_score = reference, 1.0
            elif semantic_search and app.config['REF_DATA'] is not None:
                ref_data, ref_score = search_reference(user_input, ref_threshold) if not reference else (reference, 1.0)
                if ref_data:
                    ref_data = cut_text(weights_location, ref_data)
                    prompt = formatter(f"根據以下參考資料並以台灣繁體中文回答，{user_input}\n參考資料:\n{ref_data}\n\n").gen_text()
                else:
                    result = '不好意思，我無法從參考資料中找到您需要的答案。'
            else:
                prompt = formatter(f"{user_input}\n").gen_text()
                ref_data, ref_score = None, 0.0

            max_tokens = get_model_max_len(weights_location)
            prompt_tokens = count_tokens(weights_location, prompt)

            if not result:
                result = complete(
                    app.config['GPT_MODEL'],
                    prompt,
                    inst_eos=formatter(None).instruct_eos,
                    do_sample=do_sample,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repetition_penalty=rep,
                    max_new_tokens=min(gen_tokens, max_tokens - prompt_tokens)
                    )
            result = app.config['CONVERTER'].convert(result)
            req_end_time = dt.datetime.now()
            resp = {
                '_status': 'success',
                '_time':(req_end_time - req_start_time).total_seconds(),
                'result': {
                    'Q': user_input,
                    'ref': ref_data,
                    'A': result if isinstance(result, list) else [result],
                    'prompt_tokens': prompt_tokens,
                    'gen_tokens': count_tokens(weights_location, result)
                    }}

            logger.info(f'"{resp["_time"]}", "{os.getenv("GPT_MODEL_NAME_OR_DIR")}", "{str(prompt)}", "{str(resp["result"]["A"][0])}", "{ref_score}", "{do_sample}", "{temperature}", "{top_p}", "{top_k}", "{rep}"')
            return jsonify(resp)
        except Exception as e:
            traceback.print_exc()
            return error_message('[Error Message] %s' % str(e), 500)

text_api = TextGenerationAPI.as_view('text-gen-api')
