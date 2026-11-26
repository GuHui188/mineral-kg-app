// All imports are namespaced; no deletion or mutation of old C database objects.
CREATE CONSTRAINT kg_entity_unique IF NOT EXISTS FOR (n:KGEntity) REQUIRE n.kg_id IS UNIQUE;
CREATE CONSTRAINT kg_snapshot_unique IF NOT EXISTS FOR (n:KGDataset) REQUIRE n.id IS UNIQUE;
