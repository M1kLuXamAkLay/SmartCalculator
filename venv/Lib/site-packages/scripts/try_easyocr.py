# coding: utf-8
import easyocr

reader = easyocr.Reader(['ch_sim', 'en'])
result = reader.readtext('docs/examples/general.jpg')
print(result)

