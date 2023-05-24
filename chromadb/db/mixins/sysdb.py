from typing import Optional, Sequence, Any, Tuple, cast
from uuid import UUID
from overrides import override
from pypika import Table, Column
from itertools import groupby

from chromadb.config import System
from chromadb.db.base import Cursor, SqlDB, ParameterValue, get_sql
from chromadb.db.system import SysDB
from chromadb.types import Segment, Metadata, Collection, SegmentScope


class SqlSysDB(SqlDB, SysDB):
    def __init__(self, system: System):
        super().__init__(system)

    @override
    def create_segment(self, segment: Segment) -> None:
        with self.tx() as cur:
            segments = Table("segments")
            insert_segment = (
                self.querybuilder()
                .into(segments)
                .columns(
                    segments.id,
                    segments.type,
                    segments.scope,
                    segments.topic,
                    segments.collection,
                )
                .insert(
                    ParameterValue(self.uuid_to_db(segment["id"])),
                    ParameterValue(segment["type"]),
                    ParameterValue(segment["scope"]),
                    ParameterValue(segment["topic"]),
                    ParameterValue(self.uuid_to_db(segment["collection"])),
                )
            )
            sql, params = get_sql(insert_segment, self.parameter_format())
            cur.execute(sql, params)
            metadata_t = Table("segment_metadata")
            if segment["metadata"]:
                self._insert_metadata(
                    cur,
                    metadata_t,
                    metadata_t.segment_id,
                    segment["id"],
                    segment["metadata"],
                )

    @override
    def create_collection(self, collection: Collection) -> None:
        """Create a new collection"""
        with self.tx() as cur:
            collections = Table("collections")
            insert_collection = (
                self.querybuilder()
                .into(collections)
                .columns(collections.id, collections.topic, collections.name)
                .insert(
                    ParameterValue(self.uuid_to_db(collection["id"])),
                    ParameterValue(collection["topic"]),
                    ParameterValue(collection["name"]),
                )
            )
            sql, params = get_sql(insert_collection, self.parameter_format())
            cur.execute(sql, params)
            metadata_t = Table("collection_metadata")
            if collection["metadata"]:
                self._insert_metadata(
                    cur,
                    metadata_t,
                    metadata_t.collection_id,
                    collection["id"],
                    collection["metadata"],
                )

    @override
    def get_segments(
        self,
        id: Optional[UUID] = None,
        type: Optional[str] = None,
        scope: Optional[SegmentScope] = None,
        topic: Optional[str] = None,
        collection: Optional[UUID] = None,
    ) -> Sequence[Segment]:
        segments_t = Table("segments")
        metadata_t = Table("segment_metadata")
        q = (
            self.querybuilder()
            .from_(segments_t)
            .select(
                segments_t.id,
                segments_t.type,
                segments_t.scope,
                segments_t.topic,
                segments_t.collection,
                metadata_t.key,
                metadata_t.str_value,
                metadata_t.int_value,
                metadata_t.float_value,
            )
            .left_join(metadata_t)
            .on(segments_t.id == metadata_t.segment_id)
            .orderby(segments_t.id)
        )
        if id:
            q = q.where(segments_t.id == ParameterValue(self.uuid_to_db(id)))
        if type:
            q = q.where(segments_t.type == ParameterValue(type))
        if scope:
            q = q.where(segments_t.scope == ParameterValue(scope.value))
        if topic:
            q = q.where(segments_t.topic == ParameterValue(topic))
        if collection:
            q = q.where(
                segments_t.collection == ParameterValue(self.uuid_to_db(collection))
            )

        with self.tx() as cur:
            sql, params = get_sql(q, self.parameter_format())
            rows = cur.execute(sql, params).fetchall()
            by_segment = groupby(rows, lambda r: cast(object, r[0]))
            segments = []
            for segment_id, segment_rows in by_segment:
                id = self.uuid_from_db(str(segment_id))
                rows = list(segment_rows)
                type = str(rows[0][1])
                scope = SegmentScope(str(rows[0][2]))
                topic = str(rows[0][3]) if rows[0][3] else None
                collection = self.uuid_from_db(rows[0][4]) if rows[0][4] else None
                metadata = self._metadata_from_rows(rows)
                segments.append(
                    Segment(
                        id=cast(UUID, id),
                        type=type,
                        scope=scope,
                        topic=topic,
                        collection=collection,
                        metadata=metadata,
                    )
                )

            return segments

    @override
    def get_collections(
        self,
        id: Optional[UUID] = None,
        topic: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Sequence[Collection]:
        """Get collections by name, embedding function and/or metadata"""
        collections_t = Table("collections")
        metadata_t = Table("collection_metadata")
        q = (
            self.querybuilder()
            .from_(collections_t)
            .select(
                collections_t.id,
                collections_t.name,
                collections_t.topic,
                metadata_t.key,
                metadata_t.str_value,
                metadata_t.int_value,
                metadata_t.float_value,
            )
            .left_join(metadata_t)
            .on(collections_t.id == metadata_t.collection_id)
            .orderby(collections_t.id)
        )
        if id:
            q = q.where(collections_t.id == ParameterValue(self.uuid_to_db(id)))
        if topic:
            q = q.where(collections_t.topic == ParameterValue(topic))
        if name:
            q = q.where(collections_t.name == ParameterValue(name))

        with self.tx() as cur:
            sql, params = get_sql(q, self.parameter_format())
            rows = cur.execute(sql, params).fetchall()
            by_collection = groupby(rows, lambda r: cast(object, r[0]))
            collections = []
            for collection_id, collection_rows in by_collection:
                id = self.uuid_from_db(str(collection_id))
                rows = list(collection_rows)
                name = str(rows[0][1])
                topic = str(rows[0][2])
                metadata = self._metadata_from_rows(rows)
                collections.append(
                    Collection(
                        id=cast(UUID, id),
                        topic=topic,
                        name=name,
                        metadata=metadata,
                    )
                )

            return collections

    @override
    def delete_segment(self, id: UUID) -> None:
        """Delete a segment from the SysDB"""
        t = Table("segments")
        q = (
            self.querybuilder()
            .from_(t)
            .where(t.id == ParameterValue(self.uuid_to_db(id)))
            .delete()
        )
        with self.tx() as cur:
            # no need for explicit del from metadata table because of ON DELETE CASCADE
            sql, params = get_sql(q, self.parameter_format())
            cur.execute(sql, params)

    @override
    def delete_collection(self, id: UUID) -> None:
        """Delete a topic and all associated segments from the SysDB"""
        t = Table("collections")
        q = (
            self.querybuilder()
            .from_(t)
            .where(t.id == ParameterValue(self.uuid_to_db(id)))
            .delete()
        )
        with self.tx() as cur:
            # no need for explicit del from metadata table because of ON DELETE CASCADE
            sql, params = get_sql(q, self.parameter_format())
            cur.execute(sql, params)

    def _metadata_from_rows(
        self, rows: Sequence[Tuple[Any, ...]]
    ) -> Optional[Metadata]:
        """Given SQL rows, return a metadata map (assuming that the last four columns
        are the key, str_value, int_value & float_value)"""
        # this originated from a left join, so we might not have any metadata values
        if not rows[0][-4]:
            return None
        metadata: Metadata = {}
        for row in rows:
            key = str(row[-4])
            if row[-3]:
                metadata[key] = str(row[-3])
            elif row[-2]:
                metadata[key] = int(row[-2])
            elif row[-1]:
                metadata[key] = float(row[-1])
        return metadata

    def _insert_metadata(
        self, cur: Cursor, table: Table, id_col: Column, id: UUID, metadata: Metadata
    ) -> None:
        q = (
            self.querybuilder()
            .into(table)
            .columns(
                id_col, table.key, table.str_value, table.int_value, table.float_value
            )
        )
        for k, v in metadata.items():
            if isinstance(v, str):
                q.insert(
                    ParameterValue(id), ParameterValue(k), ParameterValue(v), None, None
                )
            elif isinstance(v, int):
                q.insert(
                    ParameterValue(id), ParameterValue(k), None, ParameterValue(v), None
                )
            elif isinstance(v, float):
                q.insert(
                    ParameterValue(id), ParameterValue(k), None, None, ParameterValue(v)
                )
        sql, params = get_sql(q, self.parameter_format())
        cur.execute(sql, params)