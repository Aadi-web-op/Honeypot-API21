import csv
import random

# 4 Specific Indian Scam Types per Blueprint
SCAM_TYPES = ["digital_arrest", "electricity_bill", "part_time_job", "wrong_upi"]

TEMPLATES = {
    "digital_arrest": [
        "This is CBI. A package with drugs was seized in your name. Digital arrest warrant issued. Call {phone} now.",
        "Mumbai Police: Your Aadhar is linked to money laundering. Virtual court hearing in 1 hour. Connect via Skype.",
        "TRAI Alert: Your mobile number will be disconnected in 2 hours due to illegal activities. Press 9.",
        "Customs Dept: Illegal parcel from Thailand detained. Pay penalty or face arrest. Contact Officer {name}.",
        "Cyber Crime Unit: FIR registered against you for cyber fraud. Join video call for verification instantly."
    ],
    "electricity_bill": [
        "Dear Consumer, your electricity power will be disconnected tonight at 9:30 PM. Bill not updated. Call {phone}.",
        "TNEB Bill Reminder: Payment failed. Supply disconnection notice issued. Pay immediately via this link: {url}",
        "MSEB Alert: Your meter needs update. Urgent action required to avoid power cut. Contact Officer.",
        "Electricity Dept: Previous bill amount pending. Pay Rs {amount} to avoid line cut. Click {url}",
        "Power Department: Urgent notice. Your connection is suspended due to non-payment. Call {phone}."
    ],
    "part_time_job": [
        "Work from home! Earn Rs {amount} daily by liking YouTube videos. No investment. WhatsApp {phone}.",
        "Amazon Hiring: Part-time job available. Salary Rs 5000/day. Just review products. Join Telegram: {url}",
        "Instagram Job: Like posts and earn money. Instant payment. Limited slots. Apply now.",
        "Flipkart Part Time: Earn 30k-50k/month. Simple task. Work 2 hours/day. Contact HR {name}.",
        "Online Data Entry Job. Daily payout. Register now and get Rs 500 bonus. Click {url}"
    ],
    "wrong_upi": [
        "Hi, I mistakenly sent Rs {amount} to your GPay. Please return it na. My daughter is in hospital.",
        "Sir, money wrongly credited to your account. I am a poor student. Please refund to {phone}.",
        "Did you receive Rs {amount}? It was for my mother's medicine. Please send it back.",
        "Wrong transfer! I sent money to your number by mistake. Please check and return.",
        "Hello, I sent money for school fees to your UPI. Please return, it's urgent."
    ]
}

def generate_row(scam_type):
    template = random.choice(TEMPLATES[scam_type])
    
    # Fill dynamic slots
    text = template.format(
        amount=str(random.randint(500, 50000)),
        url="http://bit.ly/" + str(random.randint(1000, 9999)),
        phone="+91 " + str(random.randint(7000000000, 9999999999)),
        name=random.choice(["Amit", "Rahul", "Priya", "Officer Sharma", "Inspector Patil"])
    )
    return text, scam_type

def main():
    with open("scam_dataset.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        
        # Balance dataset: 125 per class = 500 samples
        for stype in SCAM_TYPES:
            for _ in range(125):
                writer.writerow(generate_row(stype))
                
    print("Generated 500 samples in scam_dataset.csv with new categories.")

if __name__ == "__main__":
    main()
