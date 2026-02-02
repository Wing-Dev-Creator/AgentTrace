use std::path::{Path, PathBuf};
use anyhow::Result;

pub struct StorageLayout {
    pub root: PathBuf,
}

impl StorageLayout {
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self {
            root: root.as_ref().to_path_buf(),
        }
    }

    pub fn trace_dir(&self, trace_id: &str) -> PathBuf {
        self.root.join(trace_id)
    }

    pub fn events_file(&self, trace_id: &str) -> PathBuf {
        self.trace_dir(trace_id).join("events.jsonl")
    }

    pub fn ensure_trace_dir(&self, trace_id: &str) -> Result<PathBuf> {
        let path = self.trace_dir(trace_id);
        std::fs::create_dir_all(&path)?;
        Ok(path)
    }
}
