from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB  # If using PostgreSQL

Base = declarative_base()
