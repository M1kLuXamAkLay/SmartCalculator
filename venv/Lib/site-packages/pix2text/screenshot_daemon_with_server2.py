# coding: utf-8
# Copyright (C) 2022, [Breezedeus](https://github.com/breezedeus).
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

# python -m pix2tex.api.run
# 也可以下调用命令在命令行调用开启的OCR服务：
# > curl -F image=@docs/examples/huochepiao.jpeg http://0.0.0.0:8000/ocr

import os
import time
import glob
import requests
from pprint import pformat

import pyperclip as pc
from PIL import Image
from pix2tex.cli import LatexOCR

from cnocr import ImageClassifier, CnOcr
from cnocr.utils import set_logger

# logging = set_logging(log_level='DEBUG')

# OCR_SERVICE_URL = os.getenv("CNOCR_SERVICE", 'http://0.0.0.0:8501/ocr')
# LATEX_SERVICE_URL = os.getenv("LATEX_SERVICE", 'http://127.0.0.1:8502/predict/')
SCREENSHOT_DIR = os.getenv(
    "SCREENSHOT_DIR", '/Users/king/Pictures/screenshot_from_xnip'
)
LATEX_MODEL = LatexOCR()
logger = set_logger('DEBUG')
categories = ('text', 'english', 'formula')
transform_configs = {'crop_size': [150, 450], 'resize_size': 160, 'resize_max_size': 1000, }
model_fp = './data/image-formula-text/image-clf-epoch=015-val-accuracy-epoch=0.9394-model.ckpt'
IMAGE_CLF = ImageClassifier(
    base_model_name='mobilenet_v2', categories=categories, transform_configs=transform_configs)
IMAGE_CLF.load(model_fp, 'cpu')

GENERAL_OCR = CnOcr()
ENGLISH_OCR = CnOcr(det_model_name='en_PP-OCRv3_det', rec_model_name='en_PP-OCRv3')


def ocr(image, image_type):
    ocr_model = ENGLISH_OCR if image_type == 'english' else GENERAL_OCR
    result = ocr_model.ocr(image)
    texts = [_one['text'] for _one in result]
    # logger.info(f'\tOCR results: {pformat(texts)}\n')
    result = '\n'.join(texts)
    return result


def latex(image):
    out = LATEX_MODEL(Image.open(image))
    return str(out)

# def latex(image):
#     r = requests.post(
#         LATEX_SERVICE_URL, files={'file': (image, open(image, 'rb'), 'image/png')},
#     )
#
#     return str(r.json())


def get_newest_fp_time(screenshot_dir):
    fn_list = glob.glob1(screenshot_dir, '*g')
    fp_list = [os.path.join(screenshot_dir, fn) for fn in fn_list]
    if not fp_list:
        return None, None
    fp_list.sort(key=lambda fp: os.path.getmtime(fp), reverse=True)
    return fp_list[0], os.path.getmtime(fp_list[0])


def recognize(screenshot_dir, delta_interval):
    while True:
        newest_fp, newest_mod_time = get_newest_fp_time(screenshot_dir)
        if (
            newest_mod_time is not None
            and time.time() - newest_mod_time < delta_interval
        ):
            logger.info(f'analyzing screenshot file {newest_fp}')
            image_type, result = _recognize_newest(newest_fp)
            logger.info('image type: %s, image text: %s', image_type, result)
            if result:
                pc.copy(result)
            write_html(newest_fp, image_type, result)
        time.sleep(1)


def _recognize_newest(newest_fp):
    res = IMAGE_CLF.predict_images([newest_fp])[0]
    logger.info('CLF Result: %s', res)
    image_type = res[0]
    if res[1] < 0.65 and res[0] == 'formula':
        image_type = 'text'
    if res[1] < 0.75 and res[0] == 'english':
        image_type = 'text'
    if image_type == 'formula':
        result = latex(newest_fp)
    else:
        result = ocr(newest_fp, image_type)

    return image_type, result


def write_html(newest_fp, image_type, text):
    html_str = """
<!DOCTYPE html>
<html>
  <head>
    <link
      rel="stylesheet"
      href="https://cindyjs.org/dist/v0.8/katex/katex.min.css"
    />
    <script
      type="text/javascript"
      src="https://cindyjs.org/dist/v0.8/katex/katex.min.js"
    ></script>
    <script
      type="text/javascript"
      src="https://cindyjs.org/dist/v0.8/webfont.js"
    ></script>
    <style>
      body {
        /* background-color: rgb(154, 183, 249); */
      }
      #latex {
        min-height: auto;
        margin-left: auto;
        margin-right: auto;
        width: 760px;
      }

      #textarea {
        margin-left: auto;
        margin-right: auto;
        display: block;
      padding: 16px;
        /* height: 200px; */
      }

      body {
        display: flex;
        flex-direction: column;
        align-items: center;
      }

      .img-container {
        max-width: 760px;
      }
      .img-container img {
        max-width: 100%
      }
            .row {
        display: flex;
        gap: 1em;
        width: 760px;
      }
      .row textarea {
        flex: 1;
      }
      .row .col {
        width: 80px;
        display: flex;
        flex-direction: column;
        gap: 0.5em;
      }

      .container {
        width: 760px;
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      .container .refresh {
        position: absolute;
        right: 0;
        top: 0;
        padding: 4px 8px;
      }
      .btn {
        font-size: 16px;
        padding: 4px 6px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        color: rgb(62, 59, 59)
      }
      .cp {
        background-color: #f07878;
      }
      .cpd {
        background-color:   #a7d797;
      }
      .cpdd {
        background-color: #74a7f9;
      }
    </style>
  </head>
  
  <body class="with-footer">
    <div class="container">
    <h2 align="center">待解析图片</h2>
    <div class="img-container">
    """
    html_str += fr'<img src="{newest_fp}" />' + '\n </div>'
    html_str += """
    <button class="refresh btn" onClick="document.location.reload()">🔄 刷新</button>
    </div>
    <hr />

    <h2 align="center">解析结果</h2>
    """
    html_str += fr'<b>Image Type: </b> <div style="background:#ff9900;font-weight:bolder"> {image_type} </div>' + '\n'

    if image_type == 'formula':
        html_str += '<div id="latex"></div>'

    html_str += """

    <hr>

    <div class="row">
      
    """

    html_str += '\n<textarea id="textarea" rows="10">' + fr"{text}" + '</textarea>'

    html_str += """
          <div class="col">
        <button class="btn cp" type="button" onclick="copyTex()">复制</button>
        <button class="btn cpd" type="button" onclick="copyTexD()">$复制$</button>
        <button class="btn cpdd" type="button" onclick="copyTexDD()">$$复制$$</button>
      </div>
    </div>


    <script type="text/javascript">
      const textarea = document.querySelector("#textarea");
      const render = () => {
        var elt = document.createElement("div");
        elt.id = "latex";
        try {
          katex.render(textarea.value, elt, { displayMode: "display" });
        } catch (err) {
          console.error(err);
        }
        document.body.replaceChild(elt, document.querySelector("#latex"));
      };

      textarea.onblur = render;
      render();
    </script>

    <script type="text/javascript">
      function copy(text) {
        navigator.permissions
          .query({ name: "clipboard-write" })
          .then((result) => {
            if (result.state == "granted" || result.state == "prompt") {
              navigator.clipboard.writeText(text).then(() => {
                /* do nothing */
              });
            }
          });
      }
      function copyTex() {
        const texText = document.querySelector("#textarea").textContent;
        copy(texText);
      }
      function copyTexD() {
        const texText = document.querySelector("#textarea").textContent;
        copy(`$${texText}$`);
      }
      function copyTexDD() {
        const texText = document.querySelector("#textarea").textContent;
        copy(`$$${texText}$$`);
      }
    </script>

    <script>
      (async function callApi() {
        const resp = await fetch('/api/ocr')
        const data = await resp.json()
        console.log(data)
      })()
    </script>
  </body>
</html>
    """

    with open('new_tex.html', 'w') as f:
        f.writelines(html_str)


if __name__ == '__main__':
    recognize(SCREENSHOT_DIR, 1.05)
