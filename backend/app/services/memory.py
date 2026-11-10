import hashlib, re, sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any

class MemoryStore:
    """Local SQLite FTS5 knowledge store for Markdown and manually added documents."""
    def __init__(self, database_path: Path, vector_enabled: bool=False, embedding_model: str="", vector_path: Path|None=None):
        self.database_path=database_path
        self.vector_enabled=vector_enabled
        self.retrieval_mode="fts5"
        database_path.parent.mkdir(parents=True,exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self)->Iterator[sqlite3.Connection]:
        db=sqlite3.connect(self.database_path); db.row_factory=sqlite3.Row
        try:
            yield db; db.commit()
        except Exception:
            db.rollback(); raise
        finally: db.close()

    def initialize(self):
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memory_documents(id TEXT PRIMARY KEY,title TEXT NOT NULL,source TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_chunks USING fts5(id UNINDEXED,document_id UNINDEXED,title,source UNINDEXED,content, tokenize='unicode61')")

    @staticmethod
    def split_chunks(content:str,chunk_size:int=1200,overlap:int=160)->list[str]:
        text=content.strip()
        if not text:return []
        chunks=[]; start=0
        while start<len(text):
            end=min(start+chunk_size,len(text)); chunks.append(text[start:end])
            if end==len(text):break
            start=max(end-overlap,start+1)
        return chunks

    def upsert_document(self,title:str,content:str,source:str="manual")->dict[str,Any]:
        digest=hashlib.sha256(f"{source}\0{title}".encode()).hexdigest()[:24]
        chunks=self.split_chunks(content)
        with self.connect() as db:
            db.execute("INSERT INTO memory_documents(id,title,source,content) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,source=excluded.source,content=excluded.content",(digest,title,source,content))
            db.execute("DELETE FROM memory_chunks WHERE document_id=?",(digest,))
            for i,chunk in enumerate(chunks):
                db.execute("INSERT INTO memory_chunks(id,document_id,title,source,content) VALUES(?,?,?,?,?)",(f"{digest}-{i}",digest,title,source,chunk))
        return {"id":digest,"title":title,"source":source,"chunks":len(chunks)}

    def ingest_vault(self,vault_path:Path)->dict[str,Any]:
        vault_path.mkdir(parents=True,exist_ok=True); ingested=[]; active=set()
        for path in vault_path.rglob("*.md"):
            try:
                resolved=path.resolve()
                if vault_path.resolve() not in resolved.parents:continue
                content=path.read_text(encoding="utf-8")
                if content.strip():
                    source=f"vault:{resolved.relative_to(vault_path.resolve()).as_posix()}"
                    active.add(hashlib.sha256(f"{source}\0{path.stem}".encode()).hexdigest()[:24])
                    ingested.append(self.upsert_document(path.stem,content,source))
            except (OSError,UnicodeError):continue
        with self.connect() as db:
            stale=[row[0] for row in db.execute("SELECT id FROM memory_documents WHERE source LIKE 'vault:%'") if row[0] not in active]
            for doc_id in stale:
                db.execute("DELETE FROM memory_chunks WHERE document_id=?",(doc_id,))
                db.execute("DELETE FROM memory_documents WHERE id=?",(doc_id,))
        return {"files_found":len(list(vault_path.rglob("*.md"))),"documents_ingested":len(ingested),"documents":ingested}

    def search(self,query:str,limit:int=6)->list[dict[str,Any]]:
        tokens=[x for x in re.findall(r"[\w\u0600-\u06FF]+",query) if len(x)>1]
        if not tokens:return []
        expr=" OR ".join('"'+x.replace('"','')+'"' for x in tokens[:20])
        with self.connect() as db:
            try: rows=db.execute("SELECT id,document_id,title,source,content,bm25(memory_chunks) rank FROM memory_chunks WHERE memory_chunks MATCH ? ORDER BY rank LIMIT ?",(expr,limit)).fetchall()
            except sqlite3.OperationalError:return []
        return [{"id":x["id"],"document_id":x["document_id"],"title":x["title"],"source":x["source"],"excerpt":x["content"],"score":float(-x["rank"])} for x in rows]

    def stats(self)->dict[str,int]:
        with self.connect() as db:
            return {"documents":db.execute("SELECT COUNT(*) FROM memory_documents").fetchone()[0],"chunks":db.execute("SELECT COUNT(*) FROM memory_chunks").fetchone()[0]}
