from PIL import Image, ImageDraw, ImageFont
import os
import random
import uuid

class FakeProofGenerator:
    def __init__(self, static_dir: str = "static"):
        self.static_dir = static_dir
        os.makedirs(self.static_dir, exist_ok=True)
        # Green background color for Google Pay success
        self.bg_color = "#00C853" 
        self.text_color = "white"

    def get_font(self):
        font_path = os.path.join(self.static_dir, "Roboto-Bold.ttf")
        if not os.path.exists(font_path):
            # Download a Google Font dynamically so it works on Azure/Linux
            try:
                import requests
                url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
                r = requests.get(url, allow_redirects=True)
                with open(font_path, 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                # Fallback to default if internet/write fails
                return None
        return font_path

    def generate_payment_proof(self, amount: str, receiver_upi: str) -> str:
        """Generates a fake GPay success screen and returns the filename."""
        
        width, height = 1080, 1920
        image = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(image)
        
        # Font Loading Logic
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        
        try:
            custom_font_path = self.get_font()
            if custom_font_path:
                font_large = ImageFont.truetype(custom_font_path, 80)
                font_medium = ImageFont.truetype(custom_font_path, 50)
            else:
                 # Try common system fonts if download failed
                try:
                    font_large = ImageFont.truetype("arial.ttf", 80)
                    font_medium = ImageFont.truetype("arial.ttf", 50)
                except IOError:
                    pass
        except Exception:
            pass

        # Draw "Payment Successful"
        draw.text((width//2 - 200, 400), "Payment Successful", fill=self.text_color, font=font_large)
        
        # Draw Amount
        draw.text((width//2 - 150, 600), f"₹{amount}", fill=self.text_color, font=font_large)
        
        # Draw Receiver
        draw.text((width//2 - 300, 800), f"To: {receiver_upi}", fill=self.text_color, font=font_medium)
        
        # Draw Transaction ID
        txn_id = "T" + str(uuid.uuid4().int)[:12]
        draw.text((width//2 - 300, 900), f"Txn ID: {txn_id}", fill=self.text_color, font=font_medium)

        # Save
        filename = f"proof_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(self.static_dir, filename)
        image.save(filepath)
        
        return filename
