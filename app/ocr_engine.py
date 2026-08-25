import easyocr

class OCREngine:
    def __init__(self):
        # Initialize EasyOCR for English. 
        # gpu=False ensures it runs purely on CPU to avoid any hardware crashes.
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)

    def extract(self, frame):
        try:
            # EasyOCR natively accepts OpenCV/numpy frames
            # It returns a list of results in the format: (bbox, text, confidence)
            results = self.reader.readtext(frame)
            
            # Extract just the text from the results
            texts = [res[1] for res in results]
            
            return " ".join(texts)
        except Exception as e:
            print(f"OCR warning: {e}")
            return ""