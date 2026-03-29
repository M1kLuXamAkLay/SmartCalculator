import json
import os
import logging
import shutil
from collections import defaultdict
from copy import deepcopy, copy
from pathlib import Path
from typing import Union, Any

from PIL import Image
from detectron2.config import get_cfg
from detectron2.config import CfgNode as CN
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.engine import (
    DefaultTrainer,
    default_argument_parser,
    default_setup,
    launch,
    DefaultPredictor,
)

from ..consts import MODEL_VERSION
from ..layout_parser import ElementType
from ..utils import (
    list2box,
    clipbox,
    box2list,
    read_img,
    save_layout_img,
    data_dir,
    select_device,
)
from .. import DocXLayoutParser
from .rcnn_vl import *
from .backbone import *

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)


def add_vit_config(cfg):
    """
    Add config for VIT.
    """
    _C = cfg

    _C.MODEL.VIT = CN()

    # CoaT model name.
    _C.MODEL.VIT.NAME = ""

    # Output features from CoaT backbone.
    _C.MODEL.VIT.OUT_FEATURES = ["layer3", "layer5", "layer7", "layer11"]

    _C.MODEL.VIT.IMG_SIZE = [224, 224]

    _C.MODEL.VIT.POS_TYPE = "shared_rel"

    _C.MODEL.VIT.DROP_PATH = 0.0

    _C.MODEL.VIT.MODEL_KWARGS = "{}"

    _C.SOLVER.OPTIMIZER = "ADAMW"

    _C.SOLVER.BACKBONE_MULTIPLIER = 1.0

    _C.AUG = CN()

    _C.AUG.DETR = False

    _C.MODEL.IMAGE_ONLY = True
    _C.PUBLAYNET_DATA_DIR_TRAIN = ""
    _C.PUBLAYNET_DATA_DIR_TEST = ""
    _C.FOOTNOTE_DATA_DIR_TRAIN = ""
    _C.FOOTNOTE_DATA_DIR_VAL = ""
    _C.SCIHUB_DATA_DIR_TRAIN = ""
    _C.SCIHUB_DATA_DIR_TEST = ""
    _C.JIAOCAI_DATA_DIR_TRAIN = ""
    _C.JIAOCAI_DATA_DIR_TEST = ""
    _C.ICDAR_DATA_DIR_TRAIN = ""
    _C.ICDAR_DATA_DIR_TEST = ""
    _C.M6DOC_DATA_DIR_TEST = ""
    _C.DOCSTRUCTBENCH_DATA_DIR_TEST = ""
    _C.DOCSTRUCTBENCHv2_DATA_DIR_TEST = ""
    _C.CACHE_DIR = ""
    _C.MODEL.CONFIG_PATH = ""

    # effective update steps would be MAX_ITER/GRADIENT_ACCUMULATION_STEPS
    # maybe need to set MAX_ITER *= GRADIENT_ACCUMULATION_STEPS
    _C.SOLVER.GRADIENT_ACCUMULATION_STEPS = 1


def setup(args):
    """
    Create configs and perform basic setups.
    """
    cfg = get_cfg()
    cfg.MODEL.RPN.CONV_DIMS = [-1]
    # add_coat_config(cfg)
    add_vit_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.2  # set threshold for this model
    cfg.merge_from_list(args.opts)
    cfg.freeze()
    default_setup(cfg, args)

    register_coco_instances(
        "scihub_train",
        {},
        cfg.SCIHUB_DATA_DIR_TRAIN + ".json",
        cfg.SCIHUB_DATA_DIR_TRAIN,
    )

    return cfg


class DotDict(dict):
    def __init__(self, *args, **kwargs):
        super(DotDict, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        if key not in self.keys():
            return None
        value = self[key]
        if isinstance(value, dict):
            value = DotDict(value)
        return value

    def __setattr__(self, key, value):
        self[key] = value


# see: https://github.com/opendatalab/PDF-Extract-Kit/issues/19
CATEGORY_MAPPING = [
    "title",
    "plain text",
    "abandon",  # 包括页眉页脚页码和页面注释
    "figure",
    "figure caption",
    "table",
    "table caption",
    "table footnote",  # 表格注释
    "isolate formula",  # 行间公式（这个是layout的行间公式，优先级低于14）
    "formula caption",  # 行间公式的标号
    "unknown-1",
    "unknown-2",
    "unknown-3",
    "inline formula",
    "isolated formula",
    "ocr text",  # ocr识别结果
]


class LayoutLMv3LayoutParser(object):
    ignored_types = {'abandon', 'table footnote'}
    type_mappings = {
        'title': ElementType.TITLE,
        'figure': ElementType.FIGURE,
        'plain text': ElementType.TEXT,
        'table': ElementType.TABLE,
        'table caption': ElementType.TEXT,
        'figure caption': ElementType.TEXT,
        'isolate formula': ElementType.FORMULA,
        'isolated formula': ElementType.FORMULA,
        'inline formula': ElementType.FORMULA,
        'formula caption': ElementType.TEXT,
        'ocr text': ElementType.TEXT,
    }
    # types that are isolated and usually don't cross different columns. They should not be merged with other elements
    is_isolated = {'table caption', 'figure caption', 'isolated formula'}

    def __init__(
        self,
        device: str = None,
        model_fp: Optional[str] = None,
        root: Union[str, Path] = data_dir(),
        **kwargs,
    ):
        if model_fp is None:
            model_fp = self._prepare_model_files(root)
        device = select_device(device)
        # The operator 'aten::upsample_bicubic2d.out' is not currently implemented for the MPS device.
        device = 'cpu' if device == 'mps' else device
        layout_args = {
            "config_file": os.path.join(CURRENT_DIR, "layoutlmv3_base_inference.yaml"),
            "resume": False,
            "eval_only": False,
            "num_gpus": 1,
            "num_machines": 1,
            "machine_rank": 0,
            "dist_url": "tcp://127.0.0.1:57823",
            "opts": ["MODEL.WEIGHTS", str(model_fp), "MODEL.DEVICE", device],
        }
        layout_args = DotDict(layout_args)

        cfg = setup(layout_args)
        self.mapping = [
            "title",
            "plain text",
            "abandon",
            "figure",
            "figure_caption",
            "table",
            "table_caption",
            "table_footnote",
            "isolate_formula",
            "formula_caption",
        ]
        MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).thing_classes = self.mapping
        self.predictor = DefaultPredictor(cfg)

    def _prepare_model_files(self, root):
        model_root_dir = Path(root).expanduser() / MODEL_VERSION
        model_dir = model_root_dir / 'layout-layoutlmv3'
        model_fp = model_dir / 'layout_LayoutLMv3.pth'
        if model_fp.exists():
            return model_fp
        if model_dir.exists():
            shutil.rmtree(str(model_dir))
        model_dir.mkdir(parents=True)
        download_cmd = f'huggingface-cli download --repo-type model --resume-download --local-dir-use-symlinks False breezedeus/pix2text-layout-layoutlmv3 --local-dir {model_dir}'
        os.system(download_cmd)
        if not model_fp.exists():  # download failed above
            if model_dir.exists():
                shutil.rmtree(str(model_dir))
            os.system('HF_ENDPOINT=https://hf-mirror.com ' + download_cmd)
        return model_fp

    @classmethod
    def from_config(cls, configs: Optional[dict] = None, device: str = None, **kwargs):
        configs = copy(configs or {})
        device = select_device(device)
        model_fp = configs.pop('model_fp', None)
        root = configs.pop('root', data_dir())
        configs.pop('device', None)

        return cls(device=device, model_fp=model_fp, root=root, **configs)

    def parse(
        self,
        img: Union[str, Path, Image.Image],
        table_as_image: bool = False,
        **kwargs,
    ) -> (List[Dict[str, Any]], Dict[str, Any]):
        """

        Args:
            img ():
            table_as_image ():
            **kwargs ():
              * save_debug_res (str): if `save_debug_res` is set, the directory to save the debug results; default value is `None`, which means not to save
              * expansion_margin (int): expansion margin

        Returns:

        """
        if isinstance(img, Image.Image):
            img0 = img.convert('RGB')
        else:
            img0 = read_img(img, return_type='Image')
        img = np.ascontiguousarray(np.array(img0))
        img = img[:, :, ::-1]  # RGB -> BGR

        img_height, img_width = img.shape[:2]
        page_layout_result = []
        outputs = self.predictor(img)
        boxes = outputs["instances"].to("cpu")._fields["pred_boxes"].tensor.tolist()
        labels = outputs["instances"].to("cpu")._fields["pred_classes"].tolist()
        scores = outputs["instances"].to("cpu")._fields["scores"].tolist()
        for bbox_idx in range(len(boxes)):
            page_layout_result.append(
                {
                    "type": CATEGORY_MAPPING[labels[bbox_idx]],
                    "position": list2box(*boxes[bbox_idx]),
                    "score": scores[bbox_idx],
                }
            )

        breakpoint()
        if page_layout_result:
            layout_out = fetch_column_info(page_layout_result, img_width)
            layout_out, column_meta = self._format_outputs(
                img_width, img_height, layout_out, table_as_image
            )
        else:
            layout_out, column_meta = [], {}

        debug_dir = None
        if kwargs.get('save_debug_res', None):
            debug_dir = Path(kwargs.get('save_debug_res'))
            debug_dir.mkdir(exist_ok=True, parents=True)
        if debug_dir is not None:
            with open(debug_dir / 'layout_out.json', 'w', encoding='utf-8') as f:
                json_out = deepcopy(layout_out)
                for item in json_out:
                    item['position'] = item['position'].tolist()
                    item['type'] = item['type'].name
                json.dump(
                    json_out, f, indent=2, ensure_ascii=False,
                )
        layout_out = DocXLayoutParser._merge_overlapped_boxes(layout_out)

        expansion_margin = kwargs.get('expansion_margin', 8)
        layout_out = DocXLayoutParser._expand_boxes(
            layout_out, expansion_margin, height=img_height, width=img_width
        )

        save_layout_fp = kwargs.get(
            'save_layout_res',
            debug_dir / 'layout_res.jpg' if debug_dir is not None else None,
        )
        if save_layout_fp:
            element_type_list = [t for t in ElementType]
            save_layout_img(
                img0,
                element_type_list,
                layout_out,
                save_path=save_layout_fp,
                key='position',
            )

        return layout_out, column_meta

    def _format_outputs(self, width, height, layout_out, table_as_image: bool):
        # 获取每一列的信息
        column_numbers = set([item['col_number'] for item in layout_out])
        column_meta = defaultdict(dict)
        for col_idx in column_numbers:
            cur_col_res = [item for item in layout_out if item['col_number'] == col_idx]
            mean_score = np.mean([item['score'] for item in cur_col_res])
            xmin, ymin, xmax, ymax = box2list(cur_col_res[0]['position'])
            for item in cur_col_res[1:]:
                cur_xmin, cur_ymin, cur_xmax, cur_ymax = box2list(item['position'])
                xmin = min(xmin, cur_xmin)
                ymin = min(ymin, cur_ymin)
                xmax = max(xmax, cur_xmax)
                ymax = max(ymax, cur_ymax)
            column_meta[col_idx]['position'] = clipbox(
                list2box(xmin, ymin, xmax, ymax), height, width
            )
            column_meta[col_idx]['score'] = mean_score

        final_out = []
        for box_info in layout_out:
            image_type = box_info['type']
            isolated = image_type in self.is_isolated
            if image_type in self.ignored_types:
                image_type = ElementType.IGNORED
            else:
                image_type = self.type_mappings.get(image_type, ElementType.UNKNOWN)
            if table_as_image and image_type == ElementType.TABLE:
                image_type = ElementType.FIGURE
            final_out.append(
                {
                    'type': image_type,
                    'position': clipbox(box_info['position'], height, width),
                    'score': box_info['score'],
                    'col_number': box_info['col_number'],
                    'isolated': isolated,
                }
            )

        return final_out, column_meta


def cal_column_width(layout_res, img_width):
    widths = [item['position'][1][0] - item['position'][0][0] for item in layout_res]
    if len(widths) <= 2:
        return min(widths + [img_width])
    return np.median(widths)


def locate_full_column(layout_res, col_width, img_width):
    # 找出跨列的模块
    for item in layout_res:
        cur_width = item['position'][1][0] - item['position'][0][0]
        if cur_width > col_width * 1.5 or cur_width > img_width * 0.7:
            item['category'] = 'full column'
            item['col_number'] = 0
        else:
            item['category'] = 'sub column'
            item['col_number'] = -1
    return layout_res


def fetch_column_info(layout_res, img_width):
    # 获取所有模块的横坐标范围
    layout_res.sort(key=lambda x: x['position'][0][0])

    col_width = cal_column_width(layout_res, img_width)
    layout_res = locate_full_column(layout_res, col_width, img_width)
    col_width = max(
        [
            item['position'][1][0] - item['position'][0][0]
            for item in layout_res
            if item['category'] == 'sub column'
        ]
    )

    # 分配模块到列中
    col_left = img_width
    cur_col = 1
    for info in layout_res:
        if info['category'] == 'full column':
            continue
        xmin, xmax = info['position'][0][0], info['position'][1][0]
        if col_left == img_width:
            col_left = xmin
        if xmin < col_left + col_width * 0.99 and xmax <= xmin + col_width * 1.02:
            info['col_number'] = cur_col
            col_left = min(col_left, xmin)
        else:
            cur_col += 1
            col_left = xmin
            info['col_number'] = cur_col
    logger.debug(f"Column number: {cur_col}, with column width: {col_width}")

    layout_res.sort(
        key=lambda x: (x['col_number'], x['position'][0][1], x['position'][0][0])
    )
    return layout_res
