import psycopg2

# حط رابط ريلواي الخارجي بتاعك هنا
DATABASE_URL = "postgresql://postgres:bhqPlGBITeuehgRNnwyPZspigxbbcMaV@reseau.proxy.rlwy.net:20529/railway"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# تعديل المسار من /lumora/ ليكون /static/images/ أو المسار المتاح للصور
cursor.execute("UPDATE products SET image = REPLACE(image, '/lumora/', '/static/images/') WHERE image LIKE '/lumora/%'")

conn.commit()
print(f"✅ تم تحديث مسارات الصور بنجاح! لـ {cursor.rowcount} منتج.")
cursor.close()
conn.close()