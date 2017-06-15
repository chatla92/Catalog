from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Products, Reviews, Categories, User
engine = create_engine('sqlite:///1_electronics_catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


f = open("amazon.txt", 'r')
content = f.read().split("\n")
uid = 1
rid = 1

for line in content:
    details = line.split(":::")
    ch = ['#', '=', '-', '+']
    if any(ext not in details[0] for ext in ch):
        reviewers = details[5].split(">>>")
        reviews = details[6].split("<<<")
        fir = details[0].find("\"")
        if fir != "-1":
            name = details[0][0:fir]
        try:
            cat = session.query(Categories).filter_by(
                name=details[2].strip()).one()
            P = Products(name=name.strip(), cat_id=cat.id,
                         category=details[2].strip(),
                         desc=details[3].strip(), user_id=uid,
                         img=details[4], url=details[7])
            session.add(P)
            session.commit()
        except:
            new_cat = Categories(name=details[2].strip())
            session.add(new_cat)
            session.commit()
            cat = session.query(Categories).filter_by(
                name=details[2].strip()).one()
            P = Products(name=name.strip(), cat_id=cat.id,
                         category=details[2].strip(),
                         desc=details[3].strip(), user_id=uid,
                         img=details[4], url=details[7])
            session.add(P)
            session.commit()
            pass

        for ind in range(3):
            U = User(name=reviewers[ind], id=uid, email=reviewers[ind].replace(
                " ", "") + "@amz.com")
            U.hash_password("1234")
            session.add(U)
            session.commit()
            R = Reviews(
                user_id=rid, product_id=details[1], review=reviews[ind])
            session.add(R)
            session.commit()
            print uid
            uid = uid + 1

print "added reviews!"
