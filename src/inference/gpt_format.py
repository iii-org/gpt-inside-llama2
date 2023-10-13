

class GPTFormat:

    def __init__(self, user_prompt, bos='', eos='', instruct_bos='', instruct_eos=''):
        self.complete = str(user_prompt).strip()
        self.bos = bos
        self.eos = eos
        self.instruct_bos = instruct_bos
        self.instruct_eos = instruct_eos
        self.user_prompt = str(user_prompt).strip()

    def gen_text(self):
        return f'{self.bos}{self.instruct_bos}{self.user_prompt}{self.instruct_eos}'


class LlamaFormat(GPTFormat):

    def __init__(self, user_prompt, instruct_bos='### Instruction:', instruct_eos='  ### Response:'):
        super().__init__(
            user_prompt,
            bos='<s>',
            eos='</s>',
            instruct_bos=instruct_bos,
            instruct_eos=instruct_eos
            )


class LlamaChatFormat(LlamaFormat):

    def __init__(self, user_prompt, sys_prompt=''):
        sys_prompt = f'<<SYS>>\n{sys_prompt}\n<</SYS>>'
        self.inst_bos = '[INST]'
        self.inst_eos = '[/INST]'
        user_prompt = f'{sys_prompt}\n\n{user_prompt}'

        super().__init__(
            user_prompt,
            instruct_bos=self.inst_bos,
            instruct_eos=self.inst_eos
            )

class GPTJFormat(GPTFormat):

    def __init__(self, user_prompt, instruct_bos='### Instruction:', instruct_eos='  ### Response:'):
        super().__init__(
            user_prompt,
            bos='',
            eos='<|endoftext|>',
            instruct_bos=instruct_bos,
            instruct_eos=instruct_eos
            )
