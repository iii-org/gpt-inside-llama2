import os
import logging

from opencc import OpenCC
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from gpt_format import LlamaFormat, LlamaChatFormat, GPTJFormat
from utils import load_model, load_encoder, load_reference


bi_encoder, cross_encoder = load_encoder(os.getenv('BI_ENCODER'), os.getenv('CROSS_ENCODER'))
ref_data = load_reference(os.getenv('REF_DATA'), bi_encoder)
formaters = {
    'llama': LlamaFormat,
    'llama-chat': LlamaChatFormat,
    'gpt-j': GPTJFormat
}

def init_log():
    logger = logging.getLogger('chat_logger')
    logger.setLevel(logging.DEBUG)

    # 創建一個文件處理器，並設置日誌級別為DEBUG
    file_handler = logging.FileHandler('/chat_log/chat.log')
    file_handler.setLevel(logging.INFO)

    # 創建一個格式化器，以設置日誌消息的格式
    formatter = logging.Formatter('"%(asctime)s", %(message)s')
    file_handler.setFormatter(formatter)

    # 將文件處理器添加到Logger中
    logger.addHandler(file_handler)

init_log()
app = Flask(__name__)
csrf = CSRFProtect()

class Config(object):

    GPT_MODEL = load_model(os.getenv('GPT_MODEL_NAME_OR_DIR'))
    CONVERTER = OpenCC('s2twp')
    REF_DATA = ref_data
    ENCODER  = bi_encoder
    CROSS_ENCODER = cross_encoder
    FORMATTER = formaters[os.getenv('GPT_FORMAT_TYPE')]

app.config.from_object('environment.Config')
