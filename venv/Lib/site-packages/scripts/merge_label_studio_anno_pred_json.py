# coding: utf-8
# 合并标准和预测结果（json格式）的文件，生成新的json文件
from collections import OrderedDict
import json
from argparse import ArgumentParser


def read_json_fp(fp, content_type):
    content = json.load(open(fp))
    outs = OrderedDict()
    for info in content:
        key = info['data']['image']
        keeps = {'data': info['data'], content_type: info[content_type]}
        outs[key] = info
    return outs


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '--anno_json_fp', type=str, required=True, help='annotation json file'
    )
    parser.add_argument(
        '--pred_json_fp', type=str, required=True, help='prediction json file'
    )
    parser.add_argument(
        '-o',
        '--out_json_fp',
        type=str,
        default='annotation_prediction_results.json',
        help='output json file',
    )
    args = parser.parse_args()
    anno_dict = read_json_fp(args.anno_json_fp, 'annotations')
    print(f'{len(anno_dict)} annotations found in {args.anno_json_fp}')
    pred_dict = read_json_fp(args.pred_json_fp, 'predictions')
    print(f'{len(pred_dict)} predictions found in {args.pred_json_fp}')

    for key, pred_info in pred_dict.items():
        if key not in anno_dict:
            anno_dict[key] = pred_info
            continue
        anno_dict[key].update(pred_info)
    print(f'after merged, {len(anno_dict)} results kept')

    json.dump(
        list(anno_dict.values()),
        open(args.out_json_fp, 'w'),
        indent=2,
        ensure_ascii=False,
    )


if __name__ == '__main__':
    main()
