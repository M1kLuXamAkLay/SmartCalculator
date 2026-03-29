# coding=utf-8
import os
import dotenv

from pix2text.text_formula_ocr import VlmTextFormulaOCR

# Load environment variables from .env file
dotenv.load_dotenv()
    
def main():
    img_path = "docs/examples/ch_tra1.jpg" 
    
    vlm_text_formula_ocr = VlmTextFormulaOCR.from_config(
        model_name=os.getenv("GEMINI_MODEL"),
        api_key=os.getenv("GEMINI_API_KEY"),
        enable_spell_checker=False,
    )
    result = vlm_text_formula_ocr.recognize(img_path, resized_shape=768, return_text=False)
    
    # Print the result
    print("识别结果:")
    print(result)


if __name__ == "__main__":
    main()