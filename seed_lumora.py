import psycopg2

# 🌟 حط رابط داتابيز ريلواي الخارجي هنا
DATABASE_URL = "postgresql://postgres:bhqPlGBITeuehgRNnwyPZspigxbbcMaV@reseau.proxy.rlwy.net:20529/railway"


if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

products_list = [
    "XQ Facial Cleanser 200ml",                        # هيأخد 0.jpeg
    "Kolagra Vit C Facial Cleanser 200ml",             # هيأخد 1.jpeg
    "Leylak Cleansing gel oily skin 200ml",            # هيأخد 2.jpeg
    "Starville Whitening cleanser 200ml",              # هيأخد 10.jpeg (حسب ترتيب الصور عندك)
    "Dear Facial Cleanser For Oily & Acne prone Skin 400ml", # 11.jpeg
    "Nuvera Sebio- control Cleaner 200ml",             # 12.jpeg
    "Moist-1 Foam Cleanser For oily 150ml",            # 13.jpeg
    "Starville Facial Cleanser gel 100ml",             # 14.jpeg
    "Nano treat oily skin cleanser 200ml",             # 15.jpeg
    "Moist-1 milky Cleanser",                          # 16.jpeg
    "Starville Whitening cleanser  100ml",             # 17.jpeg
    "Vacation Sebio Control Cleaning Gel 200ml",       # 18.jpeg
    "Shaan Facial Cleanser gel 250ml",                 # 19.jpeg
    "Starville Whitening cleanser 400ml",              # 20.jpeg
    "Tetra glow Whitening cleanser 200 ml",            # 21.jpeg
    "Kolanog Facial Cleanser dry skin 200ml",          # 22.jpeg
    "Feel Good Seba pure Cleaner 250ml",               # 23.jpeg
    "Dermactive acti - repair Soothing  Cleansing gel",# 24.jpeg
    "Starville Facial Cleanser gel 200ml",             # 25.jpeg
    "Dermactive acti - Clear Foaming gel 200ml"        # 26.jpeg
]

# خريطة لربط كل منتج برقم الصورة المقابل له بالظبط بناءً على أسماء ملفاتك
image_mapping = {
    0: "0.jpeg", 1: "1.jpeg", 2: "2.jpeg", 3: "10.jpeg", 4: "11.jpeg",
    5: "12.jpeg", 6: "13.jpeg", 7: "14.jpeg", 8: "15.jpeg", 9: "16.jpeg",
    10: "17.jpeg", 11: "18.jpeg", 12: "19.jpeg", 13: "20.jpeg", 14: "21.jpeg",
    15: "22.jpeg", 16: "23.jpeg", 17: "24.jpeg", 18: "25.jpeg", 19: "26.jpeg"
}

def seed():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return

    print("🧹 جاري تنظيف المنتجات القديمة من قسم Face...")
    cursor.execute("DELETE FROM products WHERE category = 'Face'")

    success_count = 0
    for index, prod in enumerate(products_list):
        # جلب اسم الصورة الرقمية الصحيحة من الـ mapping
        img_name = image_mapping.get(index, "placeholder.svg")
        img_path = f"/static/lumora/{img_name}"
        
        description = f"High quality {prod} for premium facial care."
        price = 0.0
        category = "Face"
        stock = 100
        
        try:
            cursor.execute(
                """INSERT INTO products (name, description, price, category, stock, image) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (prod, description, price, category, stock, img_path)
            )
            success_count += 1
            print(f"🔹 تم إدخال: {prod} -> {img_path}")
        except Exception as e:
            print(f"❌ خطأ مع ({prod}): {e}")
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n🎉 مبروك يا صاحبي! تم إدخال {success_count} منتج بنجاح، وكل منتج أخد صورته الرقمية المظبوطة.")

if __name__ == "__main__":
    seed()