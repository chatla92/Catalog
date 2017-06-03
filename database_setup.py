from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    password_hash = Column(String(64))

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

class Categories(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)


class Products(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    category = Column(String(100), nullable=False)
    cat_id = Column(Integer, ForeignKey('categories.id'))
    categories = relationship(Categories)
    desc = Column(String(1000))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    img = Column(String(100))
    url = Column(String(100))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'category': self.category,
            'description': self.desc,
        }


class Reviews(Base):
    __tablename__ = 'reviews'

    #  "{:%H:%M.%S %B %d, %Y}".format(datetime.datetime.utcnow())
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    product_id = Column(Integer, ForeignKey('product.id'))
    product = relationship(Products)
    review = Column(String(1000), nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'user': self.user,
            'product': self.product_id,
            'review': self.review,
        }


engine = create_engine('sqlite:///1_electronics_catalog.db')


Base.metadata.create_all(engine)
