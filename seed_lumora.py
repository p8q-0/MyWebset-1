import os
import sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import DictCursor

BASE_DIR = Path(__file__).resolve().parent

# 🌟 حط رابط الداتابيز الحقيقي بتاع ريلواي هنا بين القوسين 🌟
# (تلاقيه في حسابك على ريلواي في قسم الـ Variables أو الـ Connect ويكون بيبدأ بـ postgres:// أو postgresql://)
DATABASE_URL = "postgresql://postgres:bhqPlGBITeuehgRNnwyPZspigxbbcMaV@reseau.proxy.rlwy.net:20529/railway"

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# تحديد مسار قاعدة البيانات المحلية كخيار احتياطي فقط
DATA_DIR = BASE_DIR.parent / "MyWebset_data"
DATABASE_PATH = DATA_DIR / "database.sqlite"

# فولدر الصور اللي قولت لي عليه داخل المشروع
LUMORA_FOLDER = BASE_DIR / "lumora"

# قائمة المنتجات المطلوبة من قبلك
products_list = [
    "XQ Facial Cleanser 200ml",
    "Kolagra Vit C Facial Cleanser 200ml",
    "Leylak Cleansing gel oily skin 200ml",
    "Starville Whitening cleanser 200ml",
    "Dear Facial Cleanser For Oily & Acne prone Skin 400ml",
    "Nuvera Sebio- control Cleaner 200ml",
    "Moist-1 Foam Cleanser For oily 150ml",
    "Starville Facial Cleanser gel 100ml",
    "Nano treat oily skin cleanser 200ml",
    "Moist-1 milky Cleanser",
    "Starville Whitening cleanser  100ml",
    "Vacation Sebio Control Cleaning Gel 200ml",
    "Shaan Facial Cleanser gel 250ml",
    "Starville Whitening cleanser 400ml",
    "Tetra glow Whitening cleanser 200 ml",
    "Kolanog Facial Cleanser dry skin 200ml",
    "Feel Good Seba pure Cleaner 250ml",
    "Dermactive acti - repair Soothing  Cleansing gel",
    "Starville Facial Cleanser gel 200ml",
    "Dermactive acti - Clear Foaming gel 200ml"
]

def get_db_connection():
    # التحقق من وجود الرابط الصريح أولاً لتجنب التحويل التلقائي لـ SQLite
    if DATABASE_URL and "اكتب_رابط_داتابيز_ريلواي" not in DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        print("⚠️ لم يتم العثور على DATABASE_URL صريح، يتم الاتصال بقاعدة البيانات المحلية SQLite...")
        return sqlite3.connect(DATABASE_PATH)

def find_matching_image(product_name, am_files):
    # تنظيف اسم المنتج للمطابقة الذكية (مسح المسافات والرموز وتحويل الحروف لصغيرة)
    clean_name = "".join(c.lower() for c in product_name if c.isalnum())
    
    # لف على ملفات الصور داخل فولدر lumora لمعرفة الاسم المطابق
    for f in am_files:
        clean_file = "".join(c.lower() for c in Path(f).stem if c.isalnum())
        if clean_file in clean_name or clean_name in clean_file:
            # استخدام المسار النسبي الصحيح لـ lumora بناءً على هيكلة مشروعك
            return f"/lumora/{f}"
            
    # إذا لم يجد صورة مطابقة، يضع Placeholder مؤقتاً
    return "/static/images/placeholder.svg"

def seed():
    print("⏳ جاري قراءة الملفات والاتصال بقاعدة البيانات...")
    
    # جلب أسماء ملفات الصور من فولدر lumora
    images_in_folder = []
    if LUMORA_FOLDER.exists():
        images_in_folder = [f.name for f in LUMORA_FOLDER.iterdir() if f.is_file()]
        print(f"✅ تم العثور على {len(images_in_folder)} صورة داخل فولدر lumora")
    else:
        print("⚠️ تحذير: فولدر lumora غير موجود بجانب السكريبت، سيتم استخدام Placeholder للصور.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return

    # تحديد علامة الاستفهام بناءً على نوع الداتابيز (PostgreSQL تستخدم %s و SQLite تستخدم ?)
    is_postgres = hasattr(conn, 'encoding') or (DATABASE_URL and "اكتب_رابط_داتابيز_ريلواي" not in DATABASE_URL)
    param_char = "%s" if is_postgres else "?"

    success_count = 0
    for prod in products_list:
        img_path = find_matching_image(prod, images_in_folder)
        
        # إعداد الحقول الافتراضية المناسبة لـ Schema الخاص بمشروعك
        description = f"High quality {prod} for premium facial care."
        price = 0.0      # حط السعر اللي يعجبك كبداية
        category = "Face" # اسم الكاتوجري عشان ينزل تحت الـ Face علطول
        stock = 100       # الكمية المتاحة في المخزن
        
        try:
            cursor.execute(
                f"""INSERT INTO products (name, description, price, category, stock, image) 
                   VALUES ({param_char}, {param_char}, {param_char}, {param_char}, {param_char}, {param_char})""",
                (prod, description, price, category, stock, img_path)
            )
            success_count += 1
            print(f"🔹 تم إدخال المنتج بنجاح: {prod}")
        except Exception as e:
            print(f"❌ خطأ أثناء إدخال المنتج ({prod}): {e}")
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n🎉 العملية تمت بنجاح! تم إدخال {success_count} منتج في قاعدة بيانات ريلواي تحت قسم 'Face'.")

if __name__ == "__main__":
    seed()