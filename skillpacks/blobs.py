import json
import time
import uuid
from typing import List, Optional, Any, Dict
from sqlalchemy import asc

from skillpacks.db.conn import WithDB
from skillpacks.db.models import JsonBlobRecord

class JsonBlobs(WithDB):
    """A class to handle JSON blob storage and retrieval"""

    def __init__(
        self,
        data: Dict[str, Any],
        namespace: str,
        schema: Optional[str] = None,
        tags: List[str] = [],
        labels: Dict[str, Any] = {},
        owner_id: Optional[str] = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.schema = schema
        self.data = data
        self.created = time.time()
        self.updated = time.time()
        self.tags = tags
        self.labels = labels
        self.owner_id = owner_id
        self.namespace = namespace

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

    def to_record(self) -> JsonBlobRecord:
        """Converts the JsonBlobs instance to a database record."""
        return JsonBlobRecord(
            id=self.id,
            owner_id=self.owner_id,
            schema=self.schema,
            data=json.dumps(self.data),
            tags=json.dumps(self.tags),
            labels=json.dumps(self.labels),
            created=self.created,
            updated=self.updated,
            namespace=self.namespace,
        )

    @classmethod
    def from_record(cls, record: JsonBlobRecord) -> "JsonBlobs":
        """Creates a JsonBlobs instance from a database record."""
        json_blob = cls.__new__(cls)
        json_blob.id = record.id
        json_blob.owner_id = record.owner_id
        json_blob.schema = record.schema
        json_blob.data = json.loads(record.data)
        json_blob.tags = json.loads(record.tags)
        json_blob.labels = json.loads(record.labels)
        json_blob.created = record.created
        json_blob.updated = record.updated
        json_blob.namespace = record.namespace
        return json_blob

    @classmethod
    def find(cls, namespace: str, **kwargs) -> List["JsonBlobs"]:
        """Finds JsonBlobs instances based on given criteria and namespace."""
        for db in cls.get_db():
            records = (
                db.query(JsonBlobRecord)
                .filter_by(namespace=namespace, **kwargs)
                .order_by(asc(JsonBlobRecord.created))
                .all()
            )
            return [cls.from_record(record) for record in records]

        raise ValueError("no session")

    @classmethod
    def get(cls, id: str, namespace: str = "default") -> "JsonBlobs":
        """Retrieves a single JsonBlobs instance by ID and namespace."""
        for db in cls.get_db():
            record = db.query(JsonBlobRecord).filter(
                JsonBlobRecord.id == id,
                JsonBlobRecord.namespace == namespace
            ).first()
            if record:
                return cls.from_record(record)
            raise ValueError(f"No JsonBlobs found with id {id} in namespace {namespace}")
        raise ValueError("no session")

    def delete(self) -> None:
        """Deletes the JsonBlobs instance from the database."""
        for db in self.get_db():
            record = db.query(JsonBlobRecord).filter(
                JsonBlobRecord.id == self.id,
                JsonBlobRecord.namespace == self.namespace
            ).first()
            if record:
                db.delete(record)
                db.commit()
            else:
                raise ValueError(f"JsonBlobs record not found in namespace {self.namespace}")

    def update(self, data: Dict[str, Any]) -> None:
        """Updates the data of the JsonBlobs instance."""
        self.data.update(data)
        self.updated = time.time()
        self.save()

    def add_tag(self, tag: str) -> None:
        """Adds a tag to the JsonBlobs instance."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated = time.time()
            self.save()

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the JsonBlobs instance."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated = time.time()
            self.save()

    def set_label(self, key: str, value: Any) -> None:
        """Sets a label for the JsonBlobs instance."""
        self.labels[key] = value
        self.updated = time.time()
        self.save()

    def remove_label(self, key: str) -> None:
        """Removes a label from the JsonBlobs instance."""
        if key in self.labels:
            del self.labels[key]
            self.updated = time.time()
            self.save()

    @classmethod
    def list_namespaces(cls) -> List[str]:
        """Lists all unique namespaces in the database."""
        for db in cls.get_db():
            namespaces = db.query(JsonBlobRecord.namespace).distinct().all()
            return [namespace[0] for namespace in namespaces]
        raise ValueError("no session")