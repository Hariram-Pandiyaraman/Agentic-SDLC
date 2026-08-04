"""SQLAlchemy-backed LangGraph checkpointer for cross-process HITL resume."""

from collections.abc import Iterator, Sequence
from typing import Any

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

from sdlc.persistence.repositories import SqlAlchemyRepository


class SqlAlchemyCheckpointSaver(BaseCheckpointSaver):
    def __init__(self, repository: SqlAlchemyRepository) -> None:
        super().__init__()
        self.repository = repository

    def get_tuple(self, config: dict) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        namespace = config["configurable"].get("checkpoint_ns", "")
        row = self.repository.get_snapshot(thread_id, namespace, get_checkpoint_id(config))
        return self._tuple(row) if row else None

    def list(
        self,
        config: dict | None,
        *,
        filter: dict[str, Any] | None = None,
        before: dict | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"] if config else None
        namespace = config["configurable"].get("checkpoint_ns") if config else None
        checkpoint_id = get_checkpoint_id(config) if config else None
        before_id = get_checkpoint_id(before) if before else None
        count = 0
        for row in self.repository.list_snapshots(thread_id, namespace):
            if checkpoint_id and row.checkpoint_id != checkpoint_id:
                continue
            if before_id and row.checkpoint_id >= before_id:
                continue
            metadata = self.serde.loads_typed((row.metadata_type, row.metadata_blob))
            if filter and not all(metadata.get(key) == value for key, value in filter.items()):
                continue
            if limit is not None and count >= limit:
                break
            count += 1
            yield self._tuple(row)

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict,
    ) -> dict:
        thread_id = config["configurable"]["thread_id"]
        namespace = config["configurable"].get("checkpoint_ns", "")
        parent_id = config["configurable"].get("checkpoint_id")
        parent = self.repository.get_snapshot(thread_id, namespace, parent_id) if parent_id else None
        parent_values: dict[str, Any] = {}
        if parent:
            restored = self.serde.loads_typed((parent.checkpoint_type, parent.checkpoint_blob))
            parent_values = dict(restored.get("channel_values", {}))
        stored = checkpoint.copy()
        changed = dict(stored.get("channel_values", {}))
        current_channels = set(stored.get("channel_versions", {}))
        stored["channel_values"] = {
            key: value
            for key, value in {**parent_values, **changed}.items()
            if key in current_channels
        }
        checkpoint_type, checkpoint_blob = self.serde.dumps_typed(stored)
        metadata_type, metadata_blob = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        sequence = self.repository.next_snapshot_sequence(thread_id, namespace)
        self.repository.put_snapshot(
            run_id=thread_id, checkpoint_ns=namespace, checkpoint_id=checkpoint["id"],
            parent_checkpoint_id=parent_id, sequence=sequence,
            checkpoint_type=checkpoint_type, checkpoint_blob=checkpoint_blob,
            metadata_type=metadata_type, metadata_blob=metadata_blob,
            writes_type=None, writes_blob=None,
        )
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": namespace, "checkpoint_id": checkpoint["id"]}}

    def put_writes(
        self,
        config: dict,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        namespace = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        rows = []
        for index, (channel, value) in enumerate(writes):
            write_index = WRITES_IDX_MAP.get(channel, index)
            value_type, value_blob = self.serde.dumps_typed(value)
            rows.append({
                "run_id": thread_id, "checkpoint_ns": namespace,
                "checkpoint_id": checkpoint_id, "task_id": task_id,
                "write_index": write_index, "channel": channel,
                "value_type": value_type, "value_blob": value_blob,
                "task_path": task_path,
            })
        self.repository.put_checkpoint_writes(rows)

    def delete_thread(self, thread_id: str) -> None:
        self.repository.delete_snapshots(thread_id)

    def _tuple(self, row) -> CheckpointTuple:
        checkpoint = self.serde.loads_typed((row.checkpoint_type, row.checkpoint_blob))
        metadata = self.serde.loads_typed((row.metadata_type, row.metadata_blob))
        writes = self.repository.get_checkpoint_writes(row.run_id, row.checkpoint_ns, row.checkpoint_id)
        config = {"configurable": {"thread_id": row.run_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.checkpoint_id}}
        parent = {"configurable": {"thread_id": row.run_id, "checkpoint_ns": row.checkpoint_ns, "checkpoint_id": row.parent_checkpoint_id}} if row.parent_checkpoint_id else None
        return CheckpointTuple(
            config=config, checkpoint=checkpoint, metadata=metadata,
            pending_writes=[(item.task_id, item.channel, self.serde.loads_typed((item.value_type, item.value_blob))) for item in writes],
            parent_config=parent,
        )
