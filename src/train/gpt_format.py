class GPTFormat:

    def __init__(self, complete, bos='', eos='', instruct_bos='', instruct_eos='', user_prompt=''):
        self.complete = str(complete).strip()
        self.bos = bos
        self.eos = eos
        self.instruct_bos = instruct_bos
        self.instruct_eos = instruct_eos
        self.user_prompt = str(user_prompt).strip()

    def gen_text(self):
        return f'{self.bos}{self.instruct_bos}{self.user_prompt}{self.instruct_eos}{self.complete}{self.eos}'


class LlamaFormat(GPTFormat):

    def __init__(self, complete, instruct_bos='### Instruction:', instruct_eos='  ### Response:', user_prompt=''):
        super().__init__(
            complete,
            bos='<s>',
            eos='</s>',
            instruct_bos=instruct_bos,
            instruct_eos=instruct_eos,
            user_prompt=user_prompt
            )


class LlamaChatFormat(LlamaFormat):

    def __init__(self, complete, sys_prompt='', user_prompt=''):
        sys_prompt = f'<<SYS>>\n{sys_prompt}\n<</SYS>>'
        self.inst_bos = '[INST]'
        self.inst_eos = '[/INST]'
        user_prompt = f'{sys_prompt}\n\n{user_prompt}'

        super().__init__(
            complete,
            instruct_bos=self.inst_bos,
            instruct_eos=self.inst_eos,
            user_prompt=user_prompt
            )

class GPTJFormat(GPTFormat):

    def __init__(self, complete, instruct_bos='### Instruction:', instruct_eos='  ### Response:', user_prompt=''):
        super().__init__(
            complete,
            bos='',
            eos='<|endoftext|>',
            instruct_bos=instruct_bos,
            instruct_eos=instruct_eos,
            user_prompt=user_prompt
            )
