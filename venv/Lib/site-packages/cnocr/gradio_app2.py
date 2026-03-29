# coding: utf-8
# Copyright (C) 2023, [Breezedeus](https://github.com/breezedeus).
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os

import gradio as gr
from gradio_client import Client
import cv2
import numpy as np
from cnstd.utils import pil_to_numpy, imsave

from cnocr import CnOcr, DET_AVAILABLE_MODELS, REC_AVAILABLE_MODELS
from cnocr.utils import set_logger, draw_ocr_results, download


logger = set_logger()
HF_TOKEN = os.environ.get('HF_TOKEN')


def plot_for_debugging(rotated_img, one_out, box_score_thresh, crop_ncols, prefix_fp):
    import matplotlib.pyplot as plt
    import math

    rotated_img = rotated_img.copy()
    crops = [info['cropped_img'] for info in one_out]
    print('%d boxes are found' % len(crops))
    if len(crops) < 1:
        return
    ncols = crop_ncols
    nrows = math.ceil(len(crops) / ncols)
    fig, ax = plt.subplots(nrows=nrows, ncols=ncols)
    for i, axi in enumerate(ax.flat):
        if i >= len(crops):
            break
        axi.imshow(crops[i])
    crop_fp = '%s-crops.png' % prefix_fp
    plt.savefig(crop_fp)
    print('cropped results are save to file %s' % crop_fp)

    for info in one_out:
        box, score = info.get('position'), info['score']
        if score < box_score_thresh:  # score < 0.5
            continue
        if box is not None:
            box = box.astype(int).reshape(-1, 2)
            cv2.polylines(rotated_img, [box], True, color=(255, 0, 0), thickness=2)
    result_fp = '%s-result.png' % prefix_fp
    imsave(rotated_img, result_fp, normalized=False)
    print('boxes results are save to file %s' % result_fp)


def get_ocr_model(det_model_name, rec_model_name, det_more_configs):
    det_model_name, det_model_backend = det_model_name.split('::')
    rec_model_name, rec_model_backend = rec_model_name.split('::')
    return CnOcr(
        det_model_name=det_model_name,
        det_model_backend=det_model_backend,
        rec_model_name=rec_model_name,
        rec_model_backend=rec_model_backend,
        det_more_configs=det_more_configs,
    )


def visualize_naive_result(img, det_model_name, std_out, box_score_thresh):
    if len(std_out) < 1:
        # gr.Warning(f'未检测到文本！')
        return []
    img = pil_to_numpy(img).transpose((1, 2, 0)).astype(np.uint8)

    plot_for_debugging(img, std_out, box_score_thresh, 2, './streamlit-app')
    # gr.Markdown('## Detection Result')
    # if det_model_name == 'naive_det':
    #     gr.Warning('⚠️ Warning: "naive_det" 检测模型不返回文本框位置！')
    # cols = st.columns([1, 7, 1])
    # cols[1].image('./streamlit-app-result.png')
    #
    # st.subheader('Recognition Result')
    # cols = st.columns([1, 7, 1])
    # cols[1].image('./streamlit-app-crops.png')

    return _visualize_ocr(std_out)


def _visualize_ocr(ocr_outs):
    if len(ocr_outs) < 1:
        return
    ocr_res = []
    for out in ocr_outs:
        # cropped_img = out['cropped_img']  # 检测出的文本框
        ocr_res.append([out['score'], out['text']])
    return ocr_res


def visualize_result(img, ocr_outs):
    out_draw_fp = './streamlit-app-det-result.png'
    font_path = 'docs/fonts/simfang.ttf'
    if not os.path.exists(font_path):
        url = 'https://huggingface.co/datasets/breezedeus/cnocr-wx-qr-code/resolve/main/fonts/simfang.ttf'
        os.makedirs(os.path.dirname(font_path), exist_ok=True)
        download(url, path=font_path, overwrite=True)
    draw_ocr_results(img, ocr_outs, out_draw_fp, font_path)
    return out_draw_fp


PRIVATE_REC_MODELS = ['']


def recognize(
    det_model_name,
    rec_model_name,
    rotated_bbox,
    use_angle_clf,
    new_size,
    box_score_thresh,
    min_box_size,
    image_file,
):
    if True:
    # if rec_model_name in PRIVATE_REC_MODELS:
        client = Client(
            "https://breezedeus-cnocr-demo-private.hf.space/", hf_token=HF_TOKEN
        )
        result = client.predict(
            det_model_name,
            rec_model_name,
            rotated_bbox,
            use_angle_clf,
            new_size,
            box_score_thresh,
            min_box_size,
            image_file,
            fn_index=0,
        )
        return result

    img = Image.open(image_file).convert('RGB')
    det_more_configs = dict(rotated_bbox=rotated_bbox, use_angle_clf=use_angle_clf)
    ocr = get_ocr_model(det_model_name, rec_model_name, det_more_configs)

    ocr_out = ocr.ocr(
        img,
        return_cropped_image=True,
        resized_shape=new_size,
        preserve_aspect_ratio=True,
        box_score_thresh=box_score_thresh,
        min_box_size=min_box_size,
    )

    det_model_name, det_model_backend = det_model_name.split('::')
    if det_model_name == 'naive_det':
        out_texts = visualize_naive_result(
            img, det_model_name, ocr_out, box_score_thresh
        )
        return [
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value=out_texts, visible=True),
        ]
    else:
        out_img_path = visualize_result(img, ocr_out)
        return [
            gr.update(value=out_img_path, visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        ]


def main():
    det_models = list(DET_AVAILABLE_MODELS.all_models())
    det_models.append(('naive_det', 'onnx'))
    det_models.sort()
    det_models = [f'{m}::{b}' for m, b in det_models]

    all_models = list(REC_AVAILABLE_MODELS.all_models())
    all_models.sort()
    all_models = [f'{m}::{b}' for m, b in all_models]

    title = '开源Python OCR工具：'
    desc = (
        '<p style="text-align: center">详细说明参见：<a href="https://github.com/breezedeus/CnOCR" target="_blank">Github</a>；'
        '<a href="https://cnocr.readthedocs.io" target="_blank">在线文档</a>；'
        '欢迎加入 <a href="https://www.breezedeus.com/join-group" target="_blank">交流群</a>；'
        '作者：<a href="https://www.breezedeus.com" target="_blank">Breezedeus</a> ，'
        '<a href="https://github.com/breezedeus" target="_blank">Github</a> 。</p>'
    )

    with gr.Blocks() as demo:
        gr.Markdown(
            f'<h1 style="text-align: center; margin-bottom: 1rem;">{title} <a href="https://github.com/breezedeus/cnocr" target="_blank">CnOCR</a></h1>'
        )
        gr.Markdown(desc)
        with gr.Row(equal_height=False):
            with gr.Column(min_width=200, variant='panel', scale=1):
                gr.Markdown('### 模型设置')
                det_model_name = gr.Dropdown(
                    label='选择检测模型', choices=det_models, value='ch_PP-OCRv3_det::onnx',
                )

                rec_model_name = gr.Dropdown(
                    label='选择识别模型',
                    choices=all_models,
                    value='densenet_lite_136-fc::onnx',
                )

                gr.Markdown('### 检测参数')
                rotated_bbox = gr.Checkbox(label='是否检测带角度文本框', value=True)
                use_angle_clf = gr.Checkbox(label='是否使用角度预测模型校正文本框', value=False)
                new_size = gr.Slider(
                    label='resize 后图片（长边）大小', minimum=124, maximum=4096, value=768
                )
                box_score_thresh = gr.Slider(
                    label='得分阈值（低于阈值的结果会被过滤掉）', minimum=0.05, maximum=0.95, value=0.3
                )
                min_box_size = gr.Slider(
                    label='框大小阈值（更小的文本框会被过滤掉）', minimum=4, maximum=50, value=10
                )

            with gr.Column(scale=3, variant='compact'):
                gr.Markdown('### 选择待检测图片')
                image_file = gr.Image(label='', type="filepath", image_mode='RGB')
                sub_btn = gr.Button("Submit", variant="primary")
                out_image = gr.Image(label='识别结果', interactive=False, visible=False)
                naive_warn = gr.Markdown(
                    '**⚠️ Warning**: "naive_det" 检测模型不返回文本框位置！', visible=False
                )
                out_texts = gr.Dataframe(
                    headers=['得分', '文本'], label='识别结果', interactive=False, visible=False
                )
                sub_btn.click(
                    recognize,
                    inputs=[
                        det_model_name,
                        rec_model_name,
                        rotated_bbox,
                        use_angle_clf,
                        new_size,
                        box_score_thresh,
                        min_box_size,
                        image_file,
                    ],
                    outputs=[out_image, naive_warn, out_texts],
                )

    demo.queue(concurrency_count=4)
    demo.launch()


if __name__ == '__main__':
    main()
