# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
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
"""Testing suite for the PyTorch RecurrentGemma model."""

import unittest

import pytest

from transformers import AutoModelForCausalLM, AutoTokenizer, RecurrentGemmaConfig, is_torch_available, set_seed
from transformers.testing_utils import (
    require_bitsandbytes,
    require_read_token,
    require_torch,
    require_torch_accelerator,
    slow,
    torch_device,
)

from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, ids_tensor
from ...test_pipeline_mixin import PipelineTesterMixin


if is_torch_available():
    import torch

    from transformers import RecurrentGemmaForCausalLM, RecurrentGemmaModel


class RecurrentGemmaModelTester:
    def __init__(
        self,
        parent,
        batch_size=13,
        seq_length=12,
        is_training=True,
        use_input_mask=True,
        use_token_type_ids=False,
        use_labels=True,
        num_hidden_layers=3,
        vocab_size=99,
        hidden_size=32,
        intermediate_size=3 * 32,
        num_attention_heads=2,
        lru_width=2 * 32,
        embeddings_scale_by_sqrt_dim=True,
        attention_window_size=16,
        conv1d_width=4,
        logits_soft_cap=30.0,
        rms_norm_eps=1e-6,
        use_cache=True,
        rope_theta=10000.0,
        type_vocab_size=16,
        type_sequence_label_size=2,
        num_labels=3,
        num_choices=4,
        pad_token_id=0,
        scope=None,
    ):
        self.parent = parent
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.is_training = is_training
        self.use_input_mask = use_input_mask
        self.use_token_type_ids = use_token_type_ids
        self.use_labels = use_labels

        self.num_hidden_layers = num_hidden_layers
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.num_attention_heads = num_attention_heads
        self.lru_width = lru_width if lru_width is not None else hidden_size
        self.embeddings_scale_by_sqrt_dim = embeddings_scale_by_sqrt_dim
        self.attention_window_size = attention_window_size
        self.conv1d_width = conv1d_width
        self.logits_soft_cap = logits_soft_cap
        self.rms_norm_eps = rms_norm_eps
        self.use_cache = use_cache
        self.rope_theta = rope_theta

        self.type_vocab_size = type_vocab_size
        self.type_sequence_label_size = type_sequence_label_size
        self.num_labels = num_labels
        self.num_choices = num_choices
        self.pad_token_id = pad_token_id
        self.scope = scope

    # Copied from tests.models.mistral.test_modeling_mistral.MistralModelTester.prepare_config_and_inputs
    def prepare_config_and_inputs(self):
        input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

        input_mask = None
        if self.use_input_mask:
            input_mask = torch.tril(torch.ones_like(input_ids).to(torch_device))

        token_type_ids = None
        if self.use_token_type_ids:
            token_type_ids = ids_tensor([self.batch_size, self.seq_length], self.type_vocab_size)

        sequence_labels = None
        token_labels = None
        choice_labels = None
        if self.use_labels:
            sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
            token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
            choice_labels = ids_tensor([self.batch_size], self.num_choices)

        config = self.get_config()

        return config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels

    def get_config(self):
        return RecurrentGemmaConfig(
            num_hidden_layers=self.num_hidden_layers,
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
            intermediate_size=self.intermediate_size,
            num_attention_heads=self.num_attention_heads,
            lru_width=self.lru_width,
            embeddings_scale_by_sqrt_dim=self.embeddings_scale_by_sqrt_dim,
            attention_window_size=self.attention_window_size,
            conv1d_width=self.conv1d_width,
            logits_soft_cap=self.logits_soft_cap,
            rms_norm_eps=self.rms_norm_eps,
            use_cache=self.use_cache,
            rope_theta=self.rope_theta,
            pad_token_id=self.pad_token_id,
            output_attentions=False,
        )

    # Copied from tests.models.llama.test_modeling_llama.LlamaModelTester.create_and_check_model with Llama->RecurrentGemma
    def create_and_check_model(
        self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        model = RecurrentGemmaModel(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask)
        result = model(input_ids)
        self.parent.assertEqual(result.last_hidden_state.shape, (self.batch_size, self.seq_length, self.hidden_size))

    # Copied from tests.models.llama.test_modeling_llama.LlamaModelTester.prepare_config_and_inputs_for_common with Llama->RecurrentGemma
    def prepare_config_and_inputs_for_common(self):
        config_and_inputs = self.prepare_config_and_inputs()
        (
            config,
            input_ids,
            token_type_ids,
            input_mask,
            sequence_labels,
            token_labels,
            choice_labels,
        ) = config_and_inputs
        inputs_dict = {"input_ids": input_ids, "attention_mask": input_mask}
        return config, inputs_dict


@require_torch
class RecurrentGemmaModelTest(ModelTesterMixin, PipelineTesterMixin, unittest.TestCase):
    all_model_classes = (RecurrentGemmaForCausalLM,) if is_torch_available() else ()
    # Doesn't run generation tests. TODO @gante not fully supported
    all_generative_model_classes = ()
    pipeline_model_mapping = (
        {
            "feature-extraction": RecurrentGemmaModel,
            "text-generation": RecurrentGemmaForCausalLM,
        }
        if is_torch_available()
        else {}
    )
    fx_compatible = False  # FIXME let's try to support this @ArthurZucker
    test_torchscript = False  # FIXME let's try to support this @ArthurZucker
    test_missing_keys = False
    test_model_parallel = False
    test_pruning = False
    test_head_masking = False  # RecurrentGemma does not have attention heads

    # Need to remove 0.9 in `test_cpu_offload`
    # This is because we are hitting edge cases with the causal_mask buffer
    model_split_percents = [0.5, 0.6]

    # TODO (ydshieh): Check this. See https://app.circleci.com/pipelines/github/huggingface/transformers/79245/workflows/9490ef58-79c2-410d-8f51-e3495156cf9c/jobs/1012146
    def is_pipeline_test_to_skip(
        self,
        pipeline_test_case_name,
        config_class,
        model_architecture,
        tokenizer_name,
        image_processor_name,
        feature_extractor_name,
        processor_name,
    ):
        return True

    def setUp(self):
        # We don't output attentions
        self.has_attentions = False
        self.model_tester = RecurrentGemmaModelTester(self)
        self.config_tester = ConfigTester(self, config_class=RecurrentGemmaConfig, hidden_size=37)

    def test_config(self):
        self.config_tester.run_common_tests()

    def test_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_model(*config_and_inputs)

    def test_model_various_embeddings(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        for type in ["absolute", "relative_key", "relative_key_query"]:
            config_and_inputs[0].position_embedding_type = type
            self.model_tester.create_and_check_model(*config_and_inputs)

    @unittest.skip(reason="RecurrentGemma only supports sdpa")
    def test_eager_matches_sdpa_generate(self):
        pass

    @unittest.skip(reason="RecurrentGemma does not return the cache")
    def test_contrastive_generate_low_memory(self):
        pass

    @unittest.skip(reason="RecurrentGemma does not return the cache")
    def test_contrastive_generate_dict_outputs_use_cache(self):
        pass

    @unittest.skip(reason="RecurrentGemma does not return the cache")
    def test_contrastive_generate(self):
        pass

    @unittest.skip(reason="SQRBound is known to have issues with gc")
    def test_training_gradient_checkpointing_use_reentrant_false(self):
        pass

    @unittest.skip(reason="Past key values are not returned")
    def test_prompt_lookup_decoding_matches_greedy_search(self):
        pass

    @unittest.skip(reason="Past key values are not returned")
    def test_model_parallelism(self):
        pass

    @unittest.skip(reason="Past key values are not returned")
    def test_model_parallel_beam_search(self):
        pass

    @pytest.mark.generate
    @unittest.skip(reason="Rely on `past_key_values` to crop the assistant pkv. Not supported")
    def test_assisted_decoding_matches_greedy_search(self):
        pass

    @unittest.skip(reason="RecurrentGemma's output different if you pad left or right. This is expected")
    def test_left_padding_compatibility(self):
        pass

    @pytest.mark.generate
    @unittest.skip(reason="Relies on `past_key_values` returned by the model. Not supported with recurrent gemma")
    def test_assisted_decoding_sample(self):
        pass

    @unittest.skip(reason="TODO @arthurzucker not super important and failing.")
    def test_initialization(self):
        pass


@require_torch_accelerator
@slow
class RecurrentGemmaIntegrationTest(unittest.TestCase):
    input_text = ["Hello I am doing", "Hi today"]
    input_long_text = ['<bos><s>Marseille, France (CNN)The French prosecutor leading an investigation into the crash of Germanwings Flight 9525 insisted Wednesday that he was not aware of any video footage from on board the plane. Marseille prosecutor Brice Robin told CNN that "so far no videos were used in the crash investigation." He added, "A person who has such a video needs to immediately give it to the investigators." Robin\'s comments follow claims by two magazines, German daily Bild and French Paris Match, of a cell phone video showing the harrowing final seconds from on board Germanwings Flight 9525 as it crashed into the French Alps. All 150 on board were killed. Paris Match and Bild reported that the video was recovered from a phone at the wreckage site. The two publications described the supposed video, but did not post it on their websites. The publications said that they watched the video, which was found by a source close to the investigation. "One can hear cries of \'My God\' in several languages," Paris Match reported. "Metallic banging can also be heard more than three times, perhaps of the pilot trying to open the cockpit door with a heavy object.  Towards the end, after a heavy shake, stronger than the others, the screaming intensifies. Then nothing." "It is a very disturbing scene," said Julian Reichelt, editor-in-chief of Bild online. An official with France\'s accident investigation agency, the BEA, said the agency is not aware of any such video. Lt. Col.']  # fmt: skip
    model_id = "google/recurrentgemma-2b"

    @require_read_token
    def test_2b_generate(self):
        EXPECTED_TEXTS = ['Hello I am doing a project on the topic of "The impact of the internet on the society" and I am looking for some information on the topic. I am looking for some information on the impact of the internet on the society. I am looking for some information on the impact of the internet on the society. I am looking for some', 'Hi today is a new app that allows you to make money by watching videos.\n\nThe app is very simple to use and you can earn money by watching videos.\n\nThe app is available for both Android and iOS devices and you can download it from the Google Play Store or the App Store.\n\nOnce you have downloaded the app']  # fmt: skip
        model = AutoModelForCausalLM.from_pretrained(self.model_id, low_cpu_mem_usage=True).to(torch_device)

        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        tokenizer.padding_side = "right"

        inputs = tokenizer(self.input_text, return_tensors="pt", padding=True).to(torch_device)

        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        output_text = tokenizer.batch_decode(output, skip_special_tokens=True)

        self.assertEqual(output_text, EXPECTED_TEXTS)

        tokenizer.padding_side = "left"
        EXPECTED_TEXTS = ['Hello I am doing a project on the topic of "The impact of the internet on the society" and I am looking for some information on the topic. I am looking for some information on the impact of the internet on the society. I am looking for some information on the impact of the internet on the society. I am looking for some', 'Hi today I’m going to show you how to make a simple and easy to make a <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY</strong> <strong>DIY']  # fmt: skip

        inputs = tokenizer(self.input_text, return_tensors="pt", padding=True).to(torch_device)
        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        del model
        output_text = tokenizer.batch_decode(output, skip_special_tokens=True)

        self.assertEqual(output_text, EXPECTED_TEXTS)

        model = AutoModelForCausalLM.from_pretrained(
            self.model_id, low_cpu_mem_usage=True, torch_dtype=torch.float16
        ).to(torch_device)
        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        del model
        output_text = tokenizer.batch_decode(output, skip_special_tokens=True)
        self.assertEqual(output_text, EXPECTED_TEXTS)

    @require_read_token
    def test_2b_sample(self):
        set_seed(0)
        EXPECTED_TEXT = ['Where is Paris ?\n\nChoose the word or phrase that is closest in meaning to the word in capital letters.\n\nREDEEM\n(A) sort out\n(B) think over\n(C) turn in\n(D) take back\n\nWrite the correct word in the space next to each definition. Use each word only once.\n\nto badly damage\n\nOn the lines provided below, write <em>P</em> if the underlined word group is a phrase and <em>NP</em> if it is not a phrase. Example $\\underline{\\text{P}}$ 1. We have finally discovered the secret $\\underline{\\text{of delicious pizza. }}$']  # fmt: skip
        model = AutoModelForCausalLM.from_pretrained(self.model_id).to(torch_device)

        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        inputs = tokenizer("Where is Paris ?", return_tensors="pt", padding=True).to(torch_device)
        output = model.generate(**inputs, max_new_tokens=128, do_sample=True)
        output_text = tokenizer.batch_decode(output, skip_special_tokens=True)

        self.assertEqual(output_text, EXPECTED_TEXT)

    @require_bitsandbytes
    @require_read_token
    def test_model_2b_8bit(self):
        EXPECTED_TEXTS = ['Hello I am doing a project on the topic of "The impact of the internet on the society" and I am looking', "Hi today I'm going to show you how to make a simple and easy to make a simple and easy"]  # fmt: skip

        model = AutoModelForCausalLM.from_pretrained(
            "gg-hf/recurrent-gemma-2b-hf", device_map={"": torch_device}, load_in_8bit=True, torch_dtype=torch.bfloat16
        )

        tokenizer = AutoTokenizer.from_pretrained(self.model_id, padding_side="left")
        inputs = tokenizer(self.input_text, return_tensors="pt", padding=True).to(torch_device)

        output = model.generate(**inputs, max_new_tokens=20, do_sample=False)
        output_text = tokenizer.batch_decode(output, skip_special_tokens=True)

        self.assertEqual(output_text, EXPECTED_TEXTS)

    @require_read_token
    def test_long_context(self):
        EXPECTED_GENERATION = [' Jean-Paul Delannoy told CNN that the BEA is "not aware of any video footage that could have been taken on board the plane." He added that the BEA is "not aware of any video footage that could have been taken on board the plane." The BEA is the French equivalent of the National Transportation Safety Board']  # fmt: skip

        model = AutoModelForCausalLM.from_pretrained(
            self.model_id, low_cpu_mem_usage=True, torch_dtype=torch.float16
        ).to(torch_device)
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, padding_side="left")
        inputs = tokenizer(self.input_long_text, return_tensors="pt").to(torch_device)
        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        output_text = tokenizer.batch_decode(output[:, inputs.input_ids.shape[1] :], skip_special_tokens=True)
        print(output_text)
        self.assertEqual(output_text, EXPECTED_GENERATION)

    @require_read_token
    def test_longer_than_window(self):
        EXPECTED_GENERATION = [" Robin's comments follow claims by two magazines, German daily Bild and French Paris Match, of a cell phone video showing the harrowing final seconds from on board Germanwings Flight 9525 as it crashed into the French Alps. All 150 on board were killed. Paris Match and Bild reported that the"]  # fmt: skip

        model = AutoModelForCausalLM.from_pretrained(
            self.model_id, low_cpu_mem_usage=True, torch_dtype=torch.float16
        ).to(torch_device)
        model.config.attention_window_size = 256  # Make the attention window size shorter than the current prompt
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, padding_side="left")
        inputs = tokenizer(self.input_long_text, return_tensors="pt").to(torch_device)
        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        output_text = tokenizer.batch_decode(output[:, inputs.input_ids.shape[1] :], skip_special_tokens=True)
        self.assertEqual(output_text, EXPECTED_GENERATION)
