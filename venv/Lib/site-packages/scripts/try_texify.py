# moved to app-juices:p2t/scripts/predict_latex.py
# coding: utf-8
import time
from texify.inference import batch_inference
from texify.model.model import load_model
from texify.model.processor import load_processor
from PIL import Image

model = load_model()
processor = load_processor()
# img = Image.open("docs/examples/mixed.jpg")  # Your image name here
img_fps = [
    # 'data/call_images_formula/2023-08-14_2023-08-20/call-7PWyE5SRT5WHoxT30HgnklLf-YulVGmI_3.jpg',
    # 'data/call_images/2023-08-14_2023-08-20/call-FOgHhf7nqSyPvfVHStn1EVzlKrm0jjCx.jpg',
    # 'data/call_images_formula/2023-08-14_2023-08-20/call-__A94VFOt0gK8WwZ1eYtjVPyqq1ZgYAD_0.jpg',
    # 'data/call_images_formula/2023-08-14_2023-08-20/call-b5tzqng30ICprcGgLAxUkPpCaBI4MYx2_2.jpg',
    # 'data/call_images/2023-08-14_2023-08-20/call-0zcJMhzMndrTDb2HFIHPUCi470qrihhQ.jpg',
    # 'data/call_images_formula/2023-08-14_2023-08-20/call-dRtAWTwTDNQJQdhntWSYWmU3QaF4VFnK_0.jpg',
    # 'data/call_images_formula/2023-08-14_2023-08-20/call-hS-gUgWvRPZ76fma5RgWcfY4LBBTWDVz_0.jpg',
    '/Users/king/Documents/WhatIHaveDone/Test/pix2text/data/call_images_formula/2023-08-14_2023-08-20/call-t-Rue5yGQ4p_UrEoqFc2Gj-HW9kVsyrZ_23.jpg',
    '/Users/king/Documents/WhatIHaveDone/Test/apps-juice/p2t/out.jpg',
]
# img = Image.open("data/call_images/2023-08-14_2023-08-20/call-AczkIZ-vIHzpyt_lWllmUKKo3KDHNocy.jpg")  # Your image name here
img_list = [Image.open(fp) for fp in img_fps]
start_time = time.time()
results = batch_inference(img_list, model, processor)
end_time = time.time()
print("time:", end_time - start_time)
print('\n\n'.join(results))
