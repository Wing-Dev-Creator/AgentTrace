use std::fs::{File, OpenOptions};
use std::io::{Write, BufWriter};
use anyhow::{Result, Context};
use crate::event::Event;
use crate::crc;
use crate::storage::StorageLayout;

pub struct TraceWriter {
    pub trace_id: String,
    writer: BufWriter<File>,
}

impl TraceWriter {
    pub fn start(trace_id: &str, root: &std::path::Path) -> Result<Self> {
        let layout = StorageLayout::new(root);
        layout.ensure_trace_dir(trace_id)?;
        let path = layout.events_file(trace_id);
        
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)
            .with_context(|| format!("Failed to open events file at {:?}", path))?;
            
        Ok(Self {
            trace_id: trace_id.to_string(),
            writer: BufWriter::new(file),
        })
    }

    pub fn emit(&mut self, event: &Event) -> Result<()> {
        let json = serde_json::to_string(event)?;
        let crc_val = crc::calculate(json.as_bytes());
        let crc_hex = crc::format_hex(crc_val);
        
        writeln!(self.writer, "{}	{}", json, crc_hex)?;
        self.writer.flush()?;
        Ok(())
    }

    pub fn finish(mut self) -> Result<()> {
        self.writer.flush()?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use serde_json::json;

    #[test]
    fn test_writer_basic() -> Result<()> {
        let tmp = tempdir()?;
        let trace_id = "test-trace";
        let mut writer = TraceWriter::start(trace_id, tmp.path())?;
        
        let event = Event::new(trace_id.to_string(), 1, "test".to_string(), json!({"foo": "bar"}));
        writer.emit(&event)?;
        writer.finish()?;
        
        let events_file = tmp.path().join(trace_id).join("events.jsonl");
        assert!(events_file.exists());
        
        let content = std::fs::read_to_string(events_file)?;
        assert!(content.contains("\t"));
        assert!(content.contains("test"));
        
        Ok(())
    }
}
