from x_transformers.x_transformers import *
import torch.nn as nn

from ptls.data_load.padded_batch import PaddedBatch
from ptls.nn.seq_encoder.abs_seq_encoder import AbsSeqEncoder
from ptls.nn.seq_encoder.containers import SeqEncoderContainer

class XTransformerEncoder(nn.Module):
    '''
    Slightly modified version of TransformerWrapper from x-transformers
    '''
    def __init__(
        self,
        *,
        input_size,
        max_seq_len = None,
        attn_layers = None,
        num_memory_tokens = 1,
        return_last = False,
        post_emb_norm = False,
    ):
        super().__init__()
        assert isinstance(attn_layers, AttentionLayers), 'attention layers must be one of Encoder or Decoder'

        dim = attn_layers.dim
        emb_dim = dim

        self.input_linear = nn.Linear(input_size, dim) 

        self.post_emb_norm = nn.LayerNorm(emb_dim) if post_emb_norm else nn.Identity()
        self.attn_layers = attn_layers
        self.norm = nn.LayerNorm(dim)

        self.return_last = return_last

        # memory tokens (like [cls]) from Memory Transformers paper
        num_memory_tokens = default(num_memory_tokens, 0)
        self.num_memory_tokens = num_memory_tokens
        if num_memory_tokens > 0:
            self.memory_tokens = nn.Parameter(torch.randn(num_memory_tokens, dim))

    def forward(
        self,
        x,
        **kwargs
    ):
        x = x.payload
        b = x.shape[0]
        num_mem = self.num_memory_tokens

        x = self.input_linear(x)
        x = self.post_emb_norm(x)

        if num_mem > 0:
            mem = repeat(self.memory_tokens, 'n d -> b n d', b = b)
            x = torch.cat((mem, x), dim = 1)

        x = self.attn_layers(x, **kwargs)

        x = self.norm(x)

        mem, x = x[:, :num_mem], x[:, num_mem:]

        if self.return_last:
            return x[:,-1,:]

        return mem[:,0,:]

class XTransformerSeqEncoder(SeqEncoderContainer):
    """SeqEncoderContainer with TransformerEncoder

    Parameters
        trx_encoder:
            TrxEncoder object
        input_size:
            input_size parameter for TransformerEncoder
            If None: input_size = trx_encoder.output_size
            Set input_size explicit or use None if your trx_encoder object has output_size attribute
        **seq_encoder_params:
            params for TransformerEncoder initialisation
        is_reduce_sequence:
            False - returns PaddedBatch with all transactions embeddings
            True - returns one embedding for sequence based on CLS token

    """

    def __init__(self,
                 trx_encoder=None,
                 input_size=None,
                 is_reduce_sequence=True,
                 **seq_encoder_params,
                 ):
        super().__init__(
            trx_encoder=trx_encoder,
            seq_encoder_cls=XTransformerEncoder,
            input_size=input_size,
            seq_encoder_params=seq_encoder_params,
            is_reduce_sequence=is_reduce_sequence,
        )

    def forward(self, x):
        x = self.trx_encoder(x)
        x = self.seq_encoder(x)
        return x