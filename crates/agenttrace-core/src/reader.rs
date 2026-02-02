use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use anyhow::Result;
use thiserror::Error;
use crate::crc;
use crate::storage::StorageLayout;

#[derive(Error, Debug)]
pub enum ReadError {
    #[error("CRC mismatch at line {line}: expected {expected}, got {actual}")]
    CrcMismatch {
        line: usize,
        expected: String,
        actual: String,
    },
    #[error("trace not found: {0}")]
    TraceNotFound(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

#[derive(Debug, Clone)]
pub struct TraceMeta {
    pub id: String,
    pub name: String,
    pub project: Option<String>,
    pub ts: f64,
    pub event_count: u64,
}

pub struct TraceReader {
    layout: StorageLayout,
}

/// Split a JSONL line into the JSON portion and verify its CRC if present.
/// Returns the JSON portion as a string slice.
/// Handles both new format (with `\t<8-hex-crc>`) and legacy (plain JSON).
fn split_and_verify(line: &str, line_num: usize) -> std::result::Result<&str, ReadError> {
    if let Some(tab_pos) = line.rfind('\t') {
        let json_part = &line[..tab_pos];
        let crc_hex = &line[tab_pos + 1..];
        if crc_hex.len() == 8 {
            let actual_crc = crc::calculate(json_part.as_bytes());
            let actual_hex = crc::format_hex(actual_crc);
            if crc_hex != actual_hex {
                return Err(ReadError::CrcMismatch {
                    line: line_num,
                    expected: crc_hex.to_string(),
                    actual: actual_hex,
                });
            }
            return Ok(json_part);
        }
    }
    // No valid CRC suffix — legacy format, return whole line
    Ok(line)
}

impl TraceReader {
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self {
            layout: StorageLayout::new(root),
        }
    }

    pub fn list_traces(&self) -> Result<Vec<TraceMeta>> {
        let mut traces = Vec::new();
        if !self.layout.root.exists() {
            return Ok(traces);
        }

        for entry in std::fs::read_dir(&self.layout.root)? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }

            let id = entry.file_name().to_string_lossy().to_string();
            let dir_mtime = entry
                .metadata()
                .ok()
                .and_then(|m| m.modified().ok())
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0);

            let mut meta = TraceMeta {
                id: id.clone(),
                name: id.clone(),
                project: None,
                ts: dir_mtime,
                event_count: 0,
            };

            let events_path = self.layout.events_file(&id);
            if events_path.exists() {
                if let Ok(file) = File::open(&events_path) {
                    let reader = BufReader::new(file);
                    let mut line_count: u64 = 0;
                    for (i, line_result) in reader.lines().enumerate() {
                        let Ok(line) = line_result else { break };
                        let trimmed = line.trim();
                        if trimmed.is_empty() {
                            continue;
                        }
                        line_count += 1;

                        // Extract metadata from the first non-empty line
                        if line_count == 1 {
                            let json_str = split_and_verify(trimmed, i + 1).unwrap_or(trimmed);
                            if let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) {
                                if value.get("kind").and_then(|v| v.as_str()) == Some("trace_start") {
                                    if let Some(payload) = value.get("payload").and_then(|v| v.as_object()) {
                                        if let Some(name) = payload.get("trace_name").and_then(|v| v.as_str()) {
                                            meta.name = name.to_string();
                                        }
                                        meta.project = payload.get("project").and_then(|v| v.as_str()).map(|s| s.to_string());
                                    }
                                    if let Some(ts_ns) = value.get("ts_unix_ns").and_then(|v| v.as_u64()) {
                                        meta.ts = ts_ns as f64 / 1e9;
                                    }
                                }
                            }
                        }
                    }
                    meta.event_count = line_count;
                }
            }

            traces.push(meta);
        }

        traces.sort_by(|a, b| b.ts.partial_cmp(&a.ts).unwrap_or(std::cmp::Ordering::Equal));
        Ok(traces)
    }

    /// Read all events for a trace, verifying CRC for each line.
    /// Returns events as `serde_json::Value` dicts to preserve any extra fields.
    pub fn get_events(&self, trace_id: &str) -> std::result::Result<Vec<serde_json::Value>, ReadError> {
        let path = self.layout.events_file(trace_id);
        if !path.exists() {
            return Err(ReadError::TraceNotFound(trace_id.to_string()));
        }

        let file = File::open(&path)?;
        let reader = BufReader::new(file);
        let mut events = Vec::new();

        for (i, line_result) in reader.lines().enumerate() {
            let line = line_result?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            let json_str = split_and_verify(trimmed, i + 1)?;
            let value: serde_json::Value = serde_json::from_str(json_str)?;
            events.push(value);
        }

        Ok(events)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::writer::TraceWriter;
    use crate::event::Event;
    use tempfile::tempdir;
    use serde_json::json;
    use std::io::Write;

    #[test]
    fn test_reader_verify_crc() -> anyhow::Result<()> {
        let tmp = tempdir()?;
        let trace_id = "test-reader";

        {
            let mut writer = TraceWriter::start(trace_id, tmp.path())?;
            let event = Event::new(trace_id.to_string(), 1, "test".to_string(), json!({"a": 1}));
            writer.emit(&event)?;
        }

        let reader = TraceReader::new(tmp.path());
        let events = reader.get_events(trace_id)?;
        assert_eq!(events.len(), 1);
        assert_eq!(events[0]["kind"], "test");

        Ok(())
    }

    #[test]
    fn test_reader_legacy_support() -> anyhow::Result<()> {
        let tmp = tempdir()?;
        let trace_id = "legacy-trace";
        let layout = StorageLayout::new(tmp.path());
        layout.ensure_trace_dir(trace_id)?;

        // Write manual JSONL without CRC
        let path = layout.events_file(trace_id);
        let mut file = File::create(path)?;
        let event = Event::new(trace_id.to_string(), 1, "legacy".to_string(), json!({}));
        writeln!(file, "{}", serde_json::to_string(&event)?)?;

        let reader = TraceReader::new(tmp.path());
        let events = reader.get_events(trace_id)?;
        assert_eq!(events.len(), 1);
        assert_eq!(events[0]["kind"], "legacy");

        Ok(())
    }

    #[test]
    fn test_reader_detects_corruption() -> anyhow::Result<()> {
        let tmp = tempdir()?;
        let trace_id = "corrupt-trace";
        let layout = StorageLayout::new(tmp.path());
        layout.ensure_trace_dir(trace_id)?;

        // Write a line with a bad CRC
        let path = layout.events_file(trace_id);
        let mut file = File::create(path)?;
        writeln!(file, "{{\"kind\":\"test\",\"seq\":1}}\t00000000")?;

        let reader = TraceReader::new(tmp.path());
        let result = reader.get_events(trace_id);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ReadError::CrcMismatch { .. }));

        Ok(())
    }

    #[test]
    fn test_list_traces() -> anyhow::Result<()> {
        let tmp = tempdir()?;

        for (id, name) in &[("trace-a", "alpha"), ("trace-b", "beta")] {
            let mut writer = TraceWriter::start(id, tmp.path())?;
            let event = Event::new(id.to_string(), 1, "trace_start".to_string(), json!({"trace_name": name}));
            writer.emit(&event)?;
        }

        let reader = TraceReader::new(tmp.path());
        let traces = reader.list_traces()?;
        assert_eq!(traces.len(), 2);

        let names: Vec<&str> = traces.iter().map(|t| t.name.as_str()).collect();
        assert!(names.contains(&"alpha"));
        assert!(names.contains(&"beta"));

        for t in &traces {
            assert_eq!(t.event_count, 1);
        }

        Ok(())
    }
}
