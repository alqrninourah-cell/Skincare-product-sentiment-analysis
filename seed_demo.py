"""Populate a local database with entirely fictional demo products and reviews."""
from datetime import datetime
from app import app
from models import db, Product, Review

SAMPLES = [
    ("Sample Hydrating Cream", "Demo Botanics", "Moisturizer", "Fictional hydrating cream for a demo application", "dry", [("Leaves my skin feeling comfortable and hydrated.", 5), ("The texture is too heavy for me.", 2)]),
    ("Sample Gentle Cleanser", "Example Skincare", "Cleanser", "Fictional gentle cleanser for a demo application", "oily", [("Gentle and easy to use every morning.", 5), ("Not my favorite scent, but cleans well.", 3)]),
    ("Sample Daily Serum", "Demo Botanics", "Serum", "Fictional daily facial serum for a demo application", "combination", [("Absorbs quickly and feels lightweight.", 5), ("I did not notice much difference.", 2)]),
]

with app.app_context():
    db.create_all()
    if Product.query.first():
        print("Database already contains products; no changes made.")
    else:
        for name, brand, category, description, skin_type, reviews in SAMPLES:
            p = Product(name=name, brand_name=brand, category=category, description=description, rating=sum(r for _,r in reviews)/len(reviews))
            db.session.add(p)
            db.session.flush()
            for body, rating in reviews:
                db.session.add(Review(product_id=p.id, text=body, rating=rating, skin_type=skin_type, sentiment=('positive' if rating>=4 else 'negative' if rating<=2 else 'neutral'), created_at=datetime.utcnow()))
        db.session.commit()
        print("Created fictional demo products and reviews (no user accounts).")
