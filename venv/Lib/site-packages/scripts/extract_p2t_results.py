# coding: utf-8
# 生成检测结果（json格式）文件，这个文件可以导入到label studio中，生成待标注的任务
#! pip install imagededup

import os
from collections import OrderedDict
from glob import glob
import json
from argparse import ArgumentParser
from pathlib import Path
import tqdm

from imagededup.methods import PHash

import cv2
from pix2text.utils import read_img
from pix2text import Pix2Text


def load_p2t_model(device):
    p2t = Pix2Text(
        text_config=dict(
            det_model_name='ch_PP-OCRv3_det',
            rec_model_name='densenet_lite_136-gru',
            rec_model_backend='pytorch',
        ),
        analyzer_config=dict(  # 声明 LayoutAnalyzer 的初始化参数
            model_name='mfd',
            model_type='yolov7',  # 表示使用的是 YoloV7 模型，而不是 YoloV7_Tiny 模型
            model_fp='/Users/king/.cnstd/1.2/analysis/mfd-yolov7-epoch224-20230613.pt',  # 注：修改成你的模型文件所存储的路径
        ),
        formula_config={
            'model_fp': '/Users/king/.pix2text/formula/p2t-mfr-20230702.pth'
        },  # 注：修改成你的模型文件所存储的路径
        device=device,
    )
    return p2t


def transform_bbox(xmin, ymin, xmax, ymax, img_h, img_w, cut_margin_h_w):
    def clamp(v, max_value):
        return max(min(v, max_value), 0)

    xmin, xmax = (
        clamp(xmin - cut_margin_h_w[1], img_w),
        clamp(xmax + cut_margin_h_w[1], img_w),
    )

    ymin, ymax = (
        clamp(ymin - cut_margin_h_w[0], img_h),
        clamp(ymax + cut_margin_h_w[0], img_h),
    )
    return xmin, ymin, xmax, ymax


def parse_key(x):
    _key = x['img_fp'].lower()
    fn = _key.rsplit('.', maxsplit=1)[0]
    fn, idx = fn.rsplit('_', maxsplit=1)
    idx = int(idx)
    return fn, idx

def save_to_file(data, save_path):
    data.sort(key=parse_key)
    json.dump(data, open(save_path, 'w'), indent=2, ensure_ascii=False)
    # with open(save_path, 'w') as f:
    #     for d in data:
    #         f.write('\t'.join(d) + '\n')


def deduplicate_images2(img_dir):
    phasher = PHash()
    # Generate encodings for all images in an image directory
    encodings = phasher.encode_images(image_dir=img_dir)
    # Find duplicates using the generated encodings
    duplicates = phasher.find_duplicates(encoding_map=encodings, scores=True)

    results = set()
    for _fn in duplicates:
        if isinstance(duplicates[_fn], list):
            results.add(_fn)
            for sim_fn, _score in duplicates[_fn]:
                duplicates[sim_fn] = None

    print(f'{len(results)} different images kept after deduplication')
    return [os.path.join(img_dir, _fn) for _fn in results]


def deduplicate_images(img_dir):
    def calculate_image_hash(image_path):
        # with open(img_fp, 'rb') as f:
        #     image_data = f.read()
        #     return hashlib.md5(image_data).hexdigest()
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)
        _, threshold = cv2.threshold(
            resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return sum([2 ** i for (i, v) in enumerate(threshold.flatten()) if v])

    img_fp_list = glob('{}/*g'.format(img_dir), recursive=True)
    print(f'{len(img_fp_list)} images found in {img_dir}')
    outs = OrderedDict()
    for img_fp in tqdm.tqdm(img_fp_list):
        img_hash = calculate_image_hash(img_fp)

        # 将特征值与文件名存储在字典中
        if img_hash not in outs:
            outs[img_hash] = img_fp
    print(f'{len(outs)} different images kept after deduplication')
    return list(outs.values())


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-i', '--img-dir', type=str, required=True, help='image directory'
    )
    parser.add_argument(
        '--cut-margin-h-w',
        type=str,
        default='6,4',
        help='`height,width`，切图时高度和宽度上保留的margin大小。',
    )
    parser.add_argument(
        '-d', '--device', type=str, choices=['cpu', 'gpu'], default='cpu', help='device'
    )
    parser.add_argument(
        '--out-text-images-dir', type=str, default='coin-year', help='切出来的文字图片所存储的目录',
    )
    parser.add_argument(
        '--out-formula-images-dir',
        type=str,
        default='coin-year',
        help='切出来的公式图片所存储的目录',
    )

    args = parser.parse_args()
    img_dir = args.img_dir
    out_text_img_dir = Path(args.out_text_images_dir)
    out_formula_img_dir = Path(args.out_formula_images_dir)
    if os.path.exists(out_text_img_dir):
        raise FileExistsError(f'{out_text_img_dir} exists, remove it first')
    os.makedirs(out_text_img_dir)
    if os.path.exists(out_formula_img_dir):
        raise FileExistsError(f'{out_formula_img_dir} exists, remove it first')
    os.makedirs(out_formula_img_dir)
    cut_margin_h_w = [int(v) for v in args.cut_margin_h_w.split(',')]

    p2t = load_p2t_model(args.device)

    img_fp_list = deduplicate_images2(img_dir)

    text_infos = []
    formula_infos = []
    for img_fp in tqdm.tqdm(img_fp_list):
        img0 = read_img(img_fp, return_type='Image')
        width, height = img0.size
        out = p2t(img0, resized_shape=608, embed_sep=('', ''), isolated_sep=('', ''))

        for idx, box_info in enumerate(out):
            xmin, ymin = box_info['position'][0, :]
            xmax, ymax = box_info['position'][2, :]
            if not box_info['text']:
                continue
            xmin, ymin, xmax, ymax = transform_bbox(
                xmin, ymin, xmax, ymax, height, width, cut_margin_h_w
            )
            if xmax - xmin <= 2 or ymax - ymin <= 4:
                continue
            _fn = os.path.basename(img_fp).rsplit('.', maxsplit=1)[0] + f'_{idx}.jpg'
            _out_dir = (
                out_text_img_dir if box_info['type'] == 'text' else out_formula_img_dir
            )
            img0.crop((xmin, ymin, xmax, ymax)).save(_out_dir / _fn)
            _saved_info = text_infos if box_info['type'] == 'text' else formula_infos
            _saved_info.append(
                {
                    'img_fp': os.path.join(os.path.basename(_out_dir), _fn),
                    'text': box_info['text'],
                }
            )

    save_to_file(text_infos, out_text_img_dir / 'labels.json')
    save_to_file(formula_infos, out_formula_img_dir / 'labels.json')
    print(f'{len(text_infos)} texts and {len(formula_infos)} formulas are saved.')


if __name__ == '__main__':
    main()
