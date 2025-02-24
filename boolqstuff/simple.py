import torchmetrics
from datasets import load_dataset
from pytorch_lightning.callbacks import TQDMProgressBar, EarlyStopping, ModelCheckpoint
from transformers import T5ForConditionalGeneration, AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import pandas as pd
import torch

from boolqstuff.BaseModules import prep_boolq_dataset, NO, YES
from boolqstuff.bert_modules import BoolQBertModule
from boolqstuff.t5_modules import MyLightningDataModule, MyLightningModel
import pytorch_lightning as pl
from argparse import ArgumentParser
import glob
import os
parser = ArgumentParser()
# add PROGRAM level args
# parser.add_argument("--conda_env", type=str, default="some_name")
# parser.add_argument("--notification_email", type=str, default="will@email.com")
# add model specific args
# parser = MyLightningModel.add_model_specific_args(parser)
# parser = pl.Trainer.add_argparse_args(parser)
parser.add_argument("--batch_size", default=8, type=int)
parser.add_argument("--max_epochs", default=2, type=int)
parser.add_argument("--num_classes", default=2, type=int)
parser.add_argument("--lr", default=1e-5, type=float)
parser.add_argument('--neg_sample', action='store_true')
parser.add_argument('--no-neg_sample', action='store_false')
parser.set_defaults(neg_sample=False)
parser.add_argument("--t_type", default="bert", type=str)
parser.add_argument("--resume_version", default=None, type=int)
parser.add_argument("--t_name", default="microsoft/deberta-base", type=str)
# parser.add_argument("--transformer-type", default="t5", type=str)
args = parser.parse_known_args()
# YES = "▁5.0"
# NO = "▁1.0"
# IRRELEVANT = "▁3.0"

MODEL_NAME = args[0].t_name
LR = args[0].lr
NUM_CLASSES = args[0].num_classes

# if args[0].resume_version!=None:
#     list_of_files = glob.glob(f'checkpoints/lightning_logs/version_{args[0].resume_version}/checkpoints/*.ckpt')  # * means all if need specific format then *.csv
#     resume_checkpoint = max(list_of_files, key=os.path.getctime)
#     print(f"resuming from version {args[0].resume_version}")
# else:
#     resume_checkpoint=None

# %%
if __name__ == '__main__':
    # %%

    def prep_t5_sentence(q, p):
        return f"boolq question: {q} passage: {p}"


    def prep_bert_sentence(q, p):
        return f"{q} [SEP] {p}"

    df_train, df_validation = prep_boolq_dataset(
        prep_sentence=prep_t5_sentence if args[0].t_type == "t5" else prep_bert_sentence,
        neg_sampling=args[0].neg_sample)

    weights = torch.tensor((1 / (df_train.target_class.value_counts() / df_train.shape[0]).sort_index()).to_list())
    weights = weights / weights.sum()
    # weights=torch.tensor([0.8, 0.2])
    # print(df_train.target_class.value_counts())
    # print(weights)
    # %%
    # df_validation = df_validation[:100]
    # df_train = df_train[:100]

    # %%

    BATCH_SIZE = args[0].batch_size
    source_max_token_len = 512
    target_max_token_len = 2
    dataloader_num_workers = 4
    early_stopping_patience_epochs = 0
    logger = "default"
    MAX_EPOCHS = args[0].max_epochs
    precision = 32
    # MODEL_BASE = "t5-base"
    CHECKPOINT_PATH = f"checkpoints/boolq-simple/{MODEL_NAME.split('/')[-1]}-num_class={NUM_CLASSES}-lr={args[0].lr}-batch_size={BATCH_SIZE}"
    # %%
    # num_classes = 2

    # tokenizer = AutoTokenizer.from_pretrained('roberta-base')
    # model = AutoModel.from_pretrained('roberta-base').to(0)

    # lightning_module = BertLightningModel(
    #     tokenizer=tokenizer,
    #     model=model,
    #     save_only_last_epoch=True,
    #     num_classes=3,
    #     train_metrics={
    #         "TAC": torchmetrics.Accuracy(num_classes=num_classes, multiclass=True),
    #     },
    #     val_metrics={
    #         "VAC": torchmetrics.Accuracy(num_classes=num_classes, multiclass=True),
    #         "VF1": torchmetrics.F1(num_classes=num_classes, multiclass=True)
    #     }
    # )

    # %%
    if args[0].t_type == "t5":
        tokenizer = AutoTokenizer.from_pretrained("t5-base")
        model = T5ForConditionalGeneration.from_pretrained("t5-base").to(0)

        lightning_module = MyLightningModel(
            tokenizer=tokenizer,
            model=model,
            save_only_last_epoch=True,
            num_classes=NUM_CLASSES,
            labels_text=[NO, IRRELEVANT, YES],
            train_metrics="Accuracy".split(),
            valid_metrics="Accuracy F1".split(),
            weights=weights
        )
    else:

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=NUM_CLASSES).to(0)
        # tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-TinyBERT-L6-v2")
        # model = AutoModelForSequenceClassification.from_pretrained("sentence-transformers/paraphrase-TinyBERT-L6-v2",
        #                                                            num_labels=num_classes).to(0)
        lightning_module = BoolQBertModule(
            tokenizer=tokenizer,
            model=model,
            save_only_last_epoch=True,
            num_classes=NUM_CLASSES,
            labels_text=[NO, IRRELEVANT, YES],
            train_metrics="Accuracy".split(),
            valid_metrics="Accuracy F1".split(),
            weights=weights,
            lr=LR
        )
        # lightning_module.load_from_checkpoint(
        #     "./checkpoints/lightning_logs/version_28266369/checkpoints/epoch=0-step=4713.ckpt",
        #     tokenizer=tokenizer,
        #     model=model,
        #     save_only_last_epoch=True,
        #     num_classes=num_classes,
        #     labels_text=[NO, IRRELEVANT, YES],
        #     train_metrics="Accuracy".split(),
        #     valid_metrics="Accuracy F1".split(),
        #     weights=weights
        # )

    # %%
    data_module = MyLightningDataModule(
        df_train,
        df_validation,
        tokenizer=tokenizer,
        batch_size=BATCH_SIZE,
        source_max_token_len=source_max_token_len,
        target_max_token_len=target_max_token_len,
        num_workers=dataloader_num_workers
    )
    callbacks = [TQDMProgressBar(refresh_rate=1)]
    # #
    # if early_stopping_patience_epochs > 0:
    #     early_stop_callback = EarlyStopping(
    #         monitor="val_loss",
    #         min_delta=0.00,
    #         patience=early_stopping_patience_epochs,
    #         verbose=True,
    #         mode="min",
    #     )
    #     callbacks.append(early_stop_callback)

    #         # add gpu support
    gpus = 1
    #
    #         # add logger
    loggers = True if logger == "default" else logger
    #
    #         # prepare trainer
    checkpoint_callback = ModelCheckpoint(
        monitor="valid_F1",
        filename="{epoch:02d}-{valid_F1:.3f}-{valid_Accuracy:.3f}",
        mode="max",
        dirpath=CHECKPOINT_PATH,
        every_n_epochs=1,
        save_top_k=2
    )
    callbacks.append(checkpoint_callback)


    trainer = pl.Trainer(
        logger=loggers,
        callbacks=callbacks,
        max_epochs=MAX_EPOCHS,
        gpus=gpus,
        precision=precision,
        log_every_n_steps=1,
        default_root_dir="checkpoints",
        enable_checkpointing=True,
    )
    #
    # # fit trainer
    # lightning_module.fix_stupid_metric_device_bs()
    trainer.fit(lightning_module, data_module, ckpt_path=None)
    # trainer.validate(lightning_module, data_module)

# %%

# %%
# a = "question: does ethanol take more energy make that produces passage: All biomass goes through at least some of these steps: it needs to be grown, collected, dried, fermented, distilled, and burned. All of these steps require resources and an infrastructure. The total amount of energy input into the process compared to the energy released by burning the resulting ethanol fuel is known as the energy balance (or ``energy returned on energy invested''). Figures compiled in a 2007 report by National Geographic Magazine point to modest results for corn ethanol produced in the US: one unit of fossil-fuel energy is required to create 1.3 energy units from the resulting ethanol. The energy balance for sugarcane ethanol produced in Brazil is more favorable, with one unit of fossil-fuel energy required to create 8 from the ethanol. Energy balance estimates are not easily produced, thus numerous such reports have been generated that are contradictory. For instance, a separate survey reports that production of ethanol from sugarcane, which requires a tropical climate to grow productively, returns from 8 to 9 units of energy for each unit expended, as compared to corn, which only returns about 1.34 units of fuel energy for each unit of energy expended. A 2006 University of California Berkeley study, after analyzing six separate studies, concluded that producing ethanol from corn uses much less petroleum than producing gasoline."

# %%
# import torch
# # model = T5ForConditionalGeneration.from_pretrained('t5-base').to(0)
# # tokenizer = AutoTokenizer.from_pretrained("t5-base")
# encoder_outputs = model.encoder(tokenizer(a, return_tensors="pt").input_ids, return_dict=True, output_hidden_states=True)
# decoder_input_ids = torch.tensor([[model._get_decoder_start_token_id()]])
# generated = model.greedy_search(decoder_input_ids, encoder_outputs=encoder_outputs, return_dict_in_generate=True, output_scores=True)
# tokenizer.decode(generated[0][0])
# %%
# from transformers import PreTrainedModel
# import torch
# from typing import Union, Tuple
# DecodedOutput = Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]
#
# @torch.no_grad()
# def greedy_decode(model: PreTrainedModel,
#                   input_ids: torch.Tensor,
#                   length: int,
#                   attention_mask: torch.Tensor = None,
#                   return_last_logits: bool = True) -> DecodedOutput:
#     decode_ids = torch.full((input_ids.size(0), 1),
#                             model.config.decoder_start_token_id,
#                             dtype=torch.long).to(input_ids.device)
#     encoder_outputs = model.get_encoder()(input_ids, attention_mask=attention_mask)
#     next_token_logits = None
#     for _ in range(length):
#         model_inputs = model.prepare_inputs_for_generation(
#             decode_ids,
#             encoder_outputs=encoder_outputs,
#             past=None,
#             attention_mask=attention_mask,
#             use_cache=True)
#         outputs = model(**model_inputs)  # (batch_size, cur_len, vocab_size)
#         next_token_logits = outputs[0][:, -1, :]  # (batch_size, vocab_size)
#         decode_ids = torch.cat([decode_ids,
#                                 next_token_logits.max(1)[1].unsqueeze(-1)],
#                                dim=-1)
#     if return_last_logits:
#         return decode_ids, next_token_logits
#     return decode_ids
