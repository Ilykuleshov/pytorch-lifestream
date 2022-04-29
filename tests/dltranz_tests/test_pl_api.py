import torch
import pytorch_lightning as pl
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

from dltranz.data_preprocessing.pandas_preprocessor import PandasDataPreprocessor
from dltranz.seq_encoder import SequenceEncoder
from dltranz.models import Head
from dltranz.lightning_modules.emb_module import EmbModule
from dltranz.data_load.data_module.emb_data_module import train_data_loader, inference_data_loader


def test_train_inference():
    source_data = pd.read_csv(Path(__file__).parent / "age-transactions.csv")

    preprocessor = PandasDataPreprocessor(
        col_id='client_id',
        cols_event_time='trans_date',
        time_transformation='float',
        cols_category=["trans_date", "small_group"],
        cols_log_norm=["amount_rur"],
        cols_identity=[],
        print_dataset_info=False,
    )

    dataset = preprocessor.fit_transform(source_data)

    train, test = train_test_split(dataset, test_size=0.4, random_state=42)

    seq_encoder = SequenceEncoder(
        category_features=preprocessor.get_category_sizes(),
        numeric_features=[],
        trx_embedding_noize=0.003
    )

    head = Head(input_size=seq_encoder.embedding_size, use_norm_encoder=True)

    model = EmbModule(seq_encoder=seq_encoder, head=head)

    trainer = pl.Trainer(
        max_epochs=1,
        gpus=1 if torch.cuda.is_available() else 0
    )

    train_dl = train_data_loader(
        train,
        min_seq_len=5,
        seq_split_strategy='SampleSlices',
        split_count=5,
        split_cnt_min=5,
        split_cnt_max=20,
        num_workers=1,
        batch_size=4
    )

    trainer.fit(model, train_dl)

    test_dl = inference_data_loader(test, num_workers=1, batch_size=4)
    
    trainer.predict(model, test_dl)
