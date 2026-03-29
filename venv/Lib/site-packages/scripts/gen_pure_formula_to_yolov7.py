# coding: utf-8
# 为纯公式的图片，生成训练YoloV7 MFD的格式
import os
import json
from glob import glob
from argparse import ArgumentParser


def bboxs_to_file(bboxs, out_fp):
    with open(out_fp, 'w') as f:
        for bbox in bboxs:
            bbox_str = ' '.join(map(str, bbox))
            f.write(f'{bbox_str}\n')


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-i',
        '--input_pure_image_dir',
        type=str,
        default='/data/jinlong/std_data/pure_formulas/images',
        help='dir within pure-formula images',
    )
    parser.add_argument(
        '-o',
        '--out_label_dir',
        type=str,
        default='/data/jinlong/std_data/pure_formulas/labels',
        help='label directory',
    )
    parser.add_argument(
        '--out_img_prefix',
        type=str,
        default='data/pure_formulas/images',
        help='output image prefix in train.txt',
    )
    parser.add_argument(
        '--out_img_list_fp',
        type=str,
        default='/data/jinlong/std_data/pure_formulas/train.txt',
        help='存储文件列表',
    )
    args = parser.parse_args()
    img_dir = args.input_pure_image_dir
    img_fp_list = glob('{}/*g'.format(img_dir), recursive=True)
    print(f'{len(img_fp_list)} images found in {img_dir}')
    label_root_dir = args.out_label_dir

    fp_list = []
    for fp in img_fp_list:
        fn = os.path.basename(fp)
        fp_list.append(os.path.join(args.out_img_prefix, fn))

        label_dir = os.path.join(label_root_dir)
        if not os.path.exists(label_dir):
            os.makedirs(label_dir)
        label_fp = os.path.join(label_dir, fn.rsplit('.', maxsplit=1)[0] + '.txt')

        label_infos = [[1, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]]
        bboxs_to_file(label_infos, label_fp)

    with open(args.out_img_list_fp, 'w') as f:
        for fp in fp_list:
            f.write(fp + '\n')


if __name__ == '__main__':
    main()
