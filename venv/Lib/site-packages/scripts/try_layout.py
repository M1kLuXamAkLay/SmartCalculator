# coding: utf-8

from PIL import Image
import layoutparser as lp

# config_path = 'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config'  # In model catalog
# label_map = {
#     0: "Text",
#     1: "Title",
#     2: "List",
#     3: "Table",
#     4: "Figure",
# }  # In model`label_map`

# model = lp.Detectron2LayoutModel(
#     config_path=config_path,
#     label_map=label_map,
#     extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],  # Optional
# )

model = lp.AutoLayoutModel(
    "lp://efficientdet/MFD/tf_efficientdet_d1",
    model_path='mfd-tf_efficientdet_d1.pth.tar',
    extra_config={"output_confidence_threshold": 0.5},
)


image = Image.open('docs/examples/layout3.jpg')

out = model.detect(image)
print(out)

lp.draw_box(image, out, box_width=3).show()
# breakpoint()
